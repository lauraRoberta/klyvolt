-- =====================================================================
-- KLYVOLT · Migração 02 — Regras de negócio no banco
--   • Cadastro de empresa + administrador a partir do Supabase Auth
--   • Atribuição automática da empresa em setores e decisões
--   • Validação de responsável do setor
--   • Agregação automática de leituras em consumos
--   • Motor de decisão automática (README do KLYVOLT Main: item pendente)
--   • Cálculo de consumo por período, resumo de sensores
--   • Ingestão de leituras por sensores físicos via token
-- =====================================================================

-- ---------------------------------------------------------------------
-- 1. Utilitários de validação (portados de backend/schemas.py)
-- ---------------------------------------------------------------------
create or replace function public.kv_cnpj_valido(p text)
returns boolean language plpgsql immutable set search_path = '' as $$
declare d text := regexp_replace(coalesce(p,''), '\D', '', 'g');
        pesos1 int[] := array[5,4,3,2,9,8,7,6,5,4,3,2];
        pesos2 int[] := array[6,5,4,3,2,9,8,7,6,5,4,3,2];
        s int; r int; i int;
begin
  if length(d) <> 14 or d ~ '^(\d)\1{13}$' then return false; end if;
  s := 0; for i in 1..12 loop s := s + substr(d,i,1)::int * pesos1[i]; end loop;
  r := s % 11; r := case when r < 2 then 0 else 11 - r end;
  if r <> substr(d,13,1)::int then return false; end if;
  s := 0; for i in 1..13 loop s := s + substr(d,i,1)::int * pesos2[i]; end loop;
  r := s % 11; r := case when r < 2 then 0 else 11 - r end;
  return r = substr(d,14,1)::int;
end $$;

create or replace function public.kv_formatar_cnpj(p text)
returns text language sql immutable set search_path = '' as $$
  select case when length(d) = 14
    then substr(d,1,2)||'.'||substr(d,3,3)||'.'||substr(d,6,3)||'/'||substr(d,9,4)||'-'||substr(d,13,2)
  end
  from (select regexp_replace(coalesce(p,''), '\D', '', 'g') as d) x
$$;

create or replace function public.kv_formatar_telefone(p text)
returns text language plpgsql immutable set search_path = '' as $$
declare d text := regexp_replace(coalesce(p,''), '\D', '', 'g');
begin
  if length(d) in (12,13) and left(d,2) = '55' then d := substr(d,3); end if;
  if length(d) = 11 then return '('||substr(d,1,2)||') '||substr(d,3,5)||'-'||substr(d,8); end if;
  if length(d) = 10 then return '('||substr(d,1,2)||') '||substr(d,3,4)||'-'||substr(d,7); end if;
  return null;
end $$;

-- ---------------------------------------------------------------------
-- 2. Cadastro: ao criar o usuário no Supabase Auth com os metadados do
--    formulário "Nova Empresa", cria a empresa e o administrador.
-- ---------------------------------------------------------------------
create or replace function public.kv_handle_new_user()
returns trigger language plpgsql security definer set search_path = '' as $$
declare
  m jsonb := coalesce(new.raw_user_meta_data, '{}'::jsonb);
  v_cnpj text; v_tel text; v_nome text; v_resp text; v_emp int;
begin
  if coalesce(m->>'kv_cadastro', '') <> 'empresa' then
    return new;  -- usuários criados por outros meios não são alterados
  end if;

  if not public.kv_cnpj_valido(m->>'cnpj') then
    raise exception 'KV_CNPJ_INVALIDO' using errcode = '22023';
  end if;
  v_cnpj := public.kv_formatar_cnpj(m->>'cnpj');
  v_tel  := public.kv_formatar_telefone(m->>'telefone');
  if v_tel is null then
    raise exception 'KV_TELEFONE_INVALIDO' using errcode = '22023';
  end if;
  v_nome := nullif(btrim(m->>'nome_empresa'), '');
  if v_nome is null or length(v_nome) > 100 then
    raise exception 'KV_NOME_INVALIDO' using errcode = '22023';
  end if;
  v_resp := coalesce(nullif(btrim(m->>'nome_usuario'), ''), v_nome);

  if exists (select 1 from public.empresa where cnpj = v_cnpj) then
    raise exception 'KV_CNPJ_EM_USO' using errcode = '23505';
  end if;
  if exists (select 1 from public.empresa where lower(email_empresa) = lower(new.email))
     or exists (select 1 from public.usuario where lower(email_usuario) = lower(new.email)) then
    raise exception 'KV_EMAIL_EM_USO' using errcode = '23505';
  end if;

  insert into public.empresa (cnpj, nome_empresa, email_empresa, telefone_empresa)
  values (v_cnpj, v_nome, new.email, v_tel)
  returning id_empresa into v_emp;

  insert into public.usuario (nome_usuario, email_usuario, tipo_usuario, id_empresa, auth_user_id)
  values (left(v_resp, 100), new.email, 'Administrador', v_emp, new.id);

  return new;
end $$;

drop trigger if exists kv_on_auth_user_created on auth.users;
create trigger kv_on_auth_user_created
  after insert on auth.users
  for each row execute function public.kv_handle_new_user();

-- Pré-verificação do formulário (mensagem clara antes de criar a conta).
create or replace function public.kv_verificar_cadastro(p_cnpj text, p_email text)
returns json language sql stable security definer set search_path = '' as $$
  select json_build_object(
    'cnpj_valido',   public.kv_cnpj_valido(p_cnpj),
    'cnpj_em_uso',   exists (select 1 from public.empresa where cnpj = public.kv_formatar_cnpj(p_cnpj)),
    'email_em_uso',  exists (select 1 from public.empresa where lower(email_empresa) = lower(btrim(p_email)))
                  or exists (select 1 from public.usuario where lower(email_usuario) = lower(btrim(p_email)))
  )
$$;
revoke all on function public.kv_verificar_cadastro(text, text) from public;
grant execute on function public.kv_verificar_cadastro(text, text) to anon, authenticated;

-- ---------------------------------------------------------------------
-- 3. Empresa atribuída pelo servidor (o cliente não escolhe a empresa)
-- ---------------------------------------------------------------------
create or replace function public.kv_definir_empresa()
returns trigger language plpgsql security definer set search_path = '' as $$
declare v_emp int := public.kv_empresa_atual();
begin
  if v_emp is not null then
    new.id_empresa := v_emp;
  elsif tg_table_name = 'setor' and new.id_empresa is null then
    -- Compatibilidade com acesso administrativo direto ao banco
    new.id_empresa := public.kv_empresa_do_usuario(new.id_usuario_responsavel);
  end if;
  return new;
end $$;

drop trigger if exists kv_setor_empresa on public.setor;
create trigger kv_setor_empresa before insert or update on public.setor
  for each row execute function public.kv_definir_empresa();
drop trigger if exists kv_decisao_empresa on public.decisao;
create trigger kv_decisao_empresa before insert or update on public.decisao
  for each row execute function public.kv_definir_empresa();

-- O responsável pelo setor precisa ser da mesma empresa do setor.
create or replace function public.kv_validar_responsavel_setor()
returns trigger language plpgsql security definer set search_path = '' as $$
begin
  if public.kv_empresa_do_usuario(new.id_usuario_responsavel) is distinct from new.id_empresa then
    raise exception 'KV_RESPONSAVEL_OUTRA_EMPRESA' using errcode = '23503';
  end if;
  return new;
end $$;

drop trigger if exists kv_setor_responsavel on public.setor;
create trigger kv_setor_responsavel before insert or update on public.setor
  for each row execute function public.kv_validar_responsavel_setor();
-- (os nomes "kv_setor_empresa" < "kv_setor_responsavel" garantem a ordem de execução)

-- ---------------------------------------------------------------------
-- 4. Agregação: leituras dos sensores de uma máquina dentro do período
--    de um consumo ficam vinculadas a ele (status "Agregada").
-- ---------------------------------------------------------------------
create or replace function public.kv_agregar_consumo()
returns trigger language plpgsql security definer set search_path = '' as $$
begin
  -- desvincula leituras que deixaram de pertencer ao período/máquina
  update public.leitura l set id_consumo = null
   where l.id_consumo = new.id_consumo
     and (l.data_leitura < new.data_inicio or l.data_leitura > new.data_fim
          or not exists (select 1 from public.sensor s
                          where s.id_sensor = l.id_sensor and s.id_maquina = new.id_maquina));
  -- vincula as leituras pendentes do período
  update public.leitura l set id_consumo = new.id_consumo
    from public.sensor s
   where s.id_sensor = l.id_sensor
     and s.id_maquina = new.id_maquina
     and l.id_consumo is null
     and l.data_leitura between new.data_inicio and new.data_fim;
  return null;
end $$;

drop trigger if exists kv_consumo_agregar on public.consumo;
create trigger kv_consumo_agregar
  after insert or update of data_inicio, data_fim, id_maquina on public.consumo
  for each row execute function public.kv_agregar_consumo();

-- Leitura nova (ou com data/sensor alterados) entra no consumo que cobre o período.
create or replace function public.kv_vincular_leitura()
returns trigger language plpgsql security definer set search_path = '' as $$
begin
  if tg_op = 'INSERT' and new.id_consumo is not null then
    return new;  -- vínculo explícito informado
  end if;
  select c.id_consumo into new.id_consumo
    from public.consumo c
    join public.sensor s on s.id_maquina = c.id_maquina
   where s.id_sensor = new.id_sensor
     and new.data_leitura between c.data_inicio and c.data_fim
   order by c.data_inicio
   limit 1;
  return new;
end $$;

drop trigger if exists kv_leitura_vincular on public.leitura;
create trigger kv_leitura_vincular
  before insert or update of data_leitura, id_sensor on public.leitura
  for each row execute function public.kv_vincular_leitura();

-- ---------------------------------------------------------------------
-- 5. Motor de decisão automática
--    Regras ativas da empresa, com unidade kWh:
--      critério "valor_medido_kwh" / contém "leitura" → avaliada a cada leitura
--      critério contém "consumo"                       → avaliada a cada consumo
--    Quando a condição é verdadeira, registra uma tomada_decisao "pendente".
-- ---------------------------------------------------------------------
create or replace function public.kv_comparar(v numeric, op text, limite numeric)
returns boolean language sql immutable set search_path = '' as $$
  select case op when '>'  then v >  limite when '>=' then v >= limite
                 when '<'  then v <  limite when '<=' then v <= limite
                 when '='  then v =  limite else false end
$$;

create or replace function public.kv_avaliar_leitura()
returns trigger language plpgsql security definer set search_path = '' as $$
declare v_emp int := public.kv_empresa_do_sensor(new.id_sensor);
begin
  insert into public.tomada_decisao (valor_referencia, status_execucao, observacao, id_decisao, id_leitura)
  select new.valor_medido_kwh, 'pendente',
         'Acionada automaticamente: leitura de ' || to_char(new.valor_medido_kwh, 'FM999999990.00')
           || ' kWh ' || d.operador || ' ' || to_char(d.limite_referencia, 'FM999999990.00') || ' kWh',
         d.id_decisao, new.id_leitura
    from public.decisao d
   where d.id_empresa = v_emp and d.ativo
     and lower(d.unidade_limite) = 'kwh'
     and (lower(d.criterio_acionado) like '%valor_medido%' or lower(d.criterio_acionado) like '%leitura%')
     and public.kv_comparar(new.valor_medido_kwh, d.operador, d.limite_referencia);
  return null;
end $$;

drop trigger if exists kv_leitura_decisao on public.leitura;
create trigger kv_leitura_decisao after insert or update of valor_medido_kwh on public.leitura
  for each row execute function public.kv_avaliar_leitura();

create or replace function public.kv_avaliar_consumo()
returns trigger language plpgsql security definer set search_path = '' as $$
declare v_emp int := public.kv_empresa_da_maquina(new.id_maquina);
begin
  insert into public.tomada_decisao (valor_referencia, status_execucao, observacao, id_decisao, id_consumo)
  select new.consumo_kwh, 'pendente',
         'Acionada automaticamente: consumo de ' || to_char(new.consumo_kwh, 'FM999999990.00')
           || ' kWh ' || d.operador || ' ' || to_char(d.limite_referencia, 'FM999999990.00') || ' kWh',
         d.id_decisao, new.id_consumo
    from public.decisao d
   where d.id_empresa = v_emp and d.ativo
     and lower(d.unidade_limite) = 'kwh'
     and lower(d.criterio_acionado) like '%consumo%'
     and public.kv_comparar(new.consumo_kwh, d.operador, d.limite_referencia)
     and not exists (select 1 from public.tomada_decisao t
                      where t.id_decisao = d.id_decisao and t.id_consumo = new.id_consumo
                        and t.valor_referencia = new.consumo_kwh);
  return null;
end $$;

drop trigger if exists kv_consumo_decisao on public.consumo;
create trigger kv_consumo_decisao after insert or update of consumo_kwh on public.consumo
  for each row execute function public.kv_avaliar_consumo();

-- ---------------------------------------------------------------------
-- 6. Cálculos (executam com as permissões do usuário → respeitam o RLS)
-- ---------------------------------------------------------------------
-- Soma das leituras dos sensores de uma máquina em um período.
create or replace function public.kv_calcular_consumo(p_id_maquina int, p_inicio timestamp, p_fim timestamp)
returns table (total_kwh numeric, leituras bigint)
language sql stable security invoker set search_path = '' as $$
  select coalesce(sum(l.valor_medido_kwh), 0)::numeric(12,2), count(l.id_leitura)
    from public.leitura l
    join public.sensor s on s.id_sensor = l.id_sensor
   where s.id_maquina = p_id_maquina
     and l.data_leitura between p_inicio and p_fim
$$;

-- Resumo por sensor: total, hoje (horário de Brasília) e maior leitura.
create or replace function public.kv_resumo_sensores()
returns table (id_sensor int, total_kwh numeric, hoje_kwh numeric, pico_kwh numeric,
               qtd_leituras bigint, ultima_leitura timestamp)
language sql stable security invoker set search_path = '' as $$
  select l.id_sensor,
         coalesce(sum(l.valor_medido_kwh), 0),
         coalesce(sum(l.valor_medido_kwh) filter (
           where l.data_leitura::date = (now() at time zone 'America/Sao_Paulo')::date), 0),
         coalesce(max(l.valor_medido_kwh), 0),
         count(*),
         max(l.data_leitura)
    from public.leitura l
   group by l.id_sensor
$$;

revoke all on function public.kv_calcular_consumo(int, timestamp, timestamp), public.kv_resumo_sensores() from public, anon;
grant execute on function public.kv_calcular_consumo(int, timestamp, timestamp), public.kv_resumo_sensores() to authenticated;

-- ---------------------------------------------------------------------
-- 7. Ingestão por sensor físico (sem login de usuário): o equipamento
--    envia seu token_autenticacao. Apenas sensores com status "ativo".
--    POST /rest/v1/rpc/kv_registrar_leitura_sensor
-- ---------------------------------------------------------------------
create or replace function public.kv_registrar_leitura_sensor(
  p_token text, p_valor_kwh numeric, p_data_leitura timestamp default null, p_observacao text default null)
returns int language plpgsql security definer set search_path = '' as $$
declare v_sensor int; v_id int;
begin
  if p_token is null or length(p_token) < 8 then
    raise exception 'KV_TOKEN_INVALIDO' using errcode = '28000';
  end if;
  select id_sensor into v_sensor from public.sensor
   where token_autenticacao = p_token and status = 'ativo' and ativo;
  if v_sensor is null then
    raise exception 'KV_TOKEN_INVALIDO' using errcode = '28000';
  end if;
  if p_valor_kwh is null or p_valor_kwh < 0 then
    raise exception 'KV_VALOR_INVALIDO' using errcode = '22023';
  end if;
  insert into public.leitura (data_leitura, valor_medido_kwh, observacao_leitura, id_sensor)
  values (coalesce(p_data_leitura, now() at time zone 'America/Sao_Paulo'), p_valor_kwh,
          left(p_observacao, 500), v_sensor)
  returning id_leitura into v_id;
  update public.sensor set status_conexao = 'online' where id_sensor = v_sensor;
  return v_id;
end $$;
revoke all on function public.kv_registrar_leitura_sensor(text, numeric, timestamp, text) from public;
grant execute on function public.kv_registrar_leitura_sensor(text, numeric, timestamp, text) to anon, authenticated;
