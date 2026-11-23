// js/nav.js - menu e perfil da pessoa logada (perfis-1).
// Telas públicas: Início, Como funciona, Nossa equipe, Entrar, Cadastrar empresa.
// Telas com login: as telas do sistema (o item Usuário só aparece para o administrador).
// Quem está logado tem uma bolinha de perfil no canto direito do cabeçalho, na mesma linha da logo, com os dados e o Sair.
// Os nomes abaixo precisam ser IGUAIS aos arquivos da pasta pages/.
(function () {
  const destino = document.querySelector('.cabecalho .container');
  if (!destino) return;

  const publica = document.body.hasAttribute('data-publica');
  const logado = typeof obterToken === 'function' && Boolean(obterToken());
  const sessao = logado ? sessaoAtual() : null;
  const ehAdministrador = Boolean(sessao && sessao.funcao === 'Administrador');

  // Nas telas públicas, o que é só para quem ainda não entrou some depois do login
  if (publica) {
    document.querySelectorAll('[data-so-deslogado]').forEach(el => { el.hidden = logado; });
    document.querySelectorAll('[data-so-logado]').forEach(el => { el.hidden = !logado; });
  }

  // [rótulo, arquivo, só administrador?]
  const ITENS_DO_SISTEMA = [
    ['Painel', 'painel.html'],
    ['Equipe', 'equipe.html'],
    ['Monitoramento', 'monitoramento.html'],
    ['Dados da empresa', 'empresa.html'],
    ['Usuário', 'usuario.html', true],
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
    itens = [['Início', 'index.html'], ['Como funciona', 'como-funciona.html'], ['Nossa equipe', 'nossa-equipe.html']];
    if (logado) itens.push(['Ir para o painel', 'painel.html']);
    else itens.push(['Entrar', 'login.html'], ['Cadastrar empresa', 'cadastro.html']);
  } else {
    itens = ITENS_DO_SISTEMA.filter(item => !item[2] || ehAdministrador);
  }

  // O logo leva ao início (público) ou ao painel (com login)
  const marca = destino.querySelector('.marca');
  if (marca) marca.setAttribute('href', publica ? 'index.html' : 'painel.html');

  // Com login: o nome da empresa ao lado do logo
  if (!publica) {
    const subtitulo = destino.querySelector('.subtitulo');
    if (sessao && sessao.empresa && subtitulo) {
      subtitulo.textContent = `Gestão de consumo elétrico · ${sessao.empresa.nome_empresa}`;
    }
  }

  // ---------- menu ----------
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
  destino.append(menu);

  // ---------- bolinha de perfil ----------
  if (!sessao) return;

  const estilo = document.createElement('style');
  estilo.id = 'estilo-perfil';
  estilo.textContent = `
    .perfil { position: relative; flex: none; margin-left: auto; }
    .perfil-botao { display: grid; place-items: center; width: 46px; height: 46px; padding: 0;
      border: 2px solid rgba(255, 255, 255, 0.55); border-radius: 50%; font: inherit; font-size: 16px;
      font-weight: 700; cursor: pointer;
      transition: transform 0.15s ease, box-shadow 0.15s ease; }
    .perfil-botao:hover { transform: translateY(-1px); box-shadow: 0 0 0 4px rgba(248, 200, 220, 0.35); }
    .perfil-botao:focus-visible { outline: 3px solid #ffe58a; outline-offset: 3px; }
    .perfil-administrador { background: #fde4ee; color: #8f2a55; }
    .perfil-operador { background: #e1f1fb; color: #1b5f8a; }
    .perfil-visualizador, .perfil-outra { background: #eef2f6; color: #4a5866; }
    .perfil-cartao { position: absolute; right: 0; top: calc(100% + 12px); z-index: 100; width: min(290px, calc(100vw - 32px));
      padding: 18px; background: #ffffff; color: #1b2733; border: 1px solid #dbe8f1; border-radius: 16px;
      box-shadow: 0 14px 40px rgba(16, 32, 46, 0.28); }
    .perfil-cartao[hidden] { display: none; }
    .perfil-topo { display: flex; align-items: center; gap: 12px; margin-bottom: 12px; }
    .perfil-topo .perfil-botao { cursor: default; border-color: #dbe8f1; }
    .perfil-topo .perfil-botao:hover { transform: none; box-shadow: none; }
    .perfil-nome { display: block; font-size: 17px; line-height: 1.25; }
    .perfil-funcao { font-size: 13px; color: #5d6873; }
    .perfil-dados { margin: 0 0 4px; }
    .perfil-dados div { padding: 8px 0; border-top: 1px solid #e8f0f6; }
    .perfil-dados dt { font-size: 12px; font-weight: 700; color: #5d6873; }
    .perfil-dados dd { margin: 2px 0 0; font-size: 15px; overflow-wrap: anywhere; }
    .perfil-sair { width: 100%; margin-top: 10px; }
  `;
  document.head.append(estilo);

  const classeDaFuncao = ({ Administrador: 'administrador', Operador: 'operador', Visualizador: 'visualizador' })[sessao.funcao] || 'outra';
  const partes = sessao.nome.trim().split(/\s+/);
  const iniciais = ((partes[0] ? partes[0][0] : '') + (partes.length > 1 ? partes[partes.length - 1][0] : '')).toUpperCase();

  function criar(tag, classe, texto) {
    const elemento = document.createElement(tag);
    if (classe) elemento.className = classe;
    if (texto !== undefined) elemento.textContent = texto;
    return elemento;
  }

  const caixa = criar('div', 'perfil');

  const botao = criar('button', `perfil-botao perfil-${classeDaFuncao}`, iniciais);
  botao.type = 'button';
  botao.setAttribute('aria-label', `Perfil de ${sessao.nome}`);
  botao.setAttribute('aria-haspopup', 'true');
  botao.setAttribute('aria-expanded', 'false');
  botao.setAttribute('aria-controls', 'perfil-cartao');

  const cartao = criar('div', 'perfil-cartao');
  cartao.id = 'perfil-cartao';
  cartao.hidden = true;
  cartao.setAttribute('role', 'dialog');
  cartao.setAttribute('aria-label', 'Dados do perfil');

  const topo = criar('div', 'perfil-topo');
  const avatar = criar('span', `perfil-botao perfil-${classeDaFuncao}`, iniciais);
  avatar.setAttribute('aria-hidden', 'true');
  const quem = document.createElement('div');
  quem.append(criar('strong', 'perfil-nome', sessao.nome), criar('span', 'perfil-funcao', sessao.funcao));
  topo.append(avatar, quem);

  const dados = criar('dl', 'perfil-dados');
  for (const [rotulo, valor] of [
    ['E-mail', sessao.email || '—'],
    ['Empresa', sessao.empresa ? sessao.empresa.nome_empresa : '—'],
    ['Função', sessao.funcao]
  ]) {
    const linha = document.createElement('div');
    linha.append(criar('dt', null, rotulo), criar('dd', null, valor));
    dados.append(linha);
  }

  const sair_ = criar('button', 'botao botao-secundario perfil-sair', 'Sair');
  sair_.type = 'button';
  sair_.addEventListener('click', () => sair());

  cartao.append(topo, dados, sair_);
  caixa.append(botao, cartao);
  // Canto direito do cabeçalho, na mesma linha da logo (o menu vai para a linha de baixo)
  destino.insertBefore(caixa, menu);

  function abrir(aberto) {
    cartao.hidden = !aberto;
    botao.setAttribute('aria-expanded', String(aberto));
  }
  botao.addEventListener('click', evento => {
    evento.stopPropagation();
    abrir(cartao.hidden);
  });
  document.addEventListener('click', evento => {
    if (!cartao.hidden && !caixa.contains(evento.target)) abrir(false);
  });
  document.addEventListener('keydown', evento => {
    if (evento.key === 'Escape' && !cartao.hidden) {
      abrir(false);
      botao.focus();
    }
  });
})();