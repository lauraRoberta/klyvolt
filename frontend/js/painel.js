// js/painel.js - painel da empresa escolhida na lista do cabeçalho.
// Carregar depois de api.js, nav.js e empresa-ativa.js.
(function () {
  const mensagem = document.querySelector('#mensagem');
  const conteudo = document.querySelector('#conteudo');
  const nomeEmpresa = document.querySelector('#nome-empresa');
  const kpis = document.querySelector('#kpis');
  const porMaquina = document.querySelector('#por-maquina');
  const porSetor = document.querySelector('#por-setor');
  const listaSensores = document.querySelector('#lista-sensores');
  const totalSensores = document.querySelector('#total-sensores');

  const decimal = valor => Number(valor).toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  const inteiro = valor => Number(valor).toLocaleString('pt-BR');

  function criar(tag, classe, texto) {
    const elemento = document.createElement(tag);
    if (classe) elemento.className = classe;
    if (texto !== undefined) elemento.textContent = texto;
    return elemento;
  }

  function desenharNumeros(totais) {
    const itens = [
      ['Usuários', inteiro(totais.usuarios), 'cadastrados na empresa'],
      ['Setores', inteiro(totais.setores), 'da empresa'],
      ['Máquinas', inteiro(totais.maquinas), 'em todos os setores'],
      ['Sensores online', `${inteiro(totais.sensores_online)} de ${inteiro(totais.sensores)}`, 'conectados agora'],
      ['Consumo total', `${decimal(totais.consumo_kwh)} kWh`, 'soma dos consumos registrados'],
      ['Decisões acionadas', inteiro(totais.decisoes), 'ligadas a leituras ou consumos']
    ];
    kpis.replaceChildren();
    itens.forEach(([rotulo, valor, detalhe], posicao) => {
      const cartao = criar('div', 'kpi');
      cartao.style.animationDelay = `${posicao * 0.05}s`;
      cartao.append(criar('span', 'kpi-rotulo', rotulo), criar('strong', 'kpi-valor', valor), criar('span', 'kpi-detalhe', detalhe));
      kpis.append(cartao);
    });
  }

  // itens: [{ nome, detalhe, consumo_kwh }] já em ordem decrescente
  function desenharBarras(lista, itens, textoVazio) {
    lista.replaceChildren();
    if (itens.length === 0) {
      lista.append(criar('li', 'vazio', textoVazio));
      return;
    }
    const maior = Math.max(...itens.map(item => item.consumo_kwh), 0);
    itens.forEach((item, posicao) => {
      const linha = criar('li', posicao === 0 && item.consumo_kwh > 0 ? 'primeiro' : '');
      const nome = item.detalhe ? `${item.nome} · ${item.detalhe}` : item.nome;
      const barra = criar('span', 'barra');
      barra.setAttribute('aria-hidden', 'true');
      const preenchimento = document.createElement('i');
      preenchimento.style.setProperty('--p', maior > 0 ? `${(item.consumo_kwh / maior) * 100}%` : '0%');
      barra.append(preenchimento);
      linha.append(criar('span', null, nome), criar('strong', null, `${decimal(item.consumo_kwh)} kWh`), barra);
      lista.append(linha);
    });
  }

  function desenharSensores(sensores) {
    listaSensores.replaceChildren();
    totalSensores.textContent = `${inteiro(sensores.length)} sensor(es)`;
    if (sensores.length === 0) {
      const linha = listaSensores.insertRow();
      const celula = linha.insertCell();
      celula.colSpan = 5;
      celula.className = 'vazio';
      celula.textContent = 'Nenhum sensor cadastrado nesta empresa.';
      return;
    }
    const ordenados = [...sensores].sort((a, b) => a.id_sensor - b.id_sensor);
    for (const sensor of ordenados) {
      const linha = listaSensores.insertRow();
      linha.insertCell().textContent = sensor.numero_serie;
      linha.insertCell().textContent = sensor.tipo_sensor;
      linha.insertCell().textContent = sensor.maquina;
      const tipoSelo = ['online', 'offline'].includes(sensor.status_conexao) ? sensor.status_conexao : 'outro';
      linha.insertCell().append(criar('span', `selo selo-${tipoSelo}`, sensor.status_conexao));
      linha.insertCell().textContent = sensor.status;
    }
  }

  async function carregar(id) {
    esconderMensagem(mensagem);
    if (id === null) {
      conteudo.hidden = true;
      nomeEmpresa.textContent = '—';
      const erro = window.empresaAtiva.erro;
      mostrarMensagem(
        mensagem,
        erro || 'Nenhuma empresa cadastrada ainda. Cadastre uma na tela Empresa para ver o painel.',
        Boolean(erro)
      );
      return;
    }
    try {
      const dados = await requisicao(`/painel/${id}`);
      nomeEmpresa.textContent = dados.empresa.nome_empresa;
      desenharNumeros(dados.totais);
      desenharBarras(
        porMaquina,
        dados.consumo_por_maquina.map(m => ({ nome: m.nome, detalhe: m.setor, consumo_kwh: m.consumo_kwh })),
        'Ainda não há máquinas cadastradas nesta empresa.'
      );
      desenharBarras(
        porSetor,
        dados.consumo_por_setor.map(s => ({ nome: s.nome, consumo_kwh: s.consumo_kwh })),
        'Ainda não há setores cadastrados nesta empresa.'
      );
      desenharSensores(dados.sensores);
      conteudo.hidden = false;
    } catch (erro) {
      conteudo.hidden = true;
      mostrarMensagem(mensagem, erro.message, true);
    }
  }

  window.empresaAtiva.aoMudar(carregar);
})();