-- =====================================================================
-- KLYVOLT — Sistema de Gestão de Consumo de Energia
-- Script completo do banco (PostgreSQL / Supabase)
--
-- USO: instalação NOVA, em um projeto Supabase vazio (SQL Editor).
--      O banco oficial do KLYVOLT JÁ ESTÁ criado: para ele, o histórico
--      aplicado está em database/migracoes/ (não execute este arquivo nele).
--
-- Ordem: tabelas → índices → funções → triggers → permissões → RLS.
-- A tabela auth.users pertence ao Supabase Auth.
-- =====================================================================

-- ---------------------------------------------------------------------
-- 1. TABELAS (na ordem das chaves estrangeiras)
-- ---------------------------------------------------------------------

-- EMPRESA: cliente do sistema (topo da hierarquia)
create table public.empresa (
  id_empresa        serial primary key,
  cnpj              varchar(18)  not null unique,
  nome_empresa      varchar(100) not null,
  email_empresa     varchar(100) not null unique,
  senha_empresa     varchar(255),                       -- legado: login agora é feito pelo Supabase Auth
  telefone_empresa  varchar(20)  not null,
  tarifa_kwh        numeric(10,4),                      -- R$/kWh, usado no cálculo de custo
  constraint chk_cnpj_formato check (cnpj ~ '^[0-9]{2}\.?[0-9]{3}\.?[0-9]{3}\/?[0-9]{4}-?[0-9]{2}$'),
  constraint chk_tarifa_kwh  check (tarifa_kwh is null or tarifa_kwh >= 0)
);
comment on table  public.empresa is 'Empresa cliente do sistema Klyvolt';
comment on column public.empresa.senha_empresa is 'Hash da senha (bcrypt/argon2). Nunca armazenar em texto puro.';

-- USUARIO: pessoa que acessa o sistema (N:1 empresa), ligada ao Supabase Auth
create table public.usuario (
  id_usuario     serial primary key,
  nome_usuario   varchar(100) not null,
  email_usuario  varchar(100) not null unique,
  senha_usuario  varchar(255),                          -- legado: login agora é feito pelo Supabase Auth
  tipo_usuario   varchar(20)  not null,
  id_empresa     int not null references public.empresa(id_empresa) on delete cascade,
  ativo          boolean default true,
  auth_user_id   uuid unique references auth.users(id) on delete set null,
  constraint chk_tipo_usuario check (tipo_usuario in ('Administrador','Operador','Visualizador'))
);

-- SETOR: área da produção (N:1 empresa, N:1 usuário responsável)
create table public.setor (
  id_setor                serial primary key,
  nome_setor              varchar(100) not null,
  divisao_setor           varchar(100),
  id_usuario_responsavel  int not null references public.usuario(id_usuario) on delete no action,
  ativo                   boolean default true,
  id_empresa              int not null references public.empresa(id_empresa) on delete cascade,
  constraint uq_setor_empresa_nome unique (id_empresa, nome_setor)
);

-- MAQUINA: equipamento da produção (N:1 setor)
create table public.maquina (
  id_maquina         serial primary key,
  nome_maquina       varchar(100) not null,
  descricao_maquina  text not null,
  potencia_nominal   numeric(10,2),                     -- W
  numero_serie       varchar(50) unique,
  id_setor           int not null references public.setor(id_setor) on delete cascade,
  ativo              boolean default true,
  constraint chk_potencia_positiva check (potencia_nominal is null or potencia_nominal > 0)
);

-- SENSOR: medidor instalado na máquina (N:1 máquina)
create table public.sensor (
  id_sensor               serial primary key,
  numero_serie            varchar(50)  not null unique,
  fabricante              varchar(100),
  modelo                  varchar(100),
  tipo_sensor             varchar(100) not null,
  unidade_medida          varchar(10)  not null,
  protocolo_comunicacao   varchar(50)  not null,
  mac_address             varchar(17)  not null unique,
  endereco_ip             varchar(45),
  token_autenticacao      varchar(255) unique,          -- nunca devolvido pela API
  status_conexao          varchar(10)  not null,
  data_instalacao         date,
  data_ultima_calibracao  date,
  status                  varchar(15)  not null,
  id_maquina              int not null references public.maquina(id_maquina) on delete cascade,
  ativo                   boolean default true,
  constraint chk_status_conexao check (status_conexao in ('online','offline','unknown','erro')),
  constraint chk_status_sensor  check (status in ('ativo','inativo','manutencao')),
  constraint chk_mac_formato    check (mac_address ~ '^([0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}$'),
  constraint chk_ip_formato     check (
    endereco_ip is null
    or endereco_ip ~ '^((25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$'
    or endereco_ip ~ '^([0-9a-fA-F]{0,4}:){2,7}[0-9a-fA-F]{0,4}$'),
  constraint chk_datas_sensor   check (
    data_instalacao is null or data_ultima_calibracao is null or data_ultima_calibracao >= data_instalacao)
);

-- CONSUMO: energia de uma máquina em um período (N:1 máquina)
create table public.consumo (
  id_consumo   serial primary key,
  data_inicio  timestamp not null,
  data_fim     timestamp not null,
  consumo_kwh  numeric(12,2) not null,
  id_maquina   int not null references public.maquina(id_maquina) on delete cascade,
  constraint chk_periodo_consumo  check (data_fim > data_inicio),
  constraint chk_consumo_positivo check (consumo_kwh >= 0),
  constraint uq_consumo_periodo   unique (id_maquina, data_inicio, data_fim)
);

-- LEITURA: medição individual de um sensor (N:1 sensor, usuário e consumo)
create table public.leitura (
  id_leitura          serial primary key,
  data_leitura        timestamp not null default (now() at time zone 'America/Sao_Paulo'),
  valor_medido_kwh    numeric(12,2) not null,           -- energia medida no intervalo da leitura
  observacao_leitura  text,
  id_sensor           int not null references public.sensor(id_sensor)   on delete cascade,
  id_usuario          int          references public.usuario(id_usuario) on delete set null,
  id_consumo          int          references public.consumo(id_consumo) on delete set null,
  constraint chk_valor_leitura_positivo check (valor_medido_kwh >= 0),
  unique (id_sensor, data_leitura)
);

-- DECISAO: regra de decisão da empresa (catálogo)
create table public.decisao (
  id_decisao         serial primary key,
  nome_decisao       varchar(100)  not null,
  descricao_decisao  text,
  criterio_acionado  varchar(150)  not null,            -- 'valor_medido_kwh' (leitura) ou 'consumo_kwh' (consumo)
  operador           varchar(2)    not null,
  limite_referencia  numeric(12,2) not null,
  unidade_limite     varchar(10)   not null,
  ativo              boolean default true,
  id_empresa         int references public.empresa(id_empresa) on delete cascade,
  constraint chk_operador check (operador in ('>','<','>=','<=','=')),
  constraint uq_decisao_empresa_nome unique (id_empresa, nome_decisao)
);

-- TOMADA_DECISAO: acionamento real de uma regra (N:1 decisão, leitura, consumo)
create table public.tomada_decisao (
  id_tomada_decisao    serial primary key,
  data_tomada_decisao  timestamp not null default (now() at time zone 'America/Sao_Paulo'),
  valor_referencia     numeric(12,2) not null,
  status_execucao      varchar(15) not null,
  observacao           text,
  id_decisao           int not null references public.decisao(id_decisao) on delete restrict,
  id_leitura           int          references public.leitura(id_leitura) on delete set null,
  id_consumo           int          references public.consumo(id_consumo) on delete set null,
  constraint chk_status_execucao check (status_execucao in ('pendente','executada','cancelada','falha'))
);

-- CONVITE_USUARIO: administrador cadastra membros da equipe na empresa
create table public.convite_usuario (
  id_convite    serial primary key,
  id_empresa    int not null references public.empresa(id_empresa) on delete cascade,
  email         varchar(100) not null,
  nome_usuario  varchar(100) not null,
  tipo_usuario  varchar(20)  not null,
  codigo        uuid not null unique default gen_random_uuid(),
  criado_em     timestamp not null default (now() at time zone 'America/Sao_Paulo'),
  usado_em      timestamp,
  constraint chk_convite_tipo check (tipo_usuario in ('Administrador','Operador','Visualizador'))
);

-- ---------------------------------------------------------------------
-- 2. ÍNDICES
-- ---------------------------------------------------------------------
create index idx_usuario_empresa         on public.usuario(id_empresa);
create index idx_setor_responsavel       on public.setor(id_usuario_responsavel);
create index idx_setor_empresa           on public.setor(id_empresa);
create index idx_maquina_setor           on public.maquina(id_setor);
create index idx_sensor_maquina          on public.sensor(id_maquina);
create index idx_consumo_maquina_periodo on public.consumo(id_maquina, data_inicio, data_fim);
create index idx_leitura_data            on public.leitura(data_leitura);
create index idx_leitura_sensor          on public.leitura(id_sensor);
create index idx_leitura_consumo         on public.leitura(id_consumo);
create index idx_decisao_empresa         on public.decisao(id_empresa);
create index idx_tomada_decisao_data     on public.tomada_decisao(data_tomada_decisao);
create index idx_tomada_decisao_decisao  on public.tomada_decisao(id_decisao);
create index idx_convite_empresa         on public.convite_usuario(id_empresa);

-- ---------------------------------------------------------------------
-- 3. FUNÇÕES DE CONTEXTO (quem está autenticado e a qual empresa pertence)
-- ---------------------------------------------------------------------
create function public.kv_empresa_atual() returns int language sql stable security definer set search_path = '' as $$
  select u.id_empresa from public.usuario u where u.auth_user_id = auth.uid() and u.ativo limit 1 $$;
create function public.kv_usuario_atual() returns int language sql stable security definer set search_path = '' as $$
  select u.id_usuario from public.usuario u where u.auth_user_id = auth.uid() and u.ativo limit 1 $$;
create function public.kv_papel_atual() returns text language sql stable security definer set search_path = '' as $$
  select u.tipo_usuario::text from public.usuario u where u.auth_user_id = auth.uid() and u.ativo limit 1 $$;
create function public.kv_is_admin() returns boolean language sql stable security definer set search_path = '' as $$
  select coalesce(public.kv_papel_atual() = 'Administrador', false) $$;
create function public.kv_pode_operar() returns boolean language sql stable security definer set search_path = '' as $$
  select coalesce(public.kv_papel_atual() in ('Administrador','Operador'), false) $$;
create function public.kv_empresa_do_setor(p_id int) returns int language sql stable security definer set search_path = '' as $$
  select id_empresa from public.setor where id_setor = p_id $$;
create function public.kv_empresa_da_maquina(p_id int) returns int language sql stable security definer set search_path = '' as $$
  select s.id_empresa from public.maquina m join public.setor s on s.id_setor = m.id_setor where m.id_maquina = p_id $$;
create function public.kv_empresa_do_sensor(p_id int) returns int language sql stable security definer set search_path = '' as $$
  select s.id_empresa from public.sensor se join public.maquina m on m.id_maquina = se.id_maquina
    join public.setor s on s.id_setor = m.id_setor where se.id_sensor = p_id $$;
create function public.kv_empresa_do_consumo(p_id int) returns int language sql stable security definer set search_path = '' as $$
  select public.kv_empresa_da_maquina(c.id_maquina) from public.consumo c where c.id_consumo = p_id $$;
create function public.kv_empresa_do_usuario(p_id int) returns int language sql stable security definer set search_path = '' as $$
  select id_empresa from public.usuario where id_usuario = p_id $$;
create function public.kv_empresa_da_decisao(p_id int) returns int language sql stable security definer set search_path = '' as $$
  select id_empresa from public.decisao where id_decisao = p_id $$;

-- Perfil completo do usuário autenticado (usado pela API a cada requisição)
create function public.kv_perfil_atual() returns json language sql stable security definer set search_path = '' as $$
  select json_build_object(
    'id_usuario', u.id_usuario, 'nome_usuario', u.nome_usuario, 'email_usuario', u.email_usuario,
    'tipo_usuario', u.tipo_usuario, 'id_empresa', u.id_empresa,
    'nome_empresa', e.nome_empresa, 'tarifa_kwh', e.tarifa_kwh)
    from public.usuario u join public.empresa e on e.id_empresa = u.id_empresa
   where u.auth_user_id = auth.uid() and u.ativo
   limit 1 $$;

-- ---------------------------------------------------------------------
-- 4. VALIDAÇÕES E REGRAS DE NEGÓCIO
-- ---------------------------------------------------------------------
create function public.kv_cnpj_valido(p text) returns boolean language plpgsql immutable set search_path = '' as $$
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

create function public.kv_formatar_cnpj(p text) returns text language sql immutable set search_path = '' as $$
  select case when length(d) = 14
    then substr(d,1,2)||'.'||substr(d,3,3)||'.'||substr(d,6,3)||'/'||substr(d,9,4)||'-'||substr(d,13,2) end
  from (select regexp_replace(coalesce(p,''), '\D', '', 'g') as d) x $$;

create function public.kv_formatar_telefone(p text) returns text language plpgsql immutable set search_path = '' as $$
declare d text := regexp_replace(coalesce(p,''), '\D', '', 'g');
begin
  if length(d) in (12,13) and left(d,2) = '55' then d := substr(d,3); end if;
  if length(d) = 11 then return '('||substr(d,1,2)||') '||substr(d,3,5)||'-'||substr(d,8); end if;
  if length(d) = 10 then return '('||substr(d,1,2)||') '||substr(d,3,4)||'-'||substr(d,7); end if;
  return null;
end $$;

create function public.kv_comparar(v numeric, op text, limite numeric) returns boolean language sql immutable set search_path = '' as $$
  select case op when '>' then v > limite when '>=' then v >= limite
                 when '<' then v < limite when '<=' then v <= limite
                 when '=' then v = limite else false end $$;

-- Cadastro pelo Supabase Auth: "empresa" (nova empresa + administrador) ou "convite" (membro da equipe)
create function public.kv_handle_new_user() returns trigger language plpgsql security definer set search_path = '' as $$
declare
  m jsonb := coalesce(new.raw_user_meta_data, '{}'::jsonb);
  v_cnpj text; v_tel text; v_nome text; v_resp text; v_emp int;
  v_conv public.convite_usuario%rowtype;
begin
  if coalesce(m->>'kv_cadastro', '') = 'convite' then
    select * into v_conv from public.convite_usuario
     where codigo::text = m->>'codigo' and lower(email) = lower(new.email) and usado_em is null
       and criado_em > (now() at time zone 'America/Sao_Paulo') - interval '7 days'
     for update;
    if v_conv.id_convite is null then raise exception 'KV_CONVITE_INVALIDO' using errcode = '22023'; end if;
    if exists (select 1 from public.usuario where lower(email_usuario) = lower(new.email)) then
      raise exception 'KV_EMAIL_EM_USO' using errcode = '23505';
    end if;
    insert into public.usuario (nome_usuario, email_usuario, tipo_usuario, id_empresa, auth_user_id)
    values (v_conv.nome_usuario, new.email, v_conv.tipo_usuario, v_conv.id_empresa, new.id);
    update public.convite_usuario set usado_em = now() at time zone 'America/Sao_Paulo' where id_convite = v_conv.id_convite;
    return new;
  end if;
  if coalesce(m->>'kv_cadastro', '') <> 'empresa' then return new; end if;
  if not public.kv_cnpj_valido(m->>'cnpj') then raise exception 'KV_CNPJ_INVALIDO' using errcode = '22023'; end if;
  v_cnpj := public.kv_formatar_cnpj(m->>'cnpj');
  v_tel  := public.kv_formatar_telefone(m->>'telefone');
  if v_tel is null then raise exception 'KV_TELEFONE_INVALIDO' using errcode = '22023'; end if;
  v_nome := nullif(btrim(m->>'nome_empresa'), '');
  if v_nome is null or length(v_nome) > 100 then raise exception 'KV_NOME_INVALIDO' using errcode = '22023'; end if;
  v_resp := coalesce(nullif(btrim(m->>'nome_usuario'), ''), v_nome);
  if exists (select 1 from public.empresa where cnpj = v_cnpj) then raise exception 'KV_CNPJ_EM_USO' using errcode = '23505'; end if;
  if exists (select 1 from public.empresa where lower(email_empresa) = lower(new.email))
     or exists (select 1 from public.usuario where lower(email_usuario) = lower(new.email)) then
    raise exception 'KV_EMAIL_EM_USO' using errcode = '23505';
  end if;
  insert into public.empresa (cnpj, nome_empresa, email_empresa, telefone_empresa)
  values (v_cnpj, v_nome, new.email, v_tel) returning id_empresa into v_emp;
  insert into public.usuario (nome_usuario, email_usuario, tipo_usuario, id_empresa, auth_user_id)
  values (left(v_resp, 100), new.email, 'Administrador', v_emp, new.id);
  return new;
end $$;

create function public.kv_verificar_cadastro(p_cnpj text, p_email text) returns json language sql stable security definer set search_path = '' as $$
  select json_build_object(
    'cnpj_valido',  public.kv_cnpj_valido(p_cnpj),
    'cnpj_em_uso',  exists (select 1 from public.empresa where cnpj = public.kv_formatar_cnpj(p_cnpj)),
    'email_em_uso', exists (select 1 from public.empresa where lower(email_empresa) = lower(btrim(p_email)))
                 or exists (select 1 from public.usuario where lower(email_usuario) = lower(btrim(p_email)))) $$;

-- A empresa do registro é sempre a do usuário autenticado (o cliente não escolhe)
create function public.kv_definir_empresa() returns trigger language plpgsql security definer set search_path = '' as $$
declare v_emp int := public.kv_empresa_atual();
begin
  if v_emp is not null then new.id_empresa := v_emp;
  elsif tg_table_name = 'setor' and new.id_empresa is null then
    new.id_empresa := public.kv_empresa_do_usuario(new.id_usuario_responsavel);
  end if;
  return new;
end $$;

create function public.kv_validar_responsavel_setor() returns trigger language plpgsql security definer set search_path = '' as $$
begin
  if public.kv_empresa_do_usuario(new.id_usuario_responsavel) is distinct from new.id_empresa then
    raise exception 'KV_RESPONSAVEL_OUTRA_EMPRESA' using errcode = '23503';
  end if;
  return new;
end $$;

-- Agregação: leituras da máquina dentro do período ficam vinculadas ao consumo
create function public.kv_agregar_consumo() returns trigger language plpgsql security definer set search_path = '' as $$
begin
  update public.leitura l set id_consumo = null
   where l.id_consumo = new.id_consumo
     and (l.data_leitura < new.data_inicio or l.data_leitura > new.data_fim
          or not exists (select 1 from public.sensor s where s.id_sensor = l.id_sensor and s.id_maquina = new.id_maquina));
  update public.leitura l set id_consumo = new.id_consumo
    from public.sensor s
   where s.id_sensor = l.id_sensor and s.id_maquina = new.id_maquina
     and l.id_consumo is null and l.data_leitura between new.data_inicio and new.data_fim;
  return null;
end $$;

create function public.kv_vincular_leitura() returns trigger language plpgsql security definer set search_path = '' as $$
begin
  if tg_op = 'INSERT' and new.id_consumo is not null then return new; end if;
  select c.id_consumo into new.id_consumo
    from public.consumo c join public.sensor s on s.id_maquina = c.id_maquina
   where s.id_sensor = new.id_sensor and new.data_leitura between c.data_inicio and c.data_fim
   order by c.data_inicio limit 1;
  return new;
end $$;

-- Motor de decisão: regras ativas em kWh avaliadas a cada leitura / consumo
create function public.kv_avaliar_leitura() returns trigger language plpgsql security definer set search_path = '' as $$
declare v_emp int := public.kv_empresa_do_sensor(new.id_sensor);
begin
  insert into public.tomada_decisao (valor_referencia, status_execucao, observacao, id_decisao, id_leitura)
  select new.valor_medido_kwh, 'pendente',
         'Acionada automaticamente: leitura de ' || to_char(new.valor_medido_kwh, 'FM999999990.00')
           || ' kWh ' || d.operador || ' ' || to_char(d.limite_referencia, 'FM999999990.00') || ' kWh',
         d.id_decisao, new.id_leitura
    from public.decisao d
   where d.id_empresa = v_emp and d.ativo and lower(d.unidade_limite) = 'kwh'
     and (lower(d.criterio_acionado) like '%valor_medido%' or lower(d.criterio_acionado) like '%leitura%')
     and public.kv_comparar(new.valor_medido_kwh, d.operador, d.limite_referencia);
  return null;
end $$;

create function public.kv_avaliar_consumo() returns trigger language plpgsql security definer set search_path = '' as $$
declare v_emp int := public.kv_empresa_da_maquina(new.id_maquina);
begin
  insert into public.tomada_decisao (valor_referencia, status_execucao, observacao, id_decisao, id_consumo)
  select new.consumo_kwh, 'pendente',
         'Acionada automaticamente: consumo de ' || to_char(new.consumo_kwh, 'FM999999990.00')
           || ' kWh ' || d.operador || ' ' || to_char(d.limite_referencia, 'FM999999990.00') || ' kWh',
         d.id_decisao, new.id_consumo
    from public.decisao d
   where d.id_empresa = v_emp and d.ativo and lower(d.unidade_limite) = 'kwh'
     and lower(d.criterio_acionado) like '%consumo%'
     and public.kv_comparar(new.consumo_kwh, d.operador, d.limite_referencia)
     and not exists (select 1 from public.tomada_decisao t
                      where t.id_decisao = d.id_decisao and t.id_consumo = new.id_consumo and t.valor_referencia = new.consumo_kwh);
  return null;
end $$;

-- Cálculos (respeitam o RLS de quem chama)
create function public.kv_calcular_consumo(p_id_maquina int, p_inicio timestamp, p_fim timestamp)
returns table (total_kwh numeric, leituras bigint) language sql stable security invoker set search_path = '' as $$
  select coalesce(sum(l.valor_medido_kwh), 0)::numeric(12,2), count(l.id_leitura)
    from public.leitura l join public.sensor s on s.id_sensor = l.id_sensor
   where s.id_maquina = p_id_maquina and l.data_leitura between p_inicio and p_fim $$;

create function public.kv_resumo_sensores()
returns table (id_sensor int, total_kwh numeric, hoje_kwh numeric, pico_kwh numeric, qtd_leituras bigint, ultima_leitura timestamp)
language sql stable security invoker set search_path = '' as $$
  select l.id_sensor, coalesce(sum(l.valor_medido_kwh), 0),
         coalesce(sum(l.valor_medido_kwh) filter (where l.data_leitura::date = (now() at time zone 'America/Sao_Paulo')::date), 0),
         coalesce(max(l.valor_medido_kwh), 0), count(*), max(l.data_leitura)
    from public.leitura l group by l.id_sensor $$;

-- Ingestão por sensor físico (token do sensor, sem login de usuário)
create function public.kv_registrar_leitura_sensor(p_token text, p_valor_kwh numeric, p_data_leitura timestamp default null, p_observacao text default null)
returns int language plpgsql security definer set search_path = '' as $$
declare v_sensor int; v_id int;
begin
  if p_token is null or length(p_token) < 8 then raise exception 'KV_TOKEN_INVALIDO' using errcode = '28000'; end if;
  select id_sensor into v_sensor from public.sensor where token_autenticacao = p_token and status = 'ativo' and ativo;
  if v_sensor is null then raise exception 'KV_TOKEN_INVALIDO' using errcode = '28000'; end if;
  if p_valor_kwh is null or p_valor_kwh < 0 then raise exception 'KV_VALOR_INVALIDO' using errcode = '22023'; end if;
  insert into public.leitura (data_leitura, valor_medido_kwh, observacao_leitura, id_sensor)
  values (coalesce(p_data_leitura, now() at time zone 'America/Sao_Paulo'), p_valor_kwh, left(p_observacao, 500), v_sensor)
  returning id_leitura into v_id;
  update public.sensor set status_conexao = 'online' where id_sensor = v_sensor;
  return v_id;
end $$;

-- ---------------------------------------------------------------------
-- 5. TRIGGERS
-- ---------------------------------------------------------------------
create trigger kv_on_auth_user_created after insert on auth.users
  for each row execute function public.kv_handle_new_user();
create trigger kv_setor_empresa     before insert or update on public.setor          for each row execute function public.kv_definir_empresa();
create trigger kv_setor_responsavel before insert or update on public.setor          for each row execute function public.kv_validar_responsavel_setor();
create trigger kv_decisao_empresa   before insert or update on public.decisao        for each row execute function public.kv_definir_empresa();
create trigger kv_convite_empresa   before insert           on public.convite_usuario for each row execute function public.kv_definir_empresa();
create trigger kv_consumo_agregar   after insert or update of data_inicio, data_fim, id_maquina on public.consumo for each row execute function public.kv_agregar_consumo();
create trigger kv_consumo_decisao   after insert or update of consumo_kwh on public.consumo for each row execute function public.kv_avaliar_consumo();
create trigger kv_leitura_vincular  before insert or update of data_leitura, id_sensor on public.leitura for each row execute function public.kv_vincular_leitura();
create trigger kv_leitura_decisao   after insert or update of valor_medido_kwh on public.leitura for each row execute function public.kv_avaliar_leitura();

-- ---------------------------------------------------------------------
-- 6. PERMISSÕES (anon não lê tabelas; senhas e tokens nunca são legíveis)
-- ---------------------------------------------------------------------
revoke all on public.empresa, public.usuario, public.setor, public.maquina, public.sensor, public.leitura,
              public.consumo, public.decisao, public.tomada_decisao, public.convite_usuario from anon, authenticated;

grant select (id_empresa, cnpj, nome_empresa, email_empresa, telefone_empresa, tarifa_kwh) on public.empresa to authenticated;
grant update (nome_empresa, telefone_empresa, tarifa_kwh), delete on public.empresa to authenticated;
grant select (id_usuario, nome_usuario, email_usuario, tipo_usuario, id_empresa, ativo) on public.usuario to authenticated;
grant update (nome_usuario, tipo_usuario, ativo), delete on public.usuario to authenticated;
grant select (id_setor, nome_setor, divisao_setor, id_usuario_responsavel, ativo, id_empresa) on public.setor to authenticated;
grant insert (nome_setor, divisao_setor, id_usuario_responsavel, ativo),
      update (nome_setor, divisao_setor, id_usuario_responsavel, ativo), delete on public.setor to authenticated;
grant select, insert, update, delete on public.maquina to authenticated;
grant select (id_sensor, numero_serie, fabricante, modelo, tipo_sensor, unidade_medida, protocolo_comunicacao, mac_address,
              endereco_ip, status_conexao, data_instalacao, data_ultima_calibracao, status, id_maquina, ativo) on public.sensor to authenticated;
grant insert, update, delete on public.sensor to authenticated;
grant select, insert, update, delete on public.leitura to authenticated;
grant select, insert, update, delete on public.consumo to authenticated;
grant select (id_decisao, nome_decisao, descricao_decisao, criterio_acionado, operador, limite_referencia, unidade_limite, ativo, id_empresa)
  on public.decisao to authenticated;
grant insert (nome_decisao, descricao_decisao, criterio_acionado, operador, limite_referencia, unidade_limite, ativo),
      update (nome_decisao, descricao_decisao, criterio_acionado, operador, limite_referencia, unidade_limite, ativo),
      delete on public.decisao to authenticated;
grant select on public.tomada_decisao to authenticated;
grant update (status_execucao, observacao) on public.tomada_decisao to authenticated;
grant select (id_convite, id_empresa, email, nome_usuario, tipo_usuario, codigo, criado_em, usado_em),
      insert (email, nome_usuario, tipo_usuario), delete on public.convite_usuario to authenticated;
grant usage, select on all sequences in schema public to authenticated;

revoke all on all functions in schema public from public, anon;
grant execute on function
  public.kv_empresa_atual(), public.kv_usuario_atual(), public.kv_papel_atual(), public.kv_is_admin(), public.kv_pode_operar(),
  public.kv_empresa_do_setor(int), public.kv_empresa_da_maquina(int), public.kv_empresa_do_sensor(int),
  public.kv_empresa_do_consumo(int), public.kv_empresa_do_usuario(int), public.kv_empresa_da_decisao(int),
  public.kv_perfil_atual(), public.kv_calcular_consumo(int, timestamp, timestamp), public.kv_resumo_sensores(),
  public.kv_cnpj_valido(text), public.kv_formatar_cnpj(text), public.kv_formatar_telefone(text), public.kv_comparar(numeric, text, numeric)
to authenticated;
grant execute on function public.kv_verificar_cadastro(text, text), public.kv_registrar_leitura_sensor(text, numeric, timestamp, text)
  to anon, authenticated;
revoke execute on function public.kv_handle_new_user(), public.kv_definir_empresa(), public.kv_validar_responsavel_setor(),
  public.kv_agregar_consumo(), public.kv_vincular_leitura(), public.kv_avaliar_leitura(), public.kv_avaliar_consumo()
  from public, anon, authenticated;

-- ---------------------------------------------------------------------
-- 7. ROW LEVEL SECURITY: cada empresa vê e altera somente os próprios dados
--    Administrador: tudo · Operador: leituras e consumos · Visualizador: consulta
-- ---------------------------------------------------------------------
alter table public.empresa         enable row level security;
alter table public.usuario         enable row level security;
alter table public.setor           enable row level security;
alter table public.maquina         enable row level security;
alter table public.sensor          enable row level security;
alter table public.leitura         enable row level security;
alter table public.consumo         enable row level security;
alter table public.decisao         enable row level security;
alter table public.tomada_decisao  enable row level security;
alter table public.convite_usuario enable row level security;

create policy kv_empresa_select on public.empresa for select to authenticated using (id_empresa = (select public.kv_empresa_atual()));
create policy kv_empresa_update on public.empresa for update to authenticated
  using (id_empresa = (select public.kv_empresa_atual()) and (select public.kv_is_admin())) with check (id_empresa = (select public.kv_empresa_atual()));
create policy kv_empresa_delete on public.empresa for delete to authenticated
  using (id_empresa = (select public.kv_empresa_atual()) and (select public.kv_is_admin()));

create policy kv_usuario_select on public.usuario for select to authenticated using (id_empresa = (select public.kv_empresa_atual()));
create policy kv_usuario_update on public.usuario for update to authenticated
  using (id_empresa = (select public.kv_empresa_atual()) and (select public.kv_is_admin())) with check (id_empresa = (select public.kv_empresa_atual()));
create policy kv_usuario_delete on public.usuario for delete to authenticated
  using (id_empresa = (select public.kv_empresa_atual()) and (select public.kv_is_admin()));

create policy kv_setor_select on public.setor for select to authenticated using (id_empresa = (select public.kv_empresa_atual()));
create policy kv_setor_insert on public.setor for insert to authenticated
  with check (id_empresa = (select public.kv_empresa_atual()) and (select public.kv_is_admin()));
create policy kv_setor_update on public.setor for update to authenticated
  using (id_empresa = (select public.kv_empresa_atual()) and (select public.kv_is_admin())) with check (id_empresa = (select public.kv_empresa_atual()));
create policy kv_setor_delete on public.setor for delete to authenticated
  using (id_empresa = (select public.kv_empresa_atual()) and (select public.kv_is_admin()));

create policy kv_maquina_select on public.maquina for select to authenticated
  using (public.kv_empresa_do_setor(id_setor) = (select public.kv_empresa_atual()));
create policy kv_maquina_insert on public.maquina for insert to authenticated
  with check (public.kv_empresa_do_setor(id_setor) = (select public.kv_empresa_atual()) and (select public.kv_is_admin()));
create policy kv_maquina_update on public.maquina for update to authenticated
  using (public.kv_empresa_do_setor(id_setor) = (select public.kv_empresa_atual()) and (select public.kv_is_admin()))
  with check (public.kv_empresa_do_setor(id_setor) = (select public.kv_empresa_atual()));
create policy kv_maquina_delete on public.maquina for delete to authenticated
  using (public.kv_empresa_do_setor(id_setor) = (select public.kv_empresa_atual()) and (select public.kv_is_admin()));

create policy kv_sensor_select on public.sensor for select to authenticated
  using (public.kv_empresa_da_maquina(id_maquina) = (select public.kv_empresa_atual()));
create policy kv_sensor_insert on public.sensor for insert to authenticated
  with check (public.kv_empresa_da_maquina(id_maquina) = (select public.kv_empresa_atual()) and (select public.kv_is_admin()));
create policy kv_sensor_update on public.sensor for update to authenticated
  using (public.kv_empresa_da_maquina(id_maquina) = (select public.kv_empresa_atual()) and (select public.kv_is_admin()))
  with check (public.kv_empresa_da_maquina(id_maquina) = (select public.kv_empresa_atual()));
create policy kv_sensor_delete on public.sensor for delete to authenticated
  using (public.kv_empresa_da_maquina(id_maquina) = (select public.kv_empresa_atual()) and (select public.kv_is_admin()));

create policy kv_leitura_select on public.leitura for select to authenticated
  using (public.kv_empresa_do_sensor(id_sensor) = (select public.kv_empresa_atual()));
create policy kv_leitura_insert on public.leitura for insert to authenticated
  with check (public.kv_empresa_do_sensor(id_sensor) = (select public.kv_empresa_atual()) and (select public.kv_pode_operar())
    and (id_usuario is null or public.kv_empresa_do_usuario(id_usuario) = (select public.kv_empresa_atual()))
    and (id_consumo is null or public.kv_empresa_do_consumo(id_consumo) = (select public.kv_empresa_atual())));
create policy kv_leitura_update on public.leitura for update to authenticated
  using (public.kv_empresa_do_sensor(id_sensor) = (select public.kv_empresa_atual()) and (select public.kv_pode_operar()))
  with check (public.kv_empresa_do_sensor(id_sensor) = (select public.kv_empresa_atual())
    and (id_usuario is null or public.kv_empresa_do_usuario(id_usuario) = (select public.kv_empresa_atual()))
    and (id_consumo is null or public.kv_empresa_do_consumo(id_consumo) = (select public.kv_empresa_atual())));
create policy kv_leitura_delete on public.leitura for delete to authenticated
  using (public.kv_empresa_do_sensor(id_sensor) = (select public.kv_empresa_atual()) and (select public.kv_pode_operar()));

create policy kv_consumo_select on public.consumo for select to authenticated
  using (public.kv_empresa_da_maquina(id_maquina) = (select public.kv_empresa_atual()));
create policy kv_consumo_insert on public.consumo for insert to authenticated
  with check (public.kv_empresa_da_maquina(id_maquina) = (select public.kv_empresa_atual()) and (select public.kv_pode_operar()));
create policy kv_consumo_update on public.consumo for update to authenticated
  using (public.kv_empresa_da_maquina(id_maquina) = (select public.kv_empresa_atual()) and (select public.kv_pode_operar()))
  with check (public.kv_empresa_da_maquina(id_maquina) = (select public.kv_empresa_atual()));
create policy kv_consumo_delete on public.consumo for delete to authenticated
  using (public.kv_empresa_da_maquina(id_maquina) = (select public.kv_empresa_atual()) and (select public.kv_pode_operar()));

create policy kv_decisao_select on public.decisao for select to authenticated using (id_empresa = (select public.kv_empresa_atual()));
create policy kv_decisao_insert on public.decisao for insert to authenticated
  with check (id_empresa = (select public.kv_empresa_atual()) and (select public.kv_is_admin()));
create policy kv_decisao_update on public.decisao for update to authenticated
  using (id_empresa = (select public.kv_empresa_atual()) and (select public.kv_is_admin())) with check (id_empresa = (select public.kv_empresa_atual()));
create policy kv_decisao_delete on public.decisao for delete to authenticated
  using (id_empresa = (select public.kv_empresa_atual()) and (select public.kv_is_admin()));

create policy kv_tomada_select on public.tomada_decisao for select to authenticated
  using (public.kv_empresa_da_decisao(id_decisao) = (select public.kv_empresa_atual()));
create policy kv_tomada_update on public.tomada_decisao for update to authenticated
  using (public.kv_empresa_da_decisao(id_decisao) = (select public.kv_empresa_atual()) and (select public.kv_pode_operar()))
  with check (public.kv_empresa_da_decisao(id_decisao) = (select public.kv_empresa_atual()));

create policy kv_convite_select on public.convite_usuario for select to authenticated
  using (id_empresa = (select public.kv_empresa_atual()) and (select public.kv_is_admin()));
create policy kv_convite_insert on public.convite_usuario for insert to authenticated
  with check (id_empresa = (select public.kv_empresa_atual()) and (select public.kv_is_admin()));
create policy kv_convite_delete on public.convite_usuario for delete to authenticated
  using (id_empresa = (select public.kv_empresa_atual()) and (select public.kv_is_admin()));
