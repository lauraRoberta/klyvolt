/* KLYVOLT · painel.js — painel de indicadores e relatórios (GET /relatorios/resumo)
   Todos os números vêm do banco. Sem registros, o painel mostra estados vazios. */
(function () {
  'use strict';
  const { requisicao, fmt, toast, ocupado, el } = KV;
  const $ = id => document.getElementById(id);
  const STATUS = { pendente: ['Pendente', 'status-pendente'], executada: ['Executada', 'status-executada'],
    cancelada: ['Cancelada', 'status-falha'], falha: ['Falha', 'status-falha'] };
  let relatorio = null;

  const iso = d => KV.toLocalISO(d).slice(0, 10);
  function periodoPadrao(tipo) {
    const hoje = new Date(); hoje.setHours(0, 0, 0, 0);
    if (tipo === 'anterior') {
      const ini = new Date(hoje.getFullYear(), hoje.getMonth() - 1, 1), fim = new Date(hoje.getFullYear(), hoje.getMonth(), 0);
      return [iso(ini), iso(fim)];
    }
    if (tipo === '30') { const ini = new Date(hoje); ini.setDate(ini.getDate() - 29); return [iso(ini), iso(hoje)]; }
    if (tipo === 'ano') return [iso(new Date(hoje.getFullYear(), 0, 1)), iso(hoje)];
    return [iso(new Date(hoje.getFullYear(), hoje.getMonth(), 1)), iso(hoje)];
  }

  window.selecionarPeriodo = function (tipo) {
    KV.marcarAba(window.event && window.event.target);
    const [ini, fim] = periodoPadrao(tipo);
    $('dataInicioRel').value = ini; $('dataFimRel').value = fim;
    carregar();
  };

  function cardItem(item, total, icone) {
    const c = KV.card({ id: item.id, badge: item.registros === 1 ? '1 registro' : `${item.registros} registros` });
    c.card.querySelector('.card-actions').remove();
    c.linha(item.nome, icone, 'rule-name');
    if (item.grupo) c.linha('Setor: ' + item.grupo, 'fa-layer-group');
    c.linha(`${total > 0 ? fmt.num(item.consumo_kwh / total * 100) : '0,00'}% do consumo do período`, 'fa-chart-pie');
    const box = el('div', 'consumo-box');
    const h = el('div', 'consumo-header'); h.append(KV.icon('fa-bolt'), ' Consumo');
    box.append(h, el('div', 'consumo-value', fmt.num(item.consumo_kwh) + ' kWh'));
    c.corpo.append(box);
    if (item.custo_estimado != null) c.linha('Custo estimado: ' + fmt.brl(item.custo_estimado), 'fa-coins', 'kv-cost');
    return c.card;
  }

  function preencherLista(id, itens, construir, vazio) {
    const container = $(id);
    container.querySelectorAll('.decision-card').forEach(c => c.remove());
    const empty = container.querySelector('.kv-empty-state');
    empty.hidden = itens.length > 0;
    empty.textContent = vazio;
    for (const item of itens) container.insertBefore(construir(item), empty);
  }

  function desenhar(r) {
    $('periodoTexto').textContent = `Período: ${fmt.dia(r.inicio)} a ${fmt.dia(r.fim)} (${r.dias} dia${r.dias > 1 ? 's' : ''})`;
    document.querySelectorAll('#kpiPrincipal, #kpiSecundario').forEach(g => g.hidden = false);
    $('kpiConsumo').textContent = fmt.num(r.consumo_total_kwh);
    $('kpiCusto').textContent = r.custo_estimado != null ? fmt.num(r.custo_estimado) : '—';
    $('kpiCustoUnit').textContent = r.custo_estimado != null ? `R$ · tarifa ${fmt.num(r.tarifa_kwh)} R$/kWh` : 'Defina a tarifa em Empresa';
    $('kpiMedia').textContent = fmt.num(r.media_diaria_kwh);
    $('kpiPico').textContent = r.pico_kwh_h != null ? fmt.num(r.pico_kwh_h) : '—';
    $('kpiAnterior').textContent = fmt.num(r.periodo_anterior_kwh);
    $('kpiVariacao').textContent = r.variacao_percentual != null ? `kWh · ${fmt.pct(r.variacao_percentual)} no período atual` : 'kWh · sem base de comparação';
    $('kpiAlertas').textContent = String(r.alertas_pendentes);

    $('graficoTitulo').textContent = `Consumo diário · ${r.registros_consumo} registro${r.registros_consumo === 1 ? '' : 's'}`;
    $('graficoTotal').textContent = fmt.num(r.consumo_total_kwh) + ' kWh';
    const area = $('graficoDias'); area.replaceChildren();
    const valores = r.por_dia.map(d => d.consumo_kwh);
    const g = KV.grafico(valores, r.por_dia.map(d => fmt.dia(d.data)));
    if (g) { g.classList.add('kv-chart-grande'); area.append(g); }
    else area.append(el('p', 'kv-empty-state', r.consumo_total_kwh > 0 ? 'Todo o consumo do período está concentrado em um único dia.' : 'Nenhum consumo registrado no período.'));
    $('estrutura').textContent = `${r.total_setores} setor(es) · ${r.total_maquinas} máquina(s) · ${r.total_sensores} sensor(es), ${r.sensores_online} online · ${r.leituras_no_periodo} leitura(s) no período`;

    preencherLista('listaSetores', r.por_setor, i => cardItem(i, r.consumo_total_kwh, 'fa-layer-group'), 'Nenhum consumo registrado no período.');
    preencherLista('listaMaquinas', r.por_maquina, i => cardItem(i, r.consumo_total_kwh, 'fa-industry'), 'Nenhum consumo registrado no período.');
    preencherLista('listaAlertas', r.alertas_recentes, a => {
      const [rotulo, classe] = STATUS[a.status_execucao] || [a.status_execucao, 'status-pendente'];
      const c = KV.card({ id: a.id_tomada_decisao, badge: rotulo, badgeClasse: classe });
      c.card.querySelector('.card-actions').replaceChildren(Object.assign(el('a', 'btn-action', 'Ver regras'), { href: 'decisoes.html' }));
      c.linha(a.nome_decisao || 'Regra', 'fa-scale-balanced', 'rule-name');
      c.linha(fmt.data(a.data_tomada_decisao), 'fa-calendar');
      c.linha(`Valor de referência: ${fmt.num(a.valor_referencia)} kWh`, 'fa-bolt');
      return c.card;
    }, 'Nenhuma regra de decisão foi acionada.');
    if (r.aviso) toast(r.aviso, 'info', 6000);
  }

  async function carregar() {
    const inicio = $('dataInicioRel').value, fim = $('dataFimRel').value;
    if (!inicio || !fim) return toast('Informe as datas inicial e final.', 'aviso');
    if (fim < inicio) return toast('A data final deve ser igual ou posterior à data inicial.', 'aviso');
    const botao = $('botaoAtualizar');
    ocupado(botao, true);
    $('estadoPainel').hidden = false; $('estadoPainel').textContent = 'Carregando indicadores...';
    try {
      relatorio = await requisicao('/relatorios/resumo?' + new URLSearchParams({ inicio, fim }));
      $('estadoPainel').hidden = true;
      $('conteudoPainel').hidden = false;
      desenhar(relatorio);
    } catch (erro) {
      $('estadoPainel').textContent = erro.message;
      toast(erro.message, 'erro');
    } finally { ocupado(botao, false); }
  }

  // Exporta o relatório em CSV (separador ";" e vírgula decimal, como o Excel em português)
  function exportar() {
    if (!relatorio) return toast('Carregue o relatório antes de exportar.', 'aviso');
    const n = v => v == null ? '' : String(v).replace('.', ',');
    const q = v => `"${String(v ?? '').replace(/"/g, '""')}"`;
    const linhas = [
      ['KLYVOLT — Relatório de consumo'], ['Período', fmt.dia(relatorio.inicio) + ' a ' + fmt.dia(relatorio.fim)],
      ['Consumo total (kWh)', n(relatorio.consumo_total_kwh)], ['Custo estimado (R$)', n(relatorio.custo_estimado)],
      ['Tarifa (R$/kWh)', n(relatorio.tarifa_kwh)], ['Média diária (kWh)', n(relatorio.media_diaria_kwh)],
      ['Período anterior (kWh)', n(relatorio.periodo_anterior_kwh)], ['Variação (%)', n(relatorio.variacao_percentual)], [],
      ['Consumo por setor'], ['Setor', 'Consumo (kWh)', 'Custo (R$)', 'Registros'],
      ...relatorio.por_setor.map(i => [q(i.nome), n(i.consumo_kwh), n(i.custo_estimado), i.registros]), [],
      ['Consumo por máquina'], ['Máquina', 'Setor', 'Consumo (kWh)', 'Custo (R$)', 'Registros'],
      ...relatorio.por_maquina.map(i => [q(i.nome), q(i.grupo), n(i.consumo_kwh), n(i.custo_estimado), i.registros]), [],
      ['Consumo por dia'], ['Data', 'Consumo (kWh)'], ...relatorio.por_dia.map(d => [fmt.dia(d.data), n(d.consumo_kwh)])
    ];
    const csv = '﻿' + linhas.map(l => l.join(';')).join('\r\n');
    const link = el('a');
    link.href = URL.createObjectURL(new Blob([csv], { type: 'text/csv;charset=utf-8' }));
    link.download = `klyvolt-relatorio-${relatorio.inicio}-a-${relatorio.fim}.csv`;
    document.body.append(link); link.click(); link.remove();
    setTimeout(() => URL.revokeObjectURL(link.href), 1000);
    toast('Relatório exportado em CSV.');
  }

  $('botaoAtualizar').addEventListener('click', carregar);
  $('botaoExportar').addEventListener('click', exportar);
  const [ini, fim] = periodoPadrao('mes');
  $('dataInicioRel').value = ini; $('dataFimRel').value = fim;
  KV.pronto.then(carregar).catch(() => {});
})();
