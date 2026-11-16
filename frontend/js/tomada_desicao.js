// js/tomada-decisao.js - regra específica da tela de tomada de decisão (carregar antes de crud.js).
// A API devolve só o NOME da decisão, mas o PUT precisa do id_decisao.
// Ao editar, procuramos a decisão pelo nome na lista carregada no select.
window.crudHooks = {
  transformarRegistro(registro, contexto) {
    const iguais = (contexto.listas.id_decisao || [])
      .filter(d => d.nome_decisao === registro.decisao);
    if (iguais.length !== 1) {
      contexto.avisar('Não foi possível identificar a decisão deste registro. Escolha a decisão no campo antes de salvar.');
    }
    return { ...registro, id_decisao: iguais.length === 1 ? iguais[0].id_decisao : '' };
  }
};
