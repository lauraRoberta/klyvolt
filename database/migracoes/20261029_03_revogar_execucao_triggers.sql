-- KLYVOLT · Migração 03 — Funções de trigger não podem ser chamadas via API (/rpc).
-- (Triggers continuam funcionando: o privilégio EXECUTE não é exigido no disparo.)
revoke execute on function
  public.kv_handle_new_user(), public.kv_definir_empresa(), public.kv_validar_responsavel_setor(),
  public.kv_agregar_consumo(), public.kv_vincular_leitura(),
  public.kv_avaliar_leitura(), public.kv_avaliar_consumo()
from public, anon, authenticated;
