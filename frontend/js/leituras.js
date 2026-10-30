/* KLYVOLT · leituras.js — registro e consulta de leituras pela API (/leituras)
   Cada leitura é a energia (kWh) medida em um intervalo. O banco agrega as leituras
   aos consumos e avalia as regras de decisão a cada gravação. */
(function () {
  'use strict';
  const { requisicao, fmt, toast, confirmar, ocupado } = KV;
  const $ = id => document.getElementById(id);
  const lista = KV.lista($('leituraList'), { vazio: 'Nenhuma leitura registrada.', filtro: (c, f) => c.dataset.statusAgregacao === f });
  let leituras = [], sensores = [], usuarios = [], consumos = new Map(), total = 0;

  window.filterList = function (f) { KV.marcarAba(window.event && window.event.target); lista.filtroAtual = f; lista.aplicar(); };
  window.searchLeitura = function () { lista.busca = $('searchInput').value; lista.aplicar(); };

  const sensor = id => sensores.find(s => s.id_sensor === id);
  const serie = id => (sensor(id) || {}).numero_serie || 'Sensor ' + fmt.id(id);

  async function carregar() {
    lista.carregando();
    try {
      const [r, s, u, c] = await Promise.all([
        requisicao('/leituras?limite=500', 'GET', null, { resposta: true }),
        requisicao('/sensores'), requisicao('/usuarios'), requisicao('/consumos')
      ]);
      leituras = r.dados; total = Number(r.resposta.headers.get('X-Total-Count')) || leituras.length;
      sensores = s; usuarios = u;
      consumos = new Map(c.map(x => [x.id_consumo, x]));
      KV.preencherSelect($('idSensor'), sensores, { valor: x => x.id_sensor, rotulo: x => `${x.numero_serie} · ${x.nome_maquina || ''}`, vazio: 'Selecione um sensor cadastrado' });
      KV.preencherSelect($('idUsuario'), usuarios, { valor: x => x.id_usuario, rotulo: x => x.nome_usuario, vazio: '— Coleta automática —' });
      lista.render(leituras, l => {
        const agregada = !!l.id_consumo;
        const c = KV.card({ id: l.id_leitura, badge: agregada ? 'Agregada' : 'Pendente', badgeClasse: agregada ? 'status-executada' : 'status-pendente',
          dataset: { statusAgregacao: agregada ? 'agregada' : 'pendente' } });
        c.linha(fmt.num(l.valor_medido_kwh) + ' kWh', 'fa-bolt', 'rule-name');
        c.linha('Sensor: ' + (l.numero_serie_sensor || serie(l.id_sensor)), 'fa-barcode');
        c.linha(fmt.data(l.data_leitura), 'fa-calendar');
        if (l.observacao_leitura) c.linha(l.observacao_leitura, null, 'ref-value');
        c.ver.addEventListener('click', () => openModal('view', l));
        return c.card;
      }, total > leituras.length ? `Exibindo as ${leituras.length} leituras mais recentes de ${total}.` : null);
      kpis();
    } catch (erro) { lista.erro(erro.message); toast(erro.message, 'erro'); }
  }

  function kpis() {
    const grid = document.querySelector('.kpi-grid');
    grid.hidden = leituras.length === 0;
    if (!leituras.length) return;
    const agora = new Date(), hoje = agora.toDateString(), limite24h = agora.getTime() - 24 * 3600e3;
    const doDia = leituras.filter(r => { const d = KV.parseLocal(r.data_leitura); return d && d.toDateString() === hoje; });
    const ult24 = leituras.filter(r => { const d = KV.parseLocal(r.data_leitura); return d && d.getTime() >= limite24h && d <= agora; });
    $('kpiTotal').textContent = String(doDia.length);
    // Média/h: energia medida nas últimas 24 h ÷ 24 h
    $('kpiMedia').textContent = fmt.num(ult24.reduce((n, r) => n + Number(r.valor_medido_kwh), 0) / 24);
    $('kpiAgreg').textContent = String(leituras.filter(r => r.id_consumo).length);
  }

  function refConsumo(id) {
    const c = consumos.get(id);
    return c ? `${c.nome_maquina || 'Máquina'} · ${fmt.data(c.data_inicio)} → ${fmt.data(c.data_fim)}` : 'Consumo ' + fmt.id(id);
  }

  function openModal(mode, l = null) {
    const inputs = document.querySelectorAll('.modal-body input, .modal-body select');
    const info = $('consumoInfoGroup');
    info.style.display = 'none';
    if (mode === 'create') {
      if (!KV.podeOperar()) return toast('Seu perfil (Visualizador) permite apenas consultas.', 'aviso');
      if (!sensores.length) return toast('Cadastre um sensor antes de registrar leituras.', 'aviso');
      $('modalTitle').innerText = 'Nova Leitura';
      inputs.forEach(i => { i.value = ''; i.disabled = false; });
      $('dataLeitura').value = fmt.inputDT(KV.toLocalISO(new Date()));
      $('idSensor').value = sensores.length === 1 ? String(sensores[0].id_sensor) : '';
      $('idUsuario').value = String((KV.perfil() || {}).id_usuario || '');
      $('sumValor').innerText = '-- kWh'; $('sumSensor').innerText = $('idSensor').value ? serie(Number($('idSensor').value)) : '--'; $('sumAgreg').innerText = '--';
      KV.botoesModal($('modalActions'), [['Cancelar', 'btn-cancel', closeModal], ['Registrar Leitura', 'btn-confirm', b => saveLeitura(null, b)]]);
    } else {
      $('dataLeitura').value = fmt.inputDT(l.data_leitura);
      $('valorMedido').value = l.valor_medido_kwh;
      $('observacao').value = l.observacao_leitura || '';
      $('idSensor').value = String(l.id_sensor);
      $('idUsuario').value = l.id_usuario ? String(l.id_usuario) : '';
      $('sumValor').innerText = fmt.num(l.valor_medido_kwh) + ' kWh';
      $('sumSensor').innerText = l.numero_serie_sensor || serie(l.id_sensor);
      $('sumAgreg').innerText = l.id_consumo ? 'Agregada' : 'Pendente';
      if (l.id_consumo) { info.style.display = 'block'; $('consumoRef').innerText = refConsumo(l.id_consumo) + ' (' + fmt.id(l.id_consumo) + ')'; }
      if (mode === 'view') {
        $('modalTitle').innerText = 'Leitura ' + fmt.id(l.id_leitura);
        inputs.forEach(i => i.disabled = true);
        KV.botoesModal($('modalActions'), [['Excluir', 'btn-cancel', () => deleteLeitura(l)], ['Editar', 'btn-confirm', () => openModal('edit', l)]]);
      } else {
        $('modalTitle').innerText = 'Editando Leitura ' + fmt.id(l.id_leitura);
        inputs.forEach(i => i.disabled = false);
        KV.botoesModal($('modalActions'), [['Cancelar', 'btn-cancel', closeModal], ['Atualizar', 'btn-confirm', b => saveLeitura(l.id_leitura, b)]]);
      }
    }
    $('modalOverlay').style.display = 'flex';
  }
  function closeModal() { $('modalOverlay').style.display = 'none'; }
  window.openModal = openModal; window.closeModal = closeModal;
  KV.prepararModal($('modalOverlay'), closeModal);
  $('valorMedido').addEventListener('input', () => {
    const v = KV.numero($('valorMedido').value);
    $('sumValor').innerText = Number.isFinite(v) ? fmt.num(v) + ' kWh' : '-- kWh';
  });
  $('idSensor').addEventListener('change', () => { $('sumSensor').innerText = serie(Number($('idSensor').value)); });

  async function saveLeitura(id, botao) {
    const data = $('dataLeitura').value, valorTxt = $('valorMedido').value.trim(), valor = KV.numero(valorTxt);
    const dados = { data_leitura: data, valor_medido_kwh: valor, observacao_leitura: $('observacao').value.trim() || null,
      id_sensor: Number($('idSensor').value), id_usuario: $('idUsuario').value ? Number($('idUsuario').value) : null };
    if (!data || valorTxt === '' || !Number.isFinite(valor) || !dados.id_sensor) return toast('Preencha todos os campos obrigatórios (*).', 'aviso');
    if (valor < 0) return toast('O valor medido não pode ser negativo.', 'aviso');
    ocupado(botao, true, 'Salvando…');
    try {
      const salvo = await requisicao(id ? `/leituras/${id}` : '/leituras', id ? 'PUT' : 'POST', dados);
      closeModal();
      toast((id ? 'Leitura atualizada' : 'Leitura registrada') + (salvo.id_consumo ? ' e agregada ao consumo ' + fmt.id(salvo.id_consumo) + '.' : '.'));
      if (!id && salvo.decisoes_acionadas && salvo.decisoes_acionadas.length)
        toast('Regra de decisão acionada: ' + salvo.decisoes_acionadas.join(', ') + '.', 'aviso', 7000);
      await carregar();
    } catch (erro) { toast(erro.message, 'erro'); } finally { ocupado(botao, false); }
  }

  async function deleteLeitura(l) {
    const ok = await confirmar({ titulo: 'Excluir leitura ' + fmt.id(l.id_leitura),
      mensagem: `Excluir a leitura de ${fmt.num(l.valor_medido_kwh)} kWh (${fmt.data(l.data_leitura)})?`,
      detalhe: 'Acionamentos de decisão gerados por ela permanecem no histórico, sem o vínculo com a leitura.' });
    if (!ok) return;
    try { await requisicao(`/leituras/${l.id_leitura}`, 'DELETE'); closeModal(); toast('Leitura excluída.'); await carregar(); }
    catch (erro) { toast(erro.message, 'erro'); }
  }

  KV.pronto.then(carregar).catch(() => {});
})();
