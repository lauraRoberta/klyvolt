// js/empresa-ativa.js - lista "Empresa" no cabeçalho: escolhe de qual empresa a tela mostra os dados.
// A escolha fica guardada no navegador. Carregar depois de api.js e nav.js.
// Nas telas: window.empresaAtiva.aoMudar(funcao) chama funcao(idDaEmpresa) agora e a cada troca
// (idDaEmpresa é null se não houver empresa). window.empresaAtiva.erro traz a mensagem se a lista falhou.
(function () {
  const CHAVE = 'klyvolt_empresa_ativa';
  const ouvintes = [];
  let pronto = false;
  let atual = null;

  window.empresaAtiva = {
    erro: null,
    id: () => atual,
    aoMudar(funcao) {
      ouvintes.push(funcao);
      if (pronto) funcao(atual);
    }
  };

  function avisar() {
    pronto = true;
    for (const funcao of ouvintes) funcao(atual);
  }

  async function iniciar() {
    const destino = document.querySelector('.cabecalho .container');
    if (!destino) return;

    const caixa = document.createElement('div');
    caixa.className = 'empresa-ativa';
    const rotulo = document.createElement('label');
    rotulo.setAttribute('for', 'seletor-empresa');
    rotulo.textContent = 'Empresa';
    const seletor = document.createElement('select');
    seletor.id = 'seletor-empresa';
    caixa.append(rotulo, seletor);
    // fica na primeira linha do cabeçalho, antes do menu
    destino.insertBefore(caixa, destino.querySelector('.menu'));

    let empresas = [];
    try {
      empresas = await requisicao('/empresas');
    } catch (erro) {
      window.empresaAtiva.erro = erro.message;
      seletor.append(new Option('Sem conexão com a API', ''));
      seletor.disabled = true;
      avisar();
      return;
    }

    if (empresas.length === 0) {
      seletor.append(new Option('Nenhuma empresa cadastrada', ''));
      seletor.disabled = true;
      avisar();
      return;
    }

    empresas.sort((a, b) => a.id_empresa - b.id_empresa);
    for (const empresa of empresas) {
      seletor.append(new Option(empresa.nome_empresa, String(empresa.id_empresa)));
    }

    // usa a empresa escolhida da última vez, se ainda existir
    const guardada = localStorage.getItem(CHAVE);
    const existe = empresas.some(e => String(e.id_empresa) === guardada);
    seletor.value = existe ? guardada : String(empresas[0].id_empresa);
    atual = Number(seletor.value);
    localStorage.setItem(CHAVE, String(atual));

    seletor.addEventListener('change', () => {
      atual = Number(seletor.value);
      localStorage.setItem(CHAVE, String(atual));
      avisar();
    });
    avisar();
  }

  iniciar();
})();