// js/monitoramento.js - sensores, últimas leituras e decisões da empresa escolhida.
// Mostra o que está cadastrado no momento da consulta (botão "Atualizar" consulta de novo).
// Carregar depois de api.js, nav.js e empresa-ativa.js.
(function () {
  const mensagem = document.querySelector('#mensagem');
  const conteudo = document.querySelector('#conteudo');
  const nomeEmpresa = document.querySelector('#nome-empresa');
  const kpis = document.querySelector('#kpis');
  const listaSensores = document.querySelector('#lista-sensores');
  const totalSensores = document.querySelector('#total-sensores');
  const listaLeituras = document.querySelector('#lista-leituras');
  const listaDecisoes = document.querySelector('#lista-decisoes');
  const botaoAtualizar = document.querySelector('#botao-atualizar');
  const ultimaAtualizacao = document.querySelector('#ultima-atualizacao');

  let idAtual = null;

  const decimal = valor => Number(valor).toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  const inteiro = valor => Number(valor).toLocaleString('pt-BR');

  function criar(tag, classe, texto) {
    const elemento = document.createElement(tag);
    if (classe) elemento.className = classe;
    if (texto !== undefined) elemento.textContent = texto;
    return elemento;
  }

  function selo(texto, tipo) {
    return criar('span', `selo selo-${tipo}`, texto);
  }

  function linhaVazia(corpo, colunas, texto) {
    const linha = corpo.insertRow();
    const celula = linha.insertCell();
    celula.colSpan = colunas;
    celula.className = 'vazio';
    celula.textContent = texto;
  }

  function desenharNumeros(totais) {
    const itens = [
      ['Sensores online', `${inteiro(totais.sensores_online)} de ${inteiro(totais.sensores)}`, 'conforme o status cadastrado'],
      ['Leituras registradas', inteiro(totais.leituras), 'de todos os sensores'],
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

  function desenharSensores(sensores) {
    listaSensores.replaceChildren();
    totalSensores.textContent = `${inteiro(sensores.length)} sensor(es)`;
    if (sensores.length === 0) {
      linhaVazia(listaSensores, 6, 'Nenhum sensor cadastrado nesta empresa.');
      return;
    }
    for (const sensor of [...sensores].sort((a, b) => a.id_sensor - b.id_sensor)) {
      const linha = listaSensores.insertRow();
      linha.insertCell().textContent = sensor.numero_serie;
      linha.insertCell().textContent = sensor.maquina;
      const tipo = ['online', 'offline'].includes(sensor.status_conexao) ? sensor.status_conexao : 'outro';
      linha.insertCell().append(selo(sensor.status_conexao, tipo));
      linha.insertCell().textContent = sensor.status;
      linha.insertCell().textContent = sensor.ultima_leitura ? formatarDataHora(sensor.ultima_leitura) : 'Sem leituras';
      linha.insertCell().textContent = sensor.ultimo_valor_kwh !== null ? `${decimal(sensor.ultimo_valor_kwh)} kWh` : '—';
    }
  }

  function desenharLeituras(leituras) {
    listaLeituras.replaceChildren();
    if (leituras.length === 0) {
      linhaVazia(listaLeituras, 4, 'Ainda não há leituras registradas.');
      return;
    }
    for (const leitura of leituras) {
      const linha = listaLeituras.insertRow();
      linha.insertCell().textContent = formatarDataHora(leitura.data_leitura);
      linha.insertCell().textContent = leitura.maquina;
      linha.insertCell().textContent = leitura.sensor;
      linha.insertCell().textContent = `${decimal(leitura.valor_medido_kwh)} kWh`;
    }
  }

  function desenharDecisoes(decisoes) {
    listaDecisoes.replaceChildren();
    if (decisoes.length === 0) {
      linhaVazia(listaDecisoes, 5, 'Nenhuma decisão registrada para esta empresa.');
      return;
    }
    for (const decisao of decisoes) {
      const linha = listaDecisoes.insertRow();
      linha.insertCell().textContent = formatarDataHora(decisao.data_tomada_decisao);
      linha.insertCell().textContent = decisao.decisao;
      linha.insertCell().textContent = decimal(decisao.valor_referencia);
      const tipo = decisao.status_execucao === 'Executada' ? 'online'
        : decisao.status_execucao === 'Pendente' ? 'pendente' : 'outro';
      linha.insertCell().append(selo(decisao.status_execucao, tipo));
      linha.insertCell().textContent = decisao.observacao || '—';
    }
  }

  async function carregar(id) {
    idAtual = id;
    esconderMensagem(mensagem);
    if (id === null) {
      conteudo.hidden = true;
      nomeEmpresa.textContent = '—';
      const erro = window.empresaAtiva.erro;
      mostrarMensagem(
        mensagem,
        erro || 'Nenhuma empresa cadastrada ainda. Cadastre uma na tela Empresa para ver o monitoramento.',
        Boolean(erro)
      );
      return;
    }
    try {
      const dados = await requisicao(`/painel/${id}`);
      nomeEmpresa.textContent = dados.empresa.nome_empresa;
      desenharNumeros(dados.totais);
      desenharSensores(dados.sensores);
      desenharLeituras(dados.ultimas_leituras);
      desenharDecisoes(dados.ultimas_decisoes);
      ultimaAtualizacao.textContent = `Atualizado às ${new Date().toLocaleTimeString('pt-BR')}`;
      conteudo.hidden = false;
    } catch (erro) {
      conteudo.hidden = true;
      mostrarMensagem(mensagem, erro.message, true);
    }
  }

  botaoAtualizar.addEventListener('click', async () => {
    if (idAtual === null) return;
    botaoAtualizar.disabled = true;
    await carregar(idAtual);
    botaoAtualizar.disabled = false;
  });

  window.empresaAtiva.aoMudar(carregar);
})();