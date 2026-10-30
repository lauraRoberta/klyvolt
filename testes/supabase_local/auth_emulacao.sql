-- Emulação mínima do ambiente Supabase (SOMENTE para o banco local de testes).
-- No Supabase real, o esquema auth e os papéis anon/authenticated já existem.
do $$ begin
  if not exists (select 1 from pg_roles where rolname = 'anon') then create role anon nologin; end if;
  if not exists (select 1 from pg_roles where rolname = 'authenticated') then create role authenticated nologin; end if;
end $$;
create schema auth;
create table auth.users (
  id uuid primary key default gen_random_uuid(), instance_id uuid, aud text, role text,
  email text unique, encrypted_password text, email_confirmed_at timestamptz,
  raw_user_meta_data jsonb default '{}'::jsonb, created_at timestamptz default now());
create function auth.uid() returns uuid language sql stable as $$
  select nullif(nullif(current_setting('request.jwt.claims', true), '')::json->>'sub', '')::uuid $$;
grant usage on schema auth to anon, authenticated;
grant execute on function auth.uid() to anon, authenticated;
grant usage on schema public to anon, authenticated;
