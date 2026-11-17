// js/nav.js - menu entre as telas do sistema, inserido no cabeçalho.
// Para usar em qualquer página, basta carregar este arquivo.
// Os nomes abaixo precisam ser IGUAIS aos arquivos da pasta pages/.
(function () {
  const ITENS = [
    ['Início', 'index.html'],
    ['Painel', 'painel.html'],
    ['Equipe', 'equipe.html'],
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

  const destino = document.querySelector('.cabecalho .container');
  if (!destino) return;

  // O logo leva para o início
  const marca = destino.querySelector('.marca');
  if (marca) marca.setAttribute('href', 'index.html');

  const menu = document.createElement('nav');
  menu.className = 'menu';
  menu.setAttribute('aria-label', 'Telas do sistema');
  for (const [rotulo, arquivo] of ITENS) {
    const link = document.createElement('a');
    link.href = arquivo;
    link.textContent = rotulo;
    if (window.location.pathname.endsWith('/' + arquivo)) link.setAttribute('aria-current', 'page');
    menu.append(link);
  }
  destino.append(menu);
})();