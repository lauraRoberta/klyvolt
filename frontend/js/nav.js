// js/nav.js - menu do cabeçalho (login-1).
// Telas públicas: Início, Como funciona, Entrar, Cadastrar empresa.
// Telas com login: todas as telas do sistema + Sair, e quem está logado no cabeçalho.
// Os nomes abaixo precisam ser IGUAIS aos arquivos da pasta pages/.
(function () {
  const destino = document.querySelector('.cabecalho .container');
  if (!destino) return;

  const publica = document.body.hasAttribute('data-publica');
  const logado = typeof obterToken === 'function' && Boolean(obterToken());

  const ITENS_DO_SISTEMA = [
    ['Painel', 'painel.html'],
    ['Equipe', 'equipe.html'],
    ['Monitoramento', 'monitoramento.html'],
    ['Empresa', 'empresa.html'],
    ['Usuário', 'usuario.html'],
    ['Setor', 'setor.html'],
    ['Máquina', 'maquina.html'],
    ['Sensor', 'sensor.html'],
    ['Consumo', 'consumo.html'],
    ['Leitura', 'leitura.html'],
    ['Decisão', 'desicao.html'],
    ['Tomada de decisão', 'tomada_desicao.html']
  ];

  let itens;
  if (publica) {
    itens = [['Início', 'index.html'], ['Como funciona', 'como-funciona.html']];
    if (logado) itens.push(['Ir para o painel', 'painel.html']);
    else itens.push(['Entrar', 'login.html'], ['Cadastrar empresa', 'cadastro.html']);
  } else {
    itens = ITENS_DO_SISTEMA;
  }

  // O logo leva ao início (público) ou ao painel (com login)
  const marca = destino.querySelector('.marca');
  if (marca) marca.setAttribute('href', publica ? 'index.html' : 'painel.html');

  // Com login: "Empresa · Nome (Função)" no lugar do subtítulo
  if (!publica) {
    const sessao = sessaoAtual();
    const subtitulo = destino.querySelector('.subtitulo');
    if (sessao && sessao.empresa && subtitulo) {
      subtitulo.textContent = `${sessao.empresa.nome_empresa} · ${sessao.nome} (${sessao.funcao})`;
    }
  }

  const menu = document.createElement('nav');
  menu.className = 'menu';
  menu.setAttribute('aria-label', 'Telas do sistema');
  for (const [rotulo, arquivo] of itens) {
    const link = document.createElement('a');
    link.href = arquivo;
    link.textContent = rotulo;
    if (window.location.pathname.endsWith('/' + arquivo)) link.setAttribute('aria-current', 'page');
    menu.append(link);
  }

  if (!publica || logado) {
    const botaoSair = document.createElement('a');
    botaoSair.href = 'login.html';
    botaoSair.textContent = 'Sair';
    botaoSair.addEventListener('click', evento => { evento.preventDefault(); sair(); });
    menu.append(botaoSair);
  }

  destino.append(menu);
})();
