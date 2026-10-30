-- =====================================================================
-- KLYVOLT · PENDENTE DE APROVAÇÃO — NÃO FOI EXECUTADO
-- Remove senhas antigas das tabelas empresa/usuario.
--
-- Motivo: 7 empresas e 7 usuários de teste têm senha gravada em TEXTO PURO
-- (ex.: valores começando com "senh..."), e os demais têm hash bcrypt da
-- API antiga. Com o Supabase Auth, essas colunas não são mais usadas para
-- login e já estão bloqueadas para leitura pela API (GRANT por coluna).
-- Mesmo assim, guardar senhas em texto puro no banco é um risco.
--
-- Efeito: apaga o conteúdo das colunas senha_empresa e senha_usuario
-- (irreversível). Nenhum outro dado é alterado.
-- =====================================================================
begin;
update public.empresa set senha_empresa = null where senha_empresa is not null;
update public.usuario set senha_usuario = null where senha_usuario is not null;
-- Opcional (recomendado depois de validar a plataforma):
-- alter table public.empresa drop column senha_empresa;
-- alter table public.usuario drop column senha_usuario;
commit;
