/* KLYVOLT · sensores.js — CRUD de sensores pela API (GET/POST/PUT/DELETE /sensores)
   O token do sensor é enviado na gravação e nunca volta da API. */
(function () {
  'use strict';
  const { requisicao, fmt, toast, confirmar, ocupado } = KV;
  const $ = id => document.getElementById(id);
  const CONEXAO = { online: 'Online', offline: 'Offline', erro: 'Erro', unknown: 'Desconhecido' };
  const OPERACAO = { ativo: 'Ativo', inativo: 'Inativo', manutencao: 'Manutenção' };
  const lista = KV.lista($('sensorList'), { vazio: 'Nenhum sensor cadastrado.', filtro: (c, f) => c.dataset.statusConexao === f });
  let sensores = [], maquinas = [];

  window.formatMAC = function (input) {
    const v = input.value.replace(/[^0-9A-Fa-f]/g, '').toUpperCase();
    let out = '';
    for (let i = 0; i < v.length && i < 12; i++) { if (i > 0 && i % 2 === 0) out += ':'; out += v[i]; }
    input.value = out;
  };
  window.filterList = function (f) { KV.marcarAba(window.event && window.event.target); lista.filtroAtual = f; lista.aplicar(); };
  window.searchSensor = function () { lista.busca = $('searchInput').value; lista.aplicar(); };

  async function carregar() {
    lista.carregando();
    try {
      [sensores, maquinas] = await Promise.all([requisicao('/sensores'), requisicao('/maquinas')]);
      KV.preencherSelect($('idMaquina'), maquinas, { valor: x => x.id_maquina, rotulo: x => x.nome_maquina, vazio: 'Selecione uma máquina cadastrada' });
      lista.render(sensores, s => {
        const cls = s.status_conexao === 'erro' || s.status_conexao === 'offline' ? 'status-falha' : s.status_conexao === 'unknown' ? 'status-pendente' : 'status-executada';
        const c = KV.card({ id: s.id_sensor, badge: CONEXAO[s.status_conexao] || s.status_conexao, badgeClasse: cls, dataset: { statusConexao: s.status_conexao } });
        c.linha(s.numero_serie, 'fa-barcode', 'rule-name');
        c.linha(`${s.tipo_sensor} (${s.unidade_medida})`, 'fa-microchip');
        c.linha('Máquina: ' + (s.nome_maquina || fmt.id(s.id_maquina)), 'fa-industry');
        if (s.fabricante) c.linha(s.fabricante + (s.modelo ? ' · ' + s.modelo : ''), 'fa-industry');
        c.linha('Status: ' + (OPERACAO[s.status] || s.status), 'fa-shield-halved');
        if (s.qtd_leituras) c.linha(`${s.qtd_leituras} leituras · total ${fmt.num(s.total_kwh)} kWh`, 'fa-wave-square');
        if (s.endereco_ip) c.linha('IP: ' + s.endereco_ip, null, 'ref-value');
        const serie = s.ultimas_leituras || [];
        const g = KV.grafico(serie.map(x => Number(x.valor_medido_kwh)), serie.map(x => fmt.data(x.data_leitura)));
        if (g) c.corpo.append(g);
        c.ver.addEventListener('click', () => openModal('view', s));
        return c.card;
      });
    } catch (erro) { lista.erro(erro.message); toast(erro.message, 'erro'); }
  }

  function preencher(s) {
    $('numeroSerie').value = s.numero_serie;
    $('fabricante').value = s.fabricante || '';
    $('modelo').value = s.modelo || '';
    $('tipoSensor').value = s.tipo_sensor;
    if ($('tipoSensor').value !== s.tipo_sensor) $('tipoSensor').add(new Option(s.tipo_sensor, s.tipo_sensor, true, true));
    $('unidadeMedida').value = s.unidade_medida;
    $('protocolo').value = s.protocolo_comunicacao;
    if ($('protocolo').value !== s.protocolo_comunicacao) $('protocolo').add(new Option(s.protocolo_comunicacao, s.protocolo_comunicacao, true, true));
    $('macAddress').value = s.mac_address;
    $('enderecoIp').value = s.endereco_ip || '';
    $('token').value = '';
    $('statusConexao').value = s.status_conexao;
    $('statusSensor').value = s.status;
    $('dataInstalacao').value = fmt.inputDate(s.data_instalacao);
    $('dataCalibracao').value = fmt.inputDate(s.data_ultima_calibracao);
    $('idMaquina').value = String(s.id_maquina);
    $('maquinaNome').innerText = s.nome_maquina || fmt.id(s.id_maquina);
  }

  function openModal(mode, s = null) {
    const inputs = document.querySelectorAll('.modal-body input, .modal-body select');
    const summary = $('consumoSummary');
    summary.style.display = 'none';
    if (mode === 'create') {
      if (!KV.isAdmin()) return toast('Somente administradores cadastram sensores.', 'aviso');
      if (!maquinas.length) return toast('Cadastre uma máquina antes de adicionar sensores.', 'aviso');
      $('modalTitle').innerText = 'Novo Sensor';
      inputs.forEach(i => { i.value = ''; i.disabled = false; });
      $('tipoSensor').value = 'Consumo Elétrico';
      $('unidadeMedida').value = 'kWh';
      $('protocolo').value = 'MQTT';
      $('statusConexao').value = 'online';
      $('statusSensor').value = 'ativo';
      $('idMaquina').value = maquinas.length === 1 ? String(maquinas[0].id_maquina) : '';
      $('token').placeholder = 'tk_xxxxxxxx';
      $('maquinaInfoGroup').style.display = 'none';
      $('maquinaSelectGroup').style.display = 'block';
      KV.botoesModal($('modalActions'), [['Cancelar', 'btn-cancel', closeModal], ['Salvar Sensor', 'btn-confirm', b => saveSensor(null, b)]]);
    } else {
      preencher(s);
      if (mode === 'view') {
        $('modalTitle').innerText = 'Sensor ' + fmt.id(s.id_sensor);
        $('maquinaInfoGroup').style.display = 'block';
        $('maquinaSelectGroup').style.display = 'none';
        $('token').placeholder = '•••••••• (oculto)';
        summary.style.display = 'flex';
        $('sumTotal').innerText = fmt.num(s.total_kwh) + ' kWh';
        $('sumHoje').innerText = fmt.num(s.hoje_kwh) + ' kWh';
        $('sumPico').innerText = fmt.num(s.pico_kwh) + ' kWh';
        inputs.forEach(i => i.disabled = true);
        KV.botoesModal($('modalActions'), [['Excluir', 'btn-cancel', () => deleteSensor(s)], ['Editar', 'btn-confirm', () => openModal('edit', s)]]);
      } else {
        $('modalTitle').innerText = 'Editando Sensor ' + fmt.id(s.id_sensor);
        $('maquinaInfoGroup').style.display = 'none';
        $('maquinaSelectGroup').style.display = 'block';
        $('token').placeholder = 'Deixe em branco para manter o token atual';
        inputs.forEach(i => i.disabled = false);
        KV.botoesModal($('modalActions'), [['Cancelar', 'btn-cancel', closeModal], ['Atualizar', 'btn-confirm', b => saveSensor(s.id_sensor, b)]]);
      }
    }
    $('modalOverlay').style.display = 'flex';
  }
  function closeModal() { $('modalOverlay').style.display = 'none'; }
  window.openModal = openModal; window.closeModal = closeModal;
  KV.prepararModal($('modalOverlay'), closeModal);

  async function saveSensor(id, botao) {
    const v = k => $(k).value.trim();
    const dados = {
      numero_serie: v('numeroSerie'), fabricante: v('fabricante') || null, modelo: v('modelo') || null,
      tipo_sensor: v('tipoSensor'), unidade_medida: v('unidadeMedida'), protocolo_comunicacao: v('protocolo'),
      mac_address: v('macAddress').toUpperCase(), endereco_ip: v('enderecoIp') || null, token_autenticacao: v('token') || null,
      status_conexao: v('statusConexao'), status: v('statusSensor'),
      data_instalacao: v('dataInstalacao') || null, data_ultima_calibracao: v('dataCalibracao') || null, id_maquina: Number(v('idMaquina'))
    };
    if (!dados.numero_serie || !dados.tipo_sensor || !dados.unidade_medida || !dados.protocolo_comunicacao || !dados.mac_address || !dados.id_maquina)
      return toast('Preencha todos os campos obrigatórios (*).', 'aviso');
    if (!/^([0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}$/.test(dados.mac_address)) return toast('MAC inválido. Formato: XX:XX:XX:XX:XX:XX', 'aviso');
    if (dados.endereco_ip) {
      const ipv4 = /^((25[0-5]|2[0-4]\d|[01]?\d\d?)\.){3}(25[0-5]|2[0-4]\d|[01]?\d\d?)$/;
      const ipv6 = /^([0-9a-fA-F]{0,4}:){2,7}[0-9a-fA-F]{0,4}$/;
      if (!ipv4.test(dados.endereco_ip) && !ipv6.test(dados.endereco_ip)) return toast('IP inválido.', 'aviso');
    }
    if (dados.data_instalacao && dados.data_ultima_calibracao && dados.data_ultima_calibracao < dados.data_instalacao)
      return toast('A calibração não pode ser anterior à instalação.', 'aviso');
    if (dados.token_autenticacao && dados.token_autenticacao.length < 8) return toast('O token deve ter ao menos 8 caracteres.', 'aviso');
    ocupado(botao, true, 'Salvando…');
    try {
      await requisicao(id ? `/sensores/${id}` : '/sensores', id ? 'PUT' : 'POST', dados);
      closeModal(); toast(id ? 'Sensor atualizado.' : 'Sensor cadastrado.'); await carregar();
    } catch (erro) { toast(erro.message, 'erro'); } finally { ocupado(botao, false); }
  }

  async function deleteSensor(s) {
    const ok = await confirmar({ titulo: 'Excluir sensor ' + fmt.id(s.id_sensor), mensagem: `Excluir o sensor ${s.numero_serie}?`,
      detalhe: s.qtd_leituras ? `As ${s.qtd_leituras} leituras registradas por este sensor também serão excluídas.` : 'Esta ação não pode ser desfeita.' });
    if (!ok) return;
    try { await requisicao(`/sensores/${s.id_sensor}`, 'DELETE'); closeModal(); toast('Sensor excluído.'); await carregar(); }
    catch (erro) { toast(erro.message, 'erro'); }
  }

  KV.pronto.then(carregar).catch(() => {});
})();
