// js/equipe.js - usuários da empresa escolhida e a função de cada um.
// Carregar depois de api.js, nav.js e empresa-ativa.js.
(function () {
  const mensagem = document.querySelector('#mensagem');
  const conteudo = document.querySelector('#conteudo');
  const nomeEmpresa = document.querySelector('#nome-empresa');
  const funcoes = document.querySelector('#funcoes');
  const pessoas = document.querySelector('#pessoas');
  const totalPessoas = document.querySelector('#total-pessoas');

  // [nome da função, classe de cor, o que essa função faz]
  const FUNCOES = [
    ['Administrador', 'administrador', 'Cuida da configuração da empresa e da equipe: cadastra setores, máquinas e usuários.'],
    ['Operador', 'operador', 'Acompanha o consumo no dia a dia e registra leituras e decisões.'],
    ['Visualizador', 'visualizador', 'Consulta o painel e os cadastros, sem alterar nada.']
  ];

  function criar(tag, classe, texto) {
    const elemento = document.createElement(tag);
    if (classe) elemento.className = classe;
    if (texto !== undefined) elemento.textContent = texto;
    return elemento;
  }

  function classeDaFuncao(tipo) {
    const achada = FUNCOES.find(f => f[0] === tipo);
    return achada ? achada[1] : 'outra';
  }

  function iniciais(nome) {
    const partes = nome.trim().split(/\s+/);
    const primeira = partes[0] ? partes[0][0] : '';
    const ultima = partes.length > 1 ? partes[partes.length - 1][0] : '';
    return (primeira + ultima).toUpperCase();
  }

  function desenharFuncoes(usuarios) {
    funcoes.replaceChildren();
    FUNCOES.forEach(([nome, , descricao], posicao) => {
      const quantidade = usuarios.filter(u => u.tipo_usuario === nome).length;
      const cartao = criar('div', 'kpi');
      cartao.style.animationDelay = `${posicao * 0.05}s`;
      cartao.append(
        criar('span', 'kpi-rotulo', nome),
        criar('strong', 'kpi-valor', String(quantidade)),
        criar('span', 'kpi-detalhe', descricao)
      );
      funcoes.append(cartao);
    });
  }

  function desenharPessoas(usuarios) {
    pessoas.replaceChildren();
    totalPessoas.textContent = `${usuarios.length} pessoa(s)`;
    if (usuarios.length === 0) {
      pessoas.append(criar('li', 'vazio', 'Nenhum usuário cadastrado nesta empresa.'));
      return;
    }
    const posicaoDaFuncao = tipo => {
      const indice = FUNCOES.findIndex(f => f[0] === tipo);
      return indice === -1 ? FUNCOES.length : indice;
    };
    const ordenados = [...usuarios].sort((a, b) =>
      posicaoDaFuncao(a.tipo_usuario) - posicaoDaFuncao(b.tipo_usuario)
      || a.nome_usuario.localeCompare(b.nome_usuario, 'pt-BR')
    );

    ordenados.forEach((usuario, posicao) => {
      const classe = classeDaFuncao(usuario.tipo_usuario);
      const cartao = criar('li', 'pessoa');
      cartao.style.animationDelay = `${Math.min(posicao, 8) * 0.04}s`;

      const avatar = criar('span', `avatar funcao-${classe}`, iniciais(usuario.nome_usuario));
      avatar.setAttribute('aria-hidden', 'true');

      const dados = criar('div', 'pessoa-dados');
      const setores = usuario.setores.length > 0
        ? `Responsável por: ${usuario.setores.join(', ')}`
        : 'Sem setor sob responsabilidade';
      dados.append(
        criar('strong', null, usuario.nome_usuario),
        criar('span', 'pessoa-email', usuario.email_usuario),
        criar('span', `selo-funcao funcao-${classe}`, usuario.tipo_usuario),
        criar('span', 'pessoa-setores', setores)
      );

      cartao.append(avatar, dados);
      pessoas.append(cartao);
    });
  }

  async function carregar(id) {
    esconderMensagem(mensagem);
    if (id === null) {
      conteudo.hidden = true;
      nomeEmpresa.textContent = '—';
      const erro = window.empresaAtiva.erro;
      mostrarMensagem(
        mensagem,
        erro || 'Nenhuma empresa cadastrada ainda. Cadastre uma na tela Empresa para ver a equipe.',
        Boolean(erro)
      );
      return;
    }
    try {
      const dados = await requisicao(`/painel/${id}`);
      nomeEmpresa.textContent = dados.empresa.nome_empresa;
      desenharFuncoes(dados.usuarios);
      desenharPessoas(dados.usuarios);
      conteudo.hidden = false;
    } catch (erro) {
      conteudo.hidden = true;
      mostrarMensagem(mensagem, erro.message, true);
    }
  }

  window.empresaAtiva.aoMudar(carregar);
})();