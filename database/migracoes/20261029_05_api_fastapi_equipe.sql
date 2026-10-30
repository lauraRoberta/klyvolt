-- =====================================================================
-- KLYVOLT · Migração 05 — Suporte à API FastAPI e à gestão da equipe
--   • kv_perfil_atual(): perfil do usuário autenticado (uma chamada por requisição)
--   • convite_usuario: administrador cadastra Operadores/Visualizadores na empresa
--   • Cadastro por convite no trigger do Supabase Auth
--   • Administrador pode editar/remover usuários e excluir a própria empresa
--   • FK setor→responsável: RESTRICT → NO ACTION (permite excluir a empresa inteira)
-- Somente alterações aditivas. Nenhum dado existente é alterado.
-- =====================================================================

-- 1. Perfil do usuário logado (id, nome, e-mail, perfil, empresa e tarifa)
create or replace function public.kv_perfil_atual()
returns json language sql stable security definer set search_path = '' as $$
  select json_build_object(
    'id_usuario', u.id_usuario, 'nome_usuario', u.nome_usuario, 'email_usuario', u.email_usuario,
    'tipo_usuario', u.tipo_usuario, 'id_empresa', u.id_empresa,
    'nome_empresa', e.nome_empresa, 'tarifa_kwh', e.tarifa_kwh)
    from public.usuario u join public.empresa e on e.id_empresa = u.id_empresa
   where u.auth_user_id = auth.uid() and u.ativo
   limit 1
$$;
revoke all on function public.kv_perfil_atual() from public, anon;
grant execute on function public.kv_perfil_atual() to authenticated;

-- 2. Convites de usuários (criados pelo administrador, consumidos no cadastro)
create table if not exists public.convite_usuario (
  id_convite    serial primary key,
  id_empresa    int not null references public.empresa(id_empresa) on delete cascade,
  email         varchar(100) not null,
  nome_usuario  varchar(100) not null,
  tipo_usuario  varchar(20)  not null
                constraint chk_convite_tipo check (tipo_usuario in ('Administrador','Operador','Visualizador')),
  codigo        uuid not null unique default gen_random_uuid(),
  criado_em     timestamp not null default (now() at time zone 'America/Sao_Paulo'),
  usado_em      timestamp
);
create index if not exists idx_convite_empresa on public.convite_usuario(id_empresa);
comment on table public.convite_usuario is 'Convite de usuário: o código secreto só é usado pela API para vincular a nova conta à empresa';

alter table public.convite_usuario enable row level security;
revoke all on public.convite_usuario from anon, authenticated;
grant select (id_convite, id_empresa, email, nome_usuario, tipo_usuario, codigo, criado_em, usado_em),
      insert (email, nome_usuario, tipo_usuario),
      delete on public.convite_usuario to authenticated;
grant usage, select on sequence public.convite_usuario_id_convite_seq to authenticated;

create policy kv_convite_select on public.convite_usuario for select to authenticated
  using (id_empresa = (select public.kv_empresa_atual()) and (select public.kv_is_admin()));
create policy kv_convite_insert on public.convite_usuario for insert to authenticated
  with check (id_empresa = (select public.kv_empresa_atual()) and (select public.kv_is_admin()));
create policy kv_convite_delete on public.convite_usuario for delete to authenticated
  using (id_empresa = (select public.kv_empresa_atual()) and (select public.kv_is_admin()));

drop trigger if exists kv_convite_empresa on public.convite_usuario;
create trigger kv_convite_empresa before insert on public.convite_usuario
  for each row execute function public.kv_definir_empresa();

-- 3. Trigger de cadastro: além de "empresa", aceita "convite"
create or replace function public.kv_handle_new_user()
returns trigger language plpgsql security definer set search_path = '' as $$
declare
  m jsonb := coalesce(new.raw_user_meta_data, '{}'::jsonb);
  v_cnpj text; v_tel text; v_nome text; v_resp text; v_emp int;
  v_conv public.convite_usuario%rowtype;
begin
  if coalesce(m->>'kv_cadastro', '') = 'convite' then
    select * into v_conv from public.convite_usuario
     where codigo::text = m->>'codigo'
       and lower(email) = lower(new.email)
       and usado_em is null
       and criado_em > (now() at time zone 'America/Sao_Paulo') - interval '7 days'
     for update;
    if v_conv.id_convite is null then
      raise exception 'KV_CONVITE_INVALIDO' using errcode = '22023';
    end if;
    if exists (select 1 from public.usuario where lower(email_usuario) = lower(new.email)) then
      raise exception 'KV_EMAIL_EM_USO' using errcode = '23505';
    end if;
    insert into public.usuario (nome_usuario, email_usuario, tipo_usuario, id_empresa, auth_user_id)
    values (v_conv.nome_usuario, new.email, v_conv.tipo_usuario, v_conv.id_empresa, new.id);
    update public.convite_usuario set usado_em = now() at time zone 'America/Sao_Paulo' where id_convite = v_conv.id_convite;
    return new;
  end if;

  if coalesce(m->>'kv_cadastro', '') <> 'empresa' then
    return new;
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
revoke execute on function public.kv_handle_new_user() from public, anon, authenticated;

-- 4. Administrador gerencia a equipe (editar nome/perfil/ativo e remover)
grant update (nome_usuario, tipo_usuario, ativo), delete on public.usuario to authenticated;
create policy kv_usuario_update on public.usuario for update to authenticated
  using (id_empresa = (select public.kv_empresa_atual()) and (select public.kv_is_admin()))
  with check (id_empresa = (select public.kv_empresa_atual()));
create policy kv_usuario_delete on public.usuario for delete to authenticated
  using (id_empresa = (select public.kv_empresa_atual()) and (select public.kv_is_admin()));

-- 5. Administrador pode excluir a própria empresa (cascata para todos os dados dela)
grant delete on public.empresa to authenticated;
create policy kv_empresa_delete on public.empresa for delete to authenticated
  using (id_empresa = (select public.kv_empresa_atual()) and (select public.kv_is_admin()));

-- Com RESTRICT, a exclusão em cascata da empresa falhava (setor e usuário removidos
-- na mesma instrução). NO ACTION valida ao fim da instrução: continua impedindo
-- excluir sozinho um usuário que é responsável por setor.
alter table public.setor drop constraint if exists setor_id_usuario_responsavel_fkey;
alter table public.setor add constraint setor_id_usuario_responsavel_fkey
  foreign key (id_usuario_responsavel) references public.usuario(id_usuario) on delete no action;
