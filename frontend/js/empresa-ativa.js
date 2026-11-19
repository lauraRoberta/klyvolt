// js/empresa-ativa.js - a empresa das telas Painel, Equipe, Minha empresa e Monitoramento
// é sempre a de quem está logado (não há mais lista para escolher).
// Nas telas: window.empresaAtiva.aoMudar(funcao) chama funcao(idDaEmpresa) na hora.
// Carregar depois de api.js e nav.js.
(function () {
  const sessao = sessaoAtual();
  const id = sessao && sessao.empresa ? sessao.empresa.id_empresa : null;

  window.empresaAtiva = {
    erro: null,
    id: () => id,
    aoMudar(funcao) { funcao(id); }
  };
})();
