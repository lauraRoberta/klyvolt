-- =====================================================================
-- KLYVOLT · PENDENTE DE APROVAÇÃO — NÃO FOI EXECUTADO
-- Remove os dados de teste/simulação gravados antes da integração.
--
-- Situação atual (29/10/2026): 14 empresas, 11 usuários, 11 setores,
-- 12 máquinas, 11 sensores, 931 leituras (926 marcadas "leitura simulada"),
-- 3 consumos, 16 regras de decisão sem empresa e 10 acionamentos.
-- Nenhum desses registros possui conta no Supabase Auth, então NINGUÉM
-- consegue vê-los pela plataforma (o RLS os isola). Eles apenas ocupam o
-- banco e bloqueiam CNPJs/e-mails/MACs já usados.
--
-- ATENÇÃO: confira a lista antes. Se alguma empresa for real (ex.: Muriel
-- Acabamentos, Ana Confecções, Lola Pithola, loca-loca, dapatosSapatonas),
-- retire-a da lista "ids_empresas" — ou não execute este script.
-- Efeito: exclusão permanente (cascata para usuários, setores, máquinas,
-- sensores, leituras e consumos dessas empresas).
-- =====================================================================
begin;

-- 1) Conferência (execute sozinho primeiro):
-- select id_empresa, nome_empresa, email_empresa from public.empresa order by id_empresa;

-- 2) Empresas a remover (ajuste conforme a conferência)
create temporary table ids_empresas on commit drop as
select id_empresa from public.empresa
 where id_empresa not in (select u.id_empresa from public.usuario u where u.auth_user_id is not null);

-- Acionamentos e regras antigas sem empresa
delete from public.tomada_decisao where id_decisao in (select id_decisao from public.decisao where id_empresa is null);
delete from public.decisao where id_empresa is null;

-- Setores têm responsável com ON DELETE RESTRICT: remove setores antes dos usuários
delete from public.setor where id_empresa in (select id_empresa from ids_empresas);
delete from public.empresa where id_empresa in (select id_empresa from ids_empresas);

commit;
