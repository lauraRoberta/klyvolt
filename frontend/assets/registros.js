/* KLYVOLT — Consumos, Leituras, Sensores e Setores ligados à API (window.KV, em api.js).
   Os modais e validações originais das páginas continuam responsáveis pelo layout;
   este arquivo só troca os "comandos SQL simulados" por chamadas reais.
   Setores não têm DELETE no backend. Decisões ainda não estão ligadas (falta o schema). */
(function () {
  'use strict';
  const page = document.body.dataset.module;
  const RES = { consumos: 'consumo', leituras: 'leitura', sensores: 'sensor', setores: 'setor' }[page];
  if (!RES) return;
  const ids = { consumos: 'consumoList', leituras: 'leituraList', sensores: 'sensorList', setores: 'sectorList' };
  const list = document.getElementById(ids[page]);
  if (!list) return;
  if (!window.KV) { console.error('api.js não foi carregado antes de registros.js'); return; }

  let items = [], machines = [], sensors = [], loaded = false, loadError = '';
  const emptyEl = list.querySelector('.kv-empty-state');
  const emptyDefault = emptyEl ? emptyEl.textContent : '';

  const fmt = number => Number(number).toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  const text = (tag, className, content) => {
    const el = document.createElement(tag);
    if (className) el.className = className;
    if (content != null) el.textContent = String(content);
    return el;
  };
  const icon = name => text('i', 'fa-solid ' + name);
  const row = (box, className, iconName, label) => {
    const p = text('p', className); if (iconName) { p.append(icon(iconName), ' '); } p.append(document.createTextNode(label)); box.append(p); return p;
  };
  const val = id => document.getElementById(id)?.value.trim() || '';
  const formatDate = date => {
    if (!date) return '—';
    const d = new Date(date); return Number.isNaN(d.getTime()) ? '—' : d.toLocaleString('pt-BR', { dateStyle: 'short', timeStyle: 'short' });
  };

  /* ---------- carga de dados ---------- */
  function enrich() {
    const mName = id => machines.find(m => String(m.id) === String(id))?.nome || '';
    const sName = id => sensors.find(s => String(s.id) === String(id))?.serie || '';
    for (const it of items) {
      if (page === 'consumos') { it.maquina = mName(it.idMaquina); it.grupo = (it.maquina.split(' ')[0] || '').toLowerCase(); }
      if (page === 'sensores') it.maquina = mName(it.idMaquina);
      if (page === 'leituras') { it.sensor = sName(it.idSensor); it.consumoRef = it.idConsumo ? 'Agregado' : null; }
    }
  }
  async function load() {
    loadError = '';
    try {
      const jobs = [KV.list(RES)];
      if (page === 'consumos' || page === 'sensores') jobs.push(KV.list('maquina'));
      if (page === 'leituras') jobs.push(KV.list('sensor'));
      const [data, extra] = await Promise.all(jobs);
      items = data;
      if (page === 'leituras') sensors = extra || []; else machines = extra || [];
    } catch (e) { loadError = KV.message(e); items = []; }
    loaded = true; enrich(); populateSelects(); render();
  }
  function populateSelects() {
    const fillSelect = (id, rows, label) => {
      const select = document.getElementById(id); if (!select) return;
      const selected = select.value;
      select.querySelectorAll('option:not([value=""])').forEach(el => el.remove());
      for (const r of rows) select.add(new Option(label(r), String(r.id)));
      select.value = selected || '';
    };
    if (page === 'consumos') fillSelect('idMaquina', machines, m => m.nome);
    if (page === 'leituras') fillSelect('idSensor', sensors, s => s.serie);
    if (page === 'sensores') fillSelect('kvSensorMachine', machines, m => m.nome);
  }

  /* ---------- cartões ---------- */
  const newCard = (item, key, state, label) => {
    const card = text('div', 'decision-card');
    card.dataset.kvLocalRecord = 'true';
    if (key) card.dataset[key] = state;
    if (key === 'statusConexao') card.dataset.conexao = state; // o style.css de Sensores usa data-conexao
    const head = text('div', 'card-header');
    head.append(text('span', 'id-badge', '#' + String(item.id).padStart(2, '0')));
    head.append(text('span', 'status-badge ' + (state === 'erro' || state === 'offline' ? 'status-falha' : state === 'pendente' ? 'status-pendente' : 'status-executada'), label));
    card.append(head);
    const body = text('div', 'card-body'); card.append(body);
    const actions = text('div', 'card-actions');
    const view = text('button', 'btn-action btn-view', 'Detalhes'); view.type = 'button'; actions.append(view);
    card.append(actions);
    return { card, body, view };
  };

  const originalOpen = window.openModal;
  function openExisting(mode, record) {
    if (typeof originalOpen !== 'function') return;
    if (page === 'setores') {
      // O openModal original monta HTML com o nome do setor; no modo "view" passamos vazio
      // e preenchemos o campo depois, para um nome com aspas nunca quebrar o botão.
      const safeName = mode === 'view' ? '' : record.nome;
      originalOpen(mode, record.id, safeName, record.divisao || 'corte', record.idResp || 0, '');
      document.getElementById('nomeSetor').value = record.nome;
      document.getElementById('idResponsavel').value = record.idResp ?? '';
    } else originalOpen(mode, record);
    if (page === 'consumos') {
      const machine = document.getElementById('idMaquina'); if (machine) machine.value = record.idMaquina ?? '';
    }
    if (page === 'leituras') {
      const sensor = document.getElementById('idSensor'); if (sensor) sensor.value = record.idSensor ?? '';
      const user = document.getElementById('idUsuario');
      if (user && record.idUsuario != null) { // mantém o responsável ao editar, mesmo sem lista de usuários
        if (![...user.options].some(o => o.value === String(record.idUsuario))) user.add(new Option('Usuário #' + record.idUsuario, String(record.idUsuario)));
        user.value = String(record.idUsuario);
      }
    }
    if (page === 'sensores') {
      const info = document.getElementById('maquinaInfoGroup'); if (info && !record.maquina) info.style.display = 'none';
      const linked = document.getElementById('kvSensorMachine'); if (linked) linked.value = record.idMaquina ?? '';
    }
    if (mode === 'view') setDetails(record);
  }
  const setDetails = record => {
    const wrap = document.getElementById('modalActions'); if (!wrap) return;
    wrap.replaceChildren();
    const buttons = [['Editar', () => openExisting('edit', record), 'btn-modal btn-confirm']];
    if (page !== 'setores') buttons.unshift(['Excluir', () => removeRecord(record.id), 'btn-modal btn-cancel']);
    for (const [title, action, cls] of buttons) {
      const b = text('button', cls, title); b.type = 'button'; b.addEventListener('click', action); wrap.append(b);
    }
  };

  const append = entry => list.insertBefore(entry, list.querySelector('.kv-empty-state'));
  function showEmpty() {
    const hasRecords = !!list.querySelector('.decision-card');
    if (emptyEl) {
      emptyEl.hidden = hasRecords;
      emptyEl.textContent = !loaded ? 'Carregando...' : loadError ? ('Não foi possível carregar os dados. ' + loadError) : emptyDefault;
    }
    const grid = document.querySelector('.kpi-grid');
    if (grid) grid.hidden = !hasRecords;
  }
  function render() {
    list.querySelectorAll('.decision-card[data-kv-local-record="true"]').forEach(e => e.remove());
    for (const item of items) {
      let parts;
      if (page === 'setores') {
        const labels = { corte: 'Corte', costura: 'Costura', acabamento: 'Acabamento', estamparia: 'Estamparia', bordado: 'Bordado' };
        parts = newCard(item, 'divisao', item.divisao, labels[item.divisao] || item.divisao);
        row(parts.body, 'rule-name', 'fa-industry', item.nome);
        row(parts.body, '', 'fa-id-card', 'ID Usuário Responsável: #' + item.idResp);
        parts.view.addEventListener('click', () => openExisting('view', item));
      } else if (page === 'sensores') {
        const labels = { online: 'Online', offline: 'Offline', erro: 'Erro', unknown: 'Desconhecido' };
        parts = newCard(item, 'statusConexao', item.statusConexao, labels[item.statusConexao] || item.statusConexao);
        row(parts.body, 'rule-name', 'fa-barcode', item.serie);
        row(parts.body, '', 'fa-microchip', item.tipo + ' (' + item.unidade + ')');
        if (item.fabricante) row(parts.body, '', 'fa-industry', item.fabricante + (item.modelo ? ' · ' + item.modelo : ''));
        row(parts.body, '', 'fa-shield-halved', 'Status: ' + item.status);
        if (item.ip) row(parts.body, 'ref-value', null, 'IP: ' + item.ip);
        if (item.maquina) row(parts.body, '', 'fa-gears', 'Máquina: ' + item.maquina);
        parts.view.addEventListener('click', () => openExisting('view', { ...item, consumoTotal: 0, consumoHoje: 0, pico: 0, hasMeasurements: false }));
      } else if (page === 'leituras') {
        const aggregated = !!item.idConsumo;
        parts = newCard(item, 'statusAgregacao', aggregated ? 'agregada' : 'pendente', aggregated ? 'Agregada' : 'Pendente');
        row(parts.body, 'rule-name', 'fa-bolt', fmt(item.valor) + ' kWh');
        row(parts.body, '', 'fa-barcode', 'Sensor: ' + (item.sensor || '#' + item.idSensor));
        row(parts.body, '', 'fa-calendar', formatDate(item.data));
        if (item.obs) row(parts.body, 'ref-value', null, item.obs);
        parts.view.addEventListener('click', () => openExisting('view', item));
      } else if (page === 'consumos') {
        parts = newCard(item, 'maquina', item.grupo || '', 'Registrado');
        row(parts.body, 'rule-name', 'fa-industry', item.maquina || 'Máquina #' + item.idMaquina);
        row(parts.body, '', 'fa-calendar-day', formatDate(item.inicio) + ' → ' + formatDate(item.fim));
        const hours = (new Date(item.fim) - new Date(item.inicio)) / 36e5;
        row(parts.body, '', 'fa-clock', 'Duração: ' + (Number.isFinite(hours) ? fmt(hours) : '—') + ' h');
        const summary = text('div', 'consumo-box');
        const header = text('div', 'consumo-header'); header.append(icon('fa-bolt'), ' Consumo Agregado');
        summary.append(header, text('div', 'consumo-value', fmt(item.kwh) + ' kWh'));
        parts.body.append(summary);
        parts.view.addEventListener('click', () => openExisting('view', item));
      }
      if (parts) append(parts.card);
    }
    updateKpis(items); showEmpty();
  }
  function updateKpis(rows) {
    const grid = document.querySelector('.kpi-grid'); if (!grid) return;
    grid.hidden = rows.length === 0;
    if (!rows.length) return;
    const set = (id, number, decimals = true) => { const e = document.getElementById(id); if (e) e.textContent = decimals ? fmt(number) : String(number); };
    if (page === 'consumos') {
      const now = new Date(); const period = rows.filter(r => { const d = new Date(r.inicio); return d.getMonth() === now.getMonth() && d.getFullYear() === now.getFullYear(); });
      const total = period.reduce((n, r) => n + Number(r.kwh || 0), 0);
      const days = new Set(period.map(r => new Date(r.inicio).toDateString())).size;
      const rates = period.map(r => Number(r.kwh) / ((new Date(r.fim) - new Date(r.inicio)) / 36e5)).filter(Number.isFinite);
      set('kpiTotal', total); set('kpiMedia', days ? total / days : 0); set('kpiPico', rates.length ? Math.max(...rates) : 0);
    } else if (page === 'leituras') {
      const now = new Date().toDateString();
      set('kpiTotal', rows.filter(r => new Date(r.data).toDateString() === now).length, false);
      set('kpiMedia', rows.reduce((n, r) => n + Number(r.valor || 0), 0) / rows.length);
      set('kpiAgreg', rows.filter(r => r.idConsumo).length, false);
    }
  }

  /* ---------- gravar / excluir pela API ---------- */
  const closeIfPossible = () => { if (typeof closeModal === 'function') closeModal(); };
  async function persist(front, id) {
    try {
      if (id == null) await KV.create(RES, front); else await KV.update(RES, id, front);
      closeIfPossible(); await load();
    } catch (e) { alert(KV.message(e)); }
  }
  async function removeRecord(id) {
    if (!confirm('Excluir o registro #' + id + '?')) return;
    try { await KV.remove(RES, id); closeIfPossible(); await load(); }
    catch (e) { alert(KV.message(e)); }
  }

  if (page === 'setores') {
    window.saveSector = function (id = null) {
      const nome = val('nomeSetor'), divisao = val('divisaoSetor'), idResp = val('idResponsavel');
      if (!nome || !idResp) { alert('Por favor, preencha todos os campos obrigatórios.'); return; }
      persist({ nome, divisao, idResp }, id);
    };
    window.deleteSector = function () { alert('Setores não podem ser excluídos: a exclusão apagaria máquinas, sensores e leituras em cascata.'); };
  }
  if (page === 'sensores') {
    window.saveSensor = function (id = null) {
      const serie = val('numeroSerie'), tipo = val('tipoSensor'), unidade = val('unidadeMedida'), protocolo = val('protocolo'), mac = val('macAddress'), ip = val('enderecoIp');
      const instalacao = val('dataInstalacao'), calibracao = val('dataCalibracao');
      if (!serie || !tipo || !unidade || !protocolo || !mac) { alert('Preencha todos os campos obrigatórios (*).'); return; }
      if (!/^([0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}$/.test(mac)) { alert('MAC inválido. Formato: XX:XX:XX:XX:XX:XX'); return; }
      if (ip && !/^((25[0-5]|2[0-4]\d|[01]?\d\d?)\.){3}(25[0-5]|2[0-4]\d|[01]?\d\d?)$/.test(ip) && !/^([0-9a-fA-F]{0,4}:){2,7}[0-9a-fA-F]{0,4}$/.test(ip)) { alert('IP inválido.'); return; }
      if (instalacao && calibracao && calibracao < instalacao) { alert('A calibração não pode ser anterior à instalação.'); return; }
      persist({
        serie, tipo, unidade, protocolo, mac, ip, instalacao, calibracao, token: val('token'),
        fabricante: val('fabricante'), modelo: val('modelo'), statusConexao: val('statusConexao'), status: val('statusSensor'),
        idMaquina: val('kvSensorMachine')
      }, id);
    };
    window.deleteSensor = id => removeRecord(id);
  }
  if (page === 'leituras') {
    window.saveLeitura = function (id = null) {
      const data = val('dataLeitura'), valor = Number(val('valorMedido')), idSensor = val('idSensor');
      if (!data || val('valorMedido') === '' || !Number.isFinite(valor) || !idSensor) { alert('Preencha todos os campos obrigatórios (*).'); return; }
      if (valor < 0) { alert('O valor medido não pode ser negativo.'); return; }
      if (!sensors.some(s => String(s.id) === idSensor)) { alert('Selecione um sensor cadastrado.'); return; }
      const existing = id != null ? items.find(r => String(r.id) === String(id)) : null;
      persist({ data, valor, idSensor, obs: val('observacao'), idUsuario: val('idUsuario'), idConsumo: existing ? existing.idConsumo : null }, id);
    };
    window.deleteLeitura = id => removeRecord(id);
  }
  if (page === 'consumos') {
    window.saveConsumo = function (id = null) {
      const inicio = val('dataInicio'), fim = val('dataFim'), kwh = Number(val('consumoKwh')), idMaquina = val('idMaquina');
      if (!inicio || !fim || val('consumoKwh') === '' || !Number.isFinite(kwh) || !idMaquina) { alert('Preencha todos os campos obrigatórios (*).'); return; }
      if (new Date(fim) <= new Date(inicio)) { alert('A data final deve ser posterior à data inicial.'); return; }
      if (kwh < 0) { alert('O consumo não pode ser negativo.'); return; }
      persist({ inicio, fim, kwh, idMaquina }, id);
    };
    window.deleteConsumo = id => removeRecord(id);
  }

  new MutationObserver(showEmpty).observe(list, { childList: true });
  showEmpty();
  load();
})();
