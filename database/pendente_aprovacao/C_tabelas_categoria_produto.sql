-- =====================================================================
-- KLYVOLT · PENDENTE DE APROVAÇÃO — NÃO FOI EXECUTADO
-- As tabelas public.categoria e public.produto existem no projeto, estão
-- vazias, não pertencem ao KLYVOLT e estão SEM RLS (o Supabase as marca
-- como expostas para a chave pública).
--
-- Escolha UMA opção:
-- Opção 1 — bloquear o acesso pela API (não apaga nada):
alter table public.categoria enable row level security;
alter table public.produto   enable row level security;

-- Opção 2 — remover as tabelas (irreversível; descomente para usar):
-- drop table public.produto;
-- drop table public.categoria;
