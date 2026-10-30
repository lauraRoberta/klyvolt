-- =====================================================================
-- KLYVOLT · Migração 01 — Multiempresa, Supabase Auth e RLS
-- Somente alterações ADITIVAS ou que relaxam restrições.
-- Nenhuma linha existente é apagada.
-- =====================================================================

-- ---------------------------------------------------------------------
-- 1. Vínculo com o Supabase Auth e novos campos
-- ---------------------------------------------------------------------
alter table public.usuario
  add column if not exists auth_user_id uuid unique references auth.users(id) on delete set null;

-- As senhas passam a ser geridas pelo Supabase Auth (nunca mais em tabela própria).
alter table public.usuario alter column senha_usuario drop not null;
alter table public.empresa alter column senha_empresa drop not null;

-- Tarifa de energia da empresa (R$/kWh), usada nos cálculos de custo.
alter table public.empresa
  add column if not exists tarifa_kwh numeric(10,4)
  constraint chk_tarifa_kwh check (tarifa_kwh is null or tarifa_kwh >= 0);

-- ---------------------------------------------------------------------
-- 2. Setor passa a pertencer explicitamente a uma empresa
--    (backfill pela empresa do usuário responsável)
-- ---------------------------------------------------------------------
alter table public.setor
  add column if not exists id_empresa int references public.empresa(id_empresa) on delete cascade;

update public.setor s
   set id_empresa = u.id_empresa
  from public.usuario u
 where u.id_usuario = s.id_usuario_responsavel
   and s.id_empresa is null;

alter table public.setor alter column id_empresa set not null;
create index if not exists idx_setor_empresa on public.setor(id_empresa);

-- Nome de setor era único no sistema inteiro (impedia duas empresas de terem "Corte").
alter table public.setor drop constraint if exists uq_setor_nome;
alter table public.setor
  add constraint uq_setor_empresa_nome unique (id_empresa, nome_setor);

-- ---------------------------------------------------------------------
-- 3. Regras de decisão passam a pertencer a uma empresa.
--    Regras antigas ficam com id_empresa NULL (preservadas, porém não
--    visíveis nem aplicadas a nenhuma empresa até serem atribuídas).
-- ---------------------------------------------------------------------
alter table public.decisao
  add column if not exists id_empresa int references public.empresa(id_empresa) on delete cascade;
create index if not exists idx_decisao_empresa on public.decisao(id_empresa);

alter table public.decisao drop constraint if exists decisao_nome_decisao_key;
alter table public.decisao
  add constraint uq_decisao_empresa_nome unique (id_empresa, nome_decisao);

-- ---------------------------------------------------------------------
-- 4. Datas gravadas no horário de Brasília (colunas são timestamp sem fuso;
--    o front-end envia horário local). Antes o padrão gravava em UTC.
-- ---------------------------------------------------------------------
alter table public.leitura
  alter column data_leitura set default (now() at time zone 'America/Sao_Paulo');
alter table public.tomada_decisao
  alter column data_tomada_decisao set default (now() at time zone 'America/Sao_Paulo');

-- ---------------------------------------------------------------------
-- 5. Funções auxiliares de contexto (quem é o usuário logado)
-- ---------------------------------------------------------------------
create or replace function public.kv_empresa_atual()
returns int language sql stable security definer set search_path = '' as $$
  select u.id_empresa from public.usuario u
   where u.auth_user_id = auth.uid() and u.ativo
   limit 1
$$;

create or replace function public.kv_usuario_atual()
returns int language sql stable security definer set search_path = '' as $$
  select u.id_usuario from public.usuario u
   where u.auth_user_id = auth.uid() and u.ativo
   limit 1
$$;

create or replace function public.kv_papel_atual()
returns text language sql stable security definer set search_path = '' as $$
  select u.tipo_usuario::text from public.usuario u
   where u.auth_user_id = auth.uid() and u.ativo
   limit 1
$$;

create or replace function public.kv_is_admin()
returns boolean language sql stable security definer set search_path = '' as $$
  select coalesce(public.kv_papel_atual() = 'Administrador', false)
$$;

-- Administrador e Operador registram leituras e consumos; Visualizador só consulta.
create or replace function public.kv_pode_operar()
returns boolean language sql stable security definer set search_path = '' as $$
  select coalesce(public.kv_papel_atual() in ('Administrador','Operador'), false)
$$;

-- Empresa dona de cada registro (resolvido sem passar pelo RLS, para evitar
-- recursão e manter as políticas rápidas).
create or replace function public.kv_empresa_do_setor(p_id int)
returns int language sql stable security definer set search_path = '' as $$
  select id_empresa from public.setor where id_setor = p_id
$$;

create or replace function public.kv_empresa_da_maquina(p_id int)
returns int language sql stable security definer set search_path = '' as $$
  select s.id_empresa from public.maquina m join public.setor s on s.id_setor = m.id_setor
   where m.id_maquina = p_id
$$;

create or replace function public.kv_empresa_do_sensor(p_id int)
returns int language sql stable security definer set search_path = '' as $$
  select s.id_empresa from public.sensor se
    join public.maquina m on m.id_maquina = se.id_maquina
    join public.setor s on s.id_setor = m.id_setor
   where se.id_sensor = p_id
$$;

create or replace function public.kv_empresa_do_consumo(p_id int)
returns int language sql stable security definer set search_path = '' as $$
  select public.kv_empresa_da_maquina(c.id_maquina) from public.consumo c where c.id_consumo = p_id
$$;

create or replace function public.kv_empresa_do_usuario(p_id int)
returns int language sql stable security definer set search_path = '' as $$
  select id_empresa from public.usuario where id_usuario = p_id
$$;

create or replace function public.kv_empresa_da_decisao(p_id int)
returns int language sql stable security definer set search_path = '' as $$
  select id_empresa from public.decisao where id_decisao = p_id
$$;

revoke all on function
  public.kv_empresa_atual(), public.kv_usuario_atual(), public.kv_papel_atual(),
  public.kv_is_admin(), public.kv_pode_operar(),
  public.kv_empresa_do_setor(int), public.kv_empresa_da_maquina(int),
  public.kv_empresa_do_sensor(int), public.kv_empresa_do_consumo(int),
  public.kv_empresa_do_usuario(int), public.kv_empresa_da_decisao(int)
from public, anon;
grant execute on function
  public.kv_empresa_atual(), public.kv_usuario_atual(), public.kv_papel_atual(),
  public.kv_is_admin(), public.kv_pode_operar(),
  public.kv_empresa_do_setor(int), public.kv_empresa_da_maquina(int),
  public.kv_empresa_do_sensor(int), public.kv_empresa_do_consumo(int),
  public.kv_empresa_do_usuario(int), public.kv_empresa_da_decisao(int)
to authenticated;

-- ---------------------------------------------------------------------
-- 6. Privilégios: anon não acessa nenhuma tabela; authenticated acessa
--    apenas as colunas necessárias (senhas e tokens nunca são lidos).
-- ---------------------------------------------------------------------
revoke all on public.empresa, public.usuario, public.setor, public.maquina,
              public.sensor, public.leitura, public.consumo, public.decisao,
              public.tomada_decisao
  from anon, authenticated;

grant select (id_empresa, cnpj, nome_empresa, email_empresa, telefone_empresa, tarifa_kwh)
  on public.empresa to authenticated;
grant update (nome_empresa, telefone_empresa, tarifa_kwh)
  on public.empresa to authenticated;

grant select (id_usuario, nome_usuario, email_usuario, tipo_usuario, id_empresa, ativo)
  on public.usuario to authenticated;

grant select (id_setor, nome_setor, divisao_setor, id_usuario_responsavel, ativo, id_empresa)
  on public.setor to authenticated;
grant insert (nome_setor, divisao_setor, id_usuario_responsavel, ativo),
      update (nome_setor, divisao_setor, id_usuario_responsavel, ativo),
      delete on public.setor to authenticated;

grant select, insert, update, delete on public.maquina to authenticated;

grant select (id_sensor, numero_serie, fabricante, modelo, tipo_sensor, unidade_medida,
              protocolo_comunicacao, mac_address, endereco_ip, status_conexao,
              data_instalacao, data_ultima_calibracao, status, id_maquina, ativo)
  on public.sensor to authenticated;
grant insert, update, delete on public.sensor to authenticated;

grant select, insert, update, delete on public.leitura to authenticated;
grant select, insert, update, delete on public.consumo to authenticated;

grant select (id_decisao, nome_decisao, descricao_decisao, criterio_acionado, operador,
              limite_referencia, unidade_limite, ativo, id_empresa)
  on public.decisao to authenticated;
grant insert (nome_decisao, descricao_decisao, criterio_acionado, operador,
              limite_referencia, unidade_limite, ativo),
      update (nome_decisao, descricao_decisao, criterio_acionado, operador,
              limite_referencia, unidade_limite, ativo),
      delete on public.decisao to authenticated;

grant select on public.tomada_decisao to authenticated;
grant update (status_execucao, observacao) on public.tomada_decisao to authenticated;

grant usage, select on all sequences in schema public to authenticated;

-- ---------------------------------------------------------------------
-- 7. Políticas RLS (o isolamento entre empresas é feito AQUI, no banco)
-- ---------------------------------------------------------------------
alter table public.empresa        enable row level security;
alter table public.usuario        enable row level security;
alter table public.setor          enable row level security;
alter table public.maquina        enable row level security;
alter table public.sensor         enable row level security;
alter table public.leitura        enable row level security;
alter table public.consumo        enable row level security;
alter table public.decisao        enable row level security;
alter table public.tomada_decisao enable row level security;

-- EMPRESA
create policy kv_empresa_select on public.empresa for select to authenticated
  using (id_empresa = (select public.kv_empresa_atual()));
create policy kv_empresa_update on public.empresa for update to authenticated
  using (id_empresa = (select public.kv_empresa_atual()) and (select public.kv_is_admin()))
  with check (id_empresa = (select public.kv_empresa_atual()));

-- USUARIO (somente leitura da equipe da própria empresa)
create policy kv_usuario_select on public.usuario for select to authenticated
  using (id_empresa = (select public.kv_empresa_atual()));

-- SETOR
create policy kv_setor_select on public.setor for select to authenticated
  using (id_empresa = (select public.kv_empresa_atual()));
create policy kv_setor_insert on public.setor for insert to authenticated
  with check (id_empresa = (select public.kv_empresa_atual()) and (select public.kv_is_admin()));
create policy kv_setor_update on public.setor for update to authenticated
  using (id_empresa = (select public.kv_empresa_atual()) and (select public.kv_is_admin()))
  with check (id_empresa = (select public.kv_empresa_atual()));
create policy kv_setor_delete on public.setor for delete to authenticated
  using (id_empresa = (select public.kv_empresa_atual()) and (select public.kv_is_admin()));

-- MAQUINA
create policy kv_maquina_select on public.maquina for select to authenticated
  using (public.kv_empresa_do_setor(id_setor) = (select public.kv_empresa_atual()));
create policy kv_maquina_insert on public.maquina for insert to authenticated
  with check (public.kv_empresa_do_setor(id_setor) = (select public.kv_empresa_atual()) and (select public.kv_is_admin()));
create policy kv_maquina_update on public.maquina for update to authenticated
  using (public.kv_empresa_do_setor(id_setor) = (select public.kv_empresa_atual()) and (select public.kv_is_admin()))
  with check (public.kv_empresa_do_setor(id_setor) = (select public.kv_empresa_atual()));
create policy kv_maquina_delete on public.maquina for delete to authenticated
  using (public.kv_empresa_do_setor(id_setor) = (select public.kv_empresa_atual()) and (select public.kv_is_admin()));

-- SENSOR
create policy kv_sensor_select on public.sensor for select to authenticated
  using (public.kv_empresa_da_maquina(id_maquina) = (select public.kv_empresa_atual()));
create policy kv_sensor_insert on public.sensor for insert to authenticated
  with check (public.kv_empresa_da_maquina(id_maquina) = (select public.kv_empresa_atual()) and (select public.kv_is_admin()));
create policy kv_sensor_update on public.sensor for update to authenticated
  using (public.kv_empresa_da_maquina(id_maquina) = (select public.kv_empresa_atual()) and (select public.kv_is_admin()))
  with check (public.kv_empresa_da_maquina(id_maquina) = (select public.kv_empresa_atual()));
create policy kv_sensor_delete on public.sensor for delete to authenticated
  using (public.kv_empresa_da_maquina(id_maquina) = (select public.kv_empresa_atual()) and (select public.kv_is_admin()));

-- LEITURA
create policy kv_leitura_select on public.leitura for select to authenticated
  using (public.kv_empresa_do_sensor(id_sensor) = (select public.kv_empresa_atual()));
create policy kv_leitura_insert on public.leitura for insert to authenticated
  with check (
    public.kv_empresa_do_sensor(id_sensor) = (select public.kv_empresa_atual())
    and (select public.kv_pode_operar())
    and (id_usuario is null or public.kv_empresa_do_usuario(id_usuario) = (select public.kv_empresa_atual()))
    and (id_consumo is null or public.kv_empresa_do_consumo(id_consumo) = (select public.kv_empresa_atual())));
create policy kv_leitura_update on public.leitura for update to authenticated
  using (public.kv_empresa_do_sensor(id_sensor) = (select public.kv_empresa_atual()) and (select public.kv_pode_operar()))
  with check (
    public.kv_empresa_do_sensor(id_sensor) = (select public.kv_empresa_atual())
    and (id_usuario is null or public.kv_empresa_do_usuario(id_usuario) = (select public.kv_empresa_atual()))
    and (id_consumo is null or public.kv_empresa_do_consumo(id_consumo) = (select public.kv_empresa_atual())));
create policy kv_leitura_delete on public.leitura for delete to authenticated
  using (public.kv_empresa_do_sensor(id_sensor) = (select public.kv_empresa_atual()) and (select public.kv_pode_operar()));

-- CONSUMO
create policy kv_consumo_select on public.consumo for select to authenticated
  using (public.kv_empresa_da_maquina(id_maquina) = (select public.kv_empresa_atual()));
create policy kv_consumo_insert on public.consumo for insert to authenticated
  with check (public.kv_empresa_da_maquina(id_maquina) = (select public.kv_empresa_atual()) and (select public.kv_pode_operar()));
create policy kv_consumo_update on public.consumo for update to authenticated
  using (public.kv_empresa_da_maquina(id_maquina) = (select public.kv_empresa_atual()) and (select public.kv_pode_operar()))
  with check (public.kv_empresa_da_maquina(id_maquina) = (select public.kv_empresa_atual()));
create policy kv_consumo_delete on public.consumo for delete to authenticated
  using (public.kv_empresa_da_maquina(id_maquina) = (select public.kv_empresa_atual()) and (select public.kv_pode_operar()));

-- DECISAO
create policy kv_decisao_select on public.decisao for select to authenticated
  using (id_empresa = (select public.kv_empresa_atual()));
create policy kv_decisao_insert on public.decisao for insert to authenticated
  with check (id_empresa = (select public.kv_empresa_atual()) and (select public.kv_is_admin()));
create policy kv_decisao_update on public.decisao for update to authenticated
  using (id_empresa = (select public.kv_empresa_atual()) and (select public.kv_is_admin()))
  with check (id_empresa = (select public.kv_empresa_atual()));
create policy kv_decisao_delete on public.decisao for delete to authenticated
  using (id_empresa = (select public.kv_empresa_atual()) and (select public.kv_is_admin()));

-- TOMADA_DECISAO (criada apenas pelo motor de decisão; usuário consulta e atualiza status)
create policy kv_tomada_select on public.tomada_decisao for select to authenticated
  using (public.kv_empresa_da_decisao(id_decisao) = (select public.kv_empresa_atual()));
create policy kv_tomada_update on public.tomada_decisao for update to authenticated
  using (public.kv_empresa_da_decisao(id_decisao) = (select public.kv_empresa_atual()) and (select public.kv_pode_operar()))
  with check (public.kv_empresa_da_decisao(id_decisao) = (select public.kv_empresa_atual()));
