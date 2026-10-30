-- KLYVOLT · Migração 04 — Histórico de decisões sobrevive à exclusão da origem.
-- Antes: excluir uma leitura/consumo (ou máquina/setor, por cascata) que já tinha
-- acionado uma decisão FALHAVA, porque o FK define id_leitura/id_consumo = NULL e
-- a restrição chk_origem_decisao exigia que um dos dois existisse.
-- Agora: a exclusão funciona e o acionamento permanece no histórico (com a
-- observação descrevendo o valor que o gerou). O motor de decisão continua
-- sempre gravando a origem.
alter table public.tomada_decisao drop constraint if exists chk_origem_decisao;
