
(() => {
  'use strict';
  const BASE = (window.KV_API_BASE || 'http://127.0.0.1:8000').replace(/\/+$/, '');
 
  /* ---------- conversores ---------- */
  const num = v => (v === '' || v == null || !Number.isFinite(Number(v))) ? null : Number(v);
  const str = v => { const s = String(v ?? '').trim(); return s === '' ? null : s; };
  // datetime-local "2026-10-29T08:00" -> "2026-10-29T08:00:00"
  const toDt = v => { const s = str(v); return s && s.length === 16 ? s + ':00' : s; };
  // ISO vindo da API -> valor aceito por <input type="datetime-local">
  const fromDt = v => {
    if (!v) return '';
    const s = String(v);
    if (/[zZ]$|[+-]\d\d:?\d\d$/.test(s)) {
      const d = new Date(s); if (Number.isNaN(d.getTime())) return '';
      const p = n => String(n).padStart(2, '0');
      return d.getFullYear() + '-' + p(d.getMonth() + 1) + '-' + p(d.getDate()) + 'T' + p(d.getHours()) + ':' + p(d.getMinutes());
    }
    return s.slice(0, 16);
  };
  const fromDate = v => v ? String(v).slice(0, 10) : '';
  const n0 = v => (v == null || v === '') ? null : Number(v); // Decimal pode vir como texto
 
  /* ---------- recursos ----------
     path : prefixo da rota, igual ao /docs do backend (ex.: /maquinas), sem barra final
     fields: campos que o front envia (usado só pelo KV.verify)
     [CONFIRMADO]  nomes que aparecem nos comandos SQL simulados do HTML original
     [CONFERIR]    nomes presumidos; rode KV.verify() e ajuste se divergirem */
  const R = {
    maquina: { path: '/maquinas', // [CONFERIR] nomes vindos do schemas.py descrito antes
      fields: ['nome_maquina', 'numero_serie', 'potencia_nominal', 'id_setor', 'descricao_maquina'],
      toApi: f => ({ nome_maquina: str(f.nome), numero_serie: str(f.codigo), potencia_nominal: num(f.potencia), id_setor: num(f.idSetor), descricao_maquina: str(f.localizacao) }),
      fromApi: r => ({ id: r.id_maquina, nome: r.nome_maquina, codigo: r.numero_serie, potencia: n0(r.potencia_nominal), idSetor: r.id_setor, localizacao: r.descricao_maquina || '' }) },
 
    setor: { path: '/setores', // [CONFIRMADO] nome_setor, divisao_setor, id_usuario_responsavel
      fields: ['nome_setor', 'divisao_setor', 'id_usuario_responsavel'],
      toApi: f => ({ nome_setor: str(f.nome), divisao_setor: str(f.divisao), id_usuario_responsavel: num(f.idResp) }),
      fromApi: r => ({ id: r.id_setor, nome: r.nome_setor, divisao: String(r.divisao_setor || '').toLowerCase(), idResp: r.id_usuario_responsavel }) },
 
    consumo: { path: '/consumos', // [CONFIRMADO] data_inicio, data_fim, consumo_kwh, id_maquina
      fields: ['data_inicio', 'data_fim', 'consumo_kwh', 'id_maquina'],
      toApi: f => ({ data_inicio: toDt(f.inicio), data_fim: toDt(f.fim), consumo_kwh: num(f.kwh), id_maquina: num(f.idMaquina) }),
      fromApi: r => ({ id: r.id_consumo, inicio: fromDt(r.data_inicio), fim: fromDt(r.data_fim), kwh: n0(r.consumo_kwh), idMaquina: r.id_maquina }) },
 
    leitura: { path: '/leituras', // [CONFIRMADO] data_leitura, valor_medido_kwh, observacao_leitura, id_sensor, id_usuario
      fields: ['data_leitura', 'valor_medido_kwh', 'observacao_leitura', 'id_sensor', 'id_usuario'],
      toApi: f => ({
        data_leitura: toDt(f.data), valor_medido_kwh: num(f.valor), observacao_leitura: str(f.obs),
        id_sensor: num(f.idSensor), id_usuario: num(f.idUsuario),
        ...(f.idConsumo != null ? { id_consumo: Number(f.idConsumo) } : {}) // preserva a agregação existente no PUT
      }),
      fromApi: r => ({ id: r.id_leitura, data: fromDt(r.data_leitura), valor: n0(r.valor_medido_kwh), obs: r.observacao_leitura || '', idSensor: r.id_sensor, idUsuario: r.id_usuario ?? null, idConsumo: r.id_consumo ?? null }) },
 
    sensor: { path: '/sensores', // [CONFERIR] o schema de sensor não foi enviado; nomes presumidos
      fields: ['numero_serie', 'fabricante', 'modelo', 'tipo_sensor', 'unidade_medida', 'protocolo', 'mac_address', 'endereco_ip', 'token_autenticacao', 'status_conexao', 'status_sensor', 'data_instalacao', 'data_ultima_calibracao', 'id_maquina'],
      toApi: f => ({
        numero_serie: str(f.serie), fabricante: str(f.fabricante), modelo: str(f.modelo), tipo_sensor: str(f.tipo), unidade_medida: str(f.unidade),
        protocolo: str(f.protocolo), mac_address: str(f.mac), endereco_ip: str(f.ip), token_autenticacao: str(f.token),
        status_conexao: str(f.statusConexao), status_sensor: str(f.status), data_instalacao: str(f.instalacao), data_ultima_calibracao: str(f.calibracao),
        id_maquina: num(f.idMaquina)
      }),
      fromApi: r => ({
        id: r.id_sensor, serie: r.numero_serie, fabricante: r.fabricante || '', modelo: r.modelo || '', tipo: r.tipo_sensor, unidade: r.unidade_medida,
        protocolo: r.protocolo, mac: r.mac_address, ip: r.endereco_ip || '', token: r.token_autenticacao || '',
        statusConexao: r.status_conexao, status: r.status_sensor, instalacao: fromDate(r.data_instalacao), calibracao: fromDate(r.data_ultima_calibracao),
        idMaquina: r.id_maquina
      }) },
 
    // Ainda sem tela / sem mapeamento: aparecem no KV.verify() para você conferir as rotas.
    usuario: { path: '/usuarios', fields: [] },
    empresa: { path: '/empresas', fields: [] },
    decisao: { path: '/decisoes', fields: [] },
    tomada_decisao: { path: '/tomadas-decisao', fields: [] }
  };
 
  /* ---------- requisições ---------- */
  class ApiError extends Error { constructor(message, status, body) { super(message); this.status = status; this.body = body; } }
 
  function describe(status, body) {
    const d = body && body.detail;
    if (Array.isArray(d)) { // 422 do FastAPI
      return d.map(e => (Array.isArray(e.loc) ? e.loc.filter(x => x !== 'body').join('.') + ': ' : '') + (e.msg || '')).join('\n');
    }
    if (typeof d === 'string') return d; // 400/404/409 com mensagem
    if (status === 404) return 'Registro não encontrado.';
    if (status === 405) return 'Esta operação não é permitida pelo servidor.';
    if (status === 409) return 'Operação recusada: há registros vinculados.';
    if (status >= 500) return 'Erro interno no servidor (' + status + '). Veja o terminal do uvicorn.';
    return 'Falha na requisição (' + status + ').';
  }
 
  async function request(method, path, body) {
    const headers = { Accept: 'application/json' };
    if (body !== undefined) headers['Content-Type'] = 'application/json';
    try { const t = sessionStorage.getItem('klyvolt.token'); if (t) headers.Authorization = 'Bearer ' + t; } catch (_) { /* sem token */ }
    let res;
    try { res = await fetch(BASE + path, { method, headers, body: body === undefined ? undefined : JSON.stringify(body) }); }
    catch (_) { throw new ApiError('Não foi possível conectar ao servidor em ' + BASE + '. Ele está rodando e com CORS liberado para esta origem?', 0); }
    if (res.status === 204) return null;
    let data = null; try { data = await res.json(); } catch (_) { /* corpo vazio */ }
    if (!res.ok) throw new ApiError(describe(res.status, data), res.status, data);
    return data;
  }
 
  const def = name => { if (!R[name]) throw new Error('Recurso desconhecido: ' + name); return R[name]; };
  const map = (d, r) => d.fromApi ? d.fromApi(r) : r;
 
  const KV = {
    base: BASE,
    ApiError,
    async list(name) { const d = def(name); const rows = await request('GET', d.path); return (Array.isArray(rows) ? rows : []).map(r => map(d, r)); },
    async get(name, id) { const d = def(name); return map(d, await request('GET', d.path + '/' + encodeURIComponent(id))); },
    async create(name, front) { const d = def(name); return map(d, await request('POST', d.path, d.toApi(front))); },
    async update(name, id, front) { const d = def(name); return map(d, await request('PUT', d.path + '/' + encodeURIComponent(id), d.toApi(front))); },
    async remove(name, id) { const d = def(name); await request('DELETE', d.path + '/' + encodeURIComponent(id)); return true; },
    message(e) { return e instanceof ApiError ? e.message : 'Erro inesperado: ' + (e && e.message ? e.message : e); },
    /* confere rotas e campos contra o /openapi.json do backend */
    async verify() {
      const spec = await (await fetch(BASE + '/openapi.json')).json();
      const paths = Object.keys(spec.paths || {});
      const resolve = s => (s && s.$ref) ? (spec.components.schemas[s.$ref.split('/').pop()] || {}) : (s || {});
      const rows = Object.entries(R).map(([name, d]) => {
        const own = paths.filter(p => p === d.path || p.startsWith(d.path + '/'));
        const postPath = own.find(p => !p.includes('{') && spec.paths[p].post);
        const schema = resolve(postPath && spec.paths[postPath].post.requestBody?.content?.['application/json']?.schema);
        const props = Object.keys(schema.properties || {}), req = schema.required || [];
        return {
          recurso: name,
          'rotas encontradas': own.map(p => Object.keys(spec.paths[p]).map(m => m.toUpperCase() + ' ' + p).join(', ')).join(' | ') || 'NENHUMA — ajuste "path"',
          'obrigatórios que o front não envia': d.fields.length ? (req.filter(k => !d.fields.includes(k)).join(', ') || '-') : '(sem mapeamento)',
          'enviados mas desconhecidos no schema': d.fields.length && props.length ? (d.fields.filter(k => !props.includes(k)).join(', ') || '-') : '-'
        };
      });
      console.table(rows);
      return rows;
    }
  };
  window.KV = KV;
})();
 