// Supabase local para TESTES — fala o mesmo protocolo HTTP do Supabase:
//   /rest/v1/*  (PostgREST: tabelas e RPC)   /auth/v1/*  (GoTrue: cadastro, login, sessão)
// Cada consulta roda no Postgres local como "anon" ou "authenticated", com
// request.jwt.claims — o mesmo mecanismo que o Supabase usa para aplicar RLS e GRANTs.
// Uso: KV_PGHOST=/caminho/socket KV_PGPORT=54329 KV_PGDB=klyvolt node servidor.js   (porta 54321)
const http = require('http');
const crypto = require('crypto');
const { execFileSync } = require('child_process');

const PORTA = Number(process.env.KV_PORTA || 54321);
const PG = { host: process.env.KV_PGHOST, port: process.env.KV_PGPORT || '54329', db: process.env.KV_PGDB || 'klyvolt' };
const SEGREDO = 'segredo-jwt-somente-para-testes-locais-klyvolt';
const config = { confirmarEmail: false, offline: false };
const refreshTokens = new Map(); // refresh -> user id
const links = new Map();         // email -> { access, refresh } (link de recuperação "enviado")

// ---------------- JWT (HS256, igual ao Supabase) ----------------
const b64 = o => Buffer.from(typeof o === 'string' ? o : JSON.stringify(o)).toString('base64url');
function assinar(payload) {
  const h = b64({ alg: 'HS256', typ: 'JWT' }), p = b64(payload);
  return `${h}.${p}.${crypto.createHmac('sha256', SEGREDO).update(`${h}.${p}`).digest('base64url')}`;
}
function verificar(token) {
  const partes = String(token || '').split('.');
  if (partes.length !== 3) return { erro: 'PGRST301', msg: 'Expected 3 parts in JWT; got ' + partes.length };
  const sig = crypto.createHmac('sha256', SEGREDO).update(`${partes[0]}.${partes[1]}`).digest('base64url');
  if (sig !== partes[2]) return { erro: 'PGRST301', msg: 'JWSError JWSInvalidSignature' };
  const payload = JSON.parse(Buffer.from(partes[1], 'base64url').toString());
  if (payload.exp && payload.exp < Date.now() / 1000) return { erro: 'PGRST303', msg: 'JWT expired' };
  return { payload };
}
const agora = () => Math.floor(Date.now() / 1000);
const CHAVE_ANON = assinar({ iss: 'supabase', ref: 'local', role: 'anon', iat: agora(), exp: agora() + 10 * 365 * 86400 });

// ---------------- Postgres ----------------
function psql(sql) {
  try {
    const out = execFileSync('psql', ['-X', '-q', '-A', '-t', '-v', 'ON_ERROR_STOP=1', '-h', PG.host, '-p', PG.port, '-U', 'postgres', '-d', PG.db],
      { input: '\\set VERBOSITY verbose\n' + sql, encoding: 'utf8', stdio: ['pipe', 'pipe', 'pipe'] });
    return { ok: true, out: out.trim() };
  } catch (e) {
    const err = String(e.stderr || e.message);
    const m = err.match(/ERROR:\s+([0-9A-Z]{5}):\s+([^\n]*)/);
    return { ok: false, code: m ? m[1] : 'XX000', message: m ? m[2] : err.split('\n')[0] };
  }
}
const ident = s => { if (!/^[a-z_][a-z0-9_]*$/.test(s)) throw Object.assign(new Error('coluna inválida: ' + s), { status: 400, code: 'PGRST100' }); return '"' + s + '"'; };
function lit(v) {
  if (v === null || v === undefined) return 'null';
  if (typeof v === 'number') return Number.isFinite(v) ? String(v) : 'null';
  if (typeof v === 'boolean') return v ? 'true' : 'false';
  if (typeof v === 'object') return "'" + JSON.stringify(v).replace(/'/g, "''") + "'::jsonb";
  return "'" + String(v).replace(/'/g, "''") + "'";
}
const colunas = s => !s || s.trim() === '*' ? '*' : s.split(',').map(c => ident(c.trim())).join(', ');
const OPS = { eq: '=', neq: '<>', gt: '>', gte: '>=', lt: '<', lte: '<=' };
function filtro(col, valor) {
  let neg = false;
  if (valor.startsWith('not.')) { neg = true; valor = valor.slice(4); }
  const i = valor.indexOf('.');
  const op = valor.slice(0, i), arg = valor.slice(i + 1);
  let sql;
  if (OPS[op]) sql = `${ident(col)} ${OPS[op]} ${lit(arg)}`;
  else if (op === 'in') {
    const itens = arg.replace(/^\(|\)$/g, '').split(',').filter(x => x !== '').map(x => lit(x.replace(/^"|"$/g, '')));
    sql = itens.length ? `${ident(col)} in (${itens.join(',')})` : 'false';
  } else if (op === 'is') sql = `${ident(col)} is ${arg === 'null' ? 'null' : arg === 'true' ? 'true' : 'false'}`;
  else throw Object.assign(new Error('operador não suportado: ' + op), { status: 400, code: 'PGRST100' });
  return neg ? `not (${sql})` : sql;
}
const RESERVADOS = new Set(['select', 'order', 'limit', 'offset', 'columns', 'on_conflict']);

function contexto(auth) {
  const token = (auth || '').replace(/^Bearer\s+/i, '');
  const v = verificar(token);
  if (v.erro) return { erro: v };
  const role = v.payload.role === 'authenticated' ? 'authenticated' : 'anon';
  return { role, sql: `begin;\nset local role ${role};\nselect set_config('request.jwt.claims', ${lit(JSON.stringify(v.payload))}, true) \\g /dev/null\n` };
}
function erroPg(r, role) {
  const status = { '23505': 409, '23503': 409, '42501': role === 'anon' ? 401 : 403, '42883': 404, '42P01': 404, '42703': 400 }[r.code] || 400;
  return { status, body: { code: r.code, message: r.message, details: null, hint: null } };
}

function rest(req, url, corpo) {
  const ctx = contexto(req.headers.authorization);
  if (ctx.erro) return { status: 401, body: { code: ctx.erro.erro, message: ctx.erro.msg, details: null, hint: null } };
  const partes = url.pathname.replace(/^\/rest\/v1\//, '').split('/');
  const prefer = String(req.headers.prefer || '');
  // ---- RPC ----
  if (partes[0] === 'rpc') {
    const fn = ident(partes[1]);
    const args = Object.entries(corpo || {}).map(([k, v]) => `${ident(k)} => ${lit(v)}`).join(', ');
    const tipo = psql(`select p.proretset from pg_proc p where p.proname = ${lit(partes[1])} and p.pronamespace = 'public'::regnamespace;`);
    if (!tipo.out) return { status: 404, body: { code: 'PGRST202', message: 'Could not find the function public.' + partes[1], details: null, hint: null } };
    const sql = tipo.out === 't' ? `select coalesce(json_agg(x), '[]'::json) from public.${fn}(${args}) x;` : `select to_json(public.${fn}(${args}));`;
    const r = psql(ctx.sql + sql + '\ncommit;');
    if (!r.ok) return erroPg(r, ctx.role);
    return { status: 200, body: JSON.parse(r.out || 'null') };
  }
  // ---- Tabelas ----
  const tabela = 'public.' + ident(partes[0]);
  const conds = [];
  for (const [k, v] of url.searchParams) if (!RESERVADOS.has(k)) conds.push(filtro(k, v));
  const where = conds.length ? ' where ' + conds.join(' and ') : '';
  const sel = colunas(url.searchParams.get('select'));
  const representacao = req.method === 'GET' || prefer.includes('return=representation');
  let sql;
  if (req.method === 'GET') {
    const ordem = (url.searchParams.get('order') || '').split(',').filter(Boolean).map(o => {
      const [c, dir, nulls] = o.split('.');
      return `${ident(c)} ${dir === 'desc' ? 'desc' : 'asc'}${nulls ? (nulls === 'nullsfirst' ? ' nulls first' : ' nulls last') : ''}`;
    }).join(', ');
    const lim = url.searchParams.get('limit'), off = url.searchParams.get('offset');
    const inner = `select ${sel} from ${tabela}${where}${ordem ? ' order by ' + ordem : ''}${lim ? ' limit ' + Number(lim) : ''}${off ? ' offset ' + Number(off) : ''}`;
    const cnt = prefer.includes('count=exact') ? `(select count(*) from ${tabela}${where})` : 'null';
    sql = `select json_build_object('rows', (select coalesce(json_agg(x), '[]'::json) from (${inner}) x), 'count', ${cnt});`;
  } else if (req.method === 'POST') {
    const linhas = Array.isArray(corpo) ? corpo : [corpo];
    const chaves = [...new Set(linhas.flatMap(l => Object.keys(l)))];
    const valores = linhas.map(l => '(' + chaves.map(k => k in l ? lit(l[k]) : 'default').join(', ') + ')').join(', ');
    sql = `with x as (insert into ${tabela} (${chaves.map(ident).join(', ')}) values ${valores} returning ${representacao ? sel : '1 as _'}) select json_build_object('rows', coalesce(json_agg(x), '[]'::json), 'count', count(*)) from x;`;
  } else if (req.method === 'PATCH') {
    const set = Object.entries(corpo).map(([k, v]) => `${ident(k)} = ${lit(v)}`).join(', ');
    sql = `with x as (update ${tabela} set ${set}${where} returning ${representacao ? sel : '1 as _'}) select json_build_object('rows', coalesce(json_agg(x), '[]'::json), 'count', count(*)) from x;`;
  } else if (req.method === 'DELETE') {
    sql = `with x as (delete from ${tabela}${where} returning ${representacao ? sel : '1 as _'}) select json_build_object('rows', coalesce(json_agg(x), '[]'::json), 'count', count(*)) from x;`;
  } else return { status: 405, body: { message: 'método não suportado' } };
  const r = psql(ctx.sql + sql + '\ncommit;');
  if (!r.ok) return erroPg(r, ctx.role);
  const { rows, count } = JSON.parse(r.out);
  const headers = {};
  if (prefer.includes('count=exact')) headers['Content-Range'] = `${rows.length ? '0-' + (rows.length - 1) : '*'}/${count ?? rows.length}`;
  const accept = String(req.headers.accept || '');
  if (accept.includes('vnd.pgrst.object')) {
    if (rows.length !== 1) return { status: 406, body: { code: 'PGRST116', message: 'JSON object requested, multiple (or no) rows returned', details: `The result contains ${rows.length} rows`, hint: null } };
    return { status: 200, body: rows[0], headers };
  }
  const st = req.method === 'POST' ? 201 : 200;
  if (!representacao) return { status: req.method === 'POST' ? 201 : 204, body: null, headers };
  return { status: st, body: rows, headers };
}

// ---------------- Auth (GoTrue) ----------------
function usuarioJson(u) {
  return {
    id: u.id, aud: 'authenticated', role: 'authenticated', email: u.email, phone: '',
    email_confirmed_at: u.email_confirmed_at, confirmed_at: u.email_confirmed_at, last_sign_in_at: new Date().toISOString(),
    app_metadata: { provider: 'email', providers: ['email'] }, user_metadata: u.raw_user_meta_data || {},
    identities: [{ id: u.id, identity_id: u.id, user_id: u.id, provider: 'email', identity_data: { email: u.email, sub: u.id },
      created_at: u.created_at, updated_at: u.created_at, last_sign_in_at: u.created_at, email: u.email }],
    created_at: u.created_at, updated_at: u.created_at, is_anonymous: false
  };
}
function buscarUsuario(cond) {
  const r = psql(`select coalesce(json_agg(u), '[]') from (select id, email, encrypted_password, email_confirmed_at, raw_user_meta_data, created_at from auth.users where ${cond}) u;`);
  return JSON.parse(r.out)[0] || null;
}
function sessao(u) {
  const refresh = crypto.randomBytes(16).toString('hex');
  refreshTokens.set(refresh, u.id);
  const exp = agora() + 3600;
  return { access_token: assinar({ aud: 'authenticated', exp, iat: agora(), sub: u.id, email: u.email, role: 'authenticated', session_id: crypto.randomUUID() }),
    token_type: 'bearer', expires_in: 3600, expires_at: exp, refresh_token: refresh, user: usuarioJson(u) };
}
const erroAuth = (status, error_code, msg) => ({ status, body: { code: status, error_code, msg } });
function usuarioDoToken(req) {
  const v = verificar((req.headers.authorization || '').replace(/^Bearer\s+/i, ''));
  if (v.erro || v.payload.role !== 'authenticated') return null;
  return buscarUsuario(`id = ${lit(v.payload.sub)}`);
}
function auth(req, url, corpo) {
  const rota = url.pathname.replace(/^\/auth\/v1\//, '');
  if (rota === 'signup' && req.method === 'POST') {
    const email = String(corpo.email || '').toLowerCase();
    const existente = buscarUsuario(`lower(email) = ${lit(email)}`);
    if (existente) {
      if (config.confirmarEmail) return { status: 200, body: { ...usuarioJson(existente), identities: [] } };
      return erroAuth(422, 'user_already_exists', 'User already registered');
    }
    if (String(corpo.password || '').length < 6) return erroAuth(422, 'weak_password', 'Password should be at least 6 characters.');
    const id = crypto.randomUUID();
    const r = psql(`insert into auth.users (id, email, aud, role, encrypted_password, email_confirmed_at, raw_user_meta_data)
      values (${lit(id)}, ${lit(email)}, 'authenticated', 'authenticated', ${lit(corpo.password)}, ${config.confirmarEmail ? 'null' : 'now()'}, ${lit(corpo.data || {})});`);
    if (!r.ok) { console.log('[signup] trigger:', r.message); return erroAuth(500, 'unexpected_failure', 'Database error saving new user'); }
    const u = buscarUsuario(`id = ${lit(id)}`);
    return { status: 200, body: config.confirmarEmail ? usuarioJson(u) : sessao(u) };
  }
  if (rota === 'token' && req.method === 'POST') {
    const tipo = url.searchParams.get('grant_type');
    if (tipo === 'password') {
      const u = buscarUsuario(`lower(email) = ${lit(String(corpo.email || '').toLowerCase())}`);
      if (!u || u.encrypted_password !== corpo.password) return erroAuth(400, 'invalid_credentials', 'Invalid login credentials');
      if (!u.email_confirmed_at) return erroAuth(400, 'email_not_confirmed', 'Email not confirmed');
      return { status: 200, body: sessao(u) };
    }
    if (tipo === 'refresh_token') {
      const id = refreshTokens.get(corpo.refresh_token);
      if (!id) return erroAuth(400, 'refresh_token_not_found', 'Invalid Refresh Token: Refresh Token Not Found');
      refreshTokens.delete(corpo.refresh_token);
      return { status: 200, body: sessao(buscarUsuario(`id = ${lit(id)}`)) };
    }
  }
  if (rota === 'user' && req.method === 'GET') {
    const u = usuarioDoToken(req);
    return u ? { status: 200, body: usuarioJson(u) } : erroAuth(403, 'bad_jwt', 'invalid JWT: unable to parse or verify signature');
  }
  if (rota === 'user' && req.method === 'PUT') {
    const u = usuarioDoToken(req);
    if (!u) return erroAuth(403, 'bad_jwt', 'invalid JWT: unable to parse or verify signature');
    if (corpo.password) {
      if (corpo.password === u.encrypted_password) return erroAuth(422, 'same_password', 'New password should be different from the old password.');
      psql(`update auth.users set encrypted_password = ${lit(corpo.password)} where id = ${lit(u.id)};`);
    }
    return { status: 200, body: usuarioJson(buscarUsuario(`id = ${lit(u.id)}`)) };
  }
  if (rota === 'logout' && req.method === 'POST') {
    const u = usuarioDoToken(req);
    if (u) for (const [t, id] of refreshTokens) if (id === u.id) refreshTokens.delete(t);
    return { status: 204, body: null };
  }
  if (rota === 'recover' && req.method === 'POST') {
    const email = String(corpo.email || '').toLowerCase();
    const u = buscarUsuario(`lower(email) = ${lit(email)}`);
    if (u) { const s = sessao(u); links.set(email, { access_token: s.access_token, refresh_token: s.refresh_token, redirect_to: url.searchParams.get('redirect_to') }); }
    return { status: 200, body: {} };
  }
  return erroAuth(404, 'not_found', 'rota de autenticação não emulada: ' + req.method + ' ' + rota);
}

// ---------------- Rotas auxiliares de TESTE ----------------
function teste(req, url, corpo) {
  const rota = url.pathname.replace(/^\/__teste\//, '');
  if (rota === 'config') { Object.assign(config, corpo); return { status: 200, body: config }; }
  if (rota === 'confirmar') { psql(`update auth.users set email_confirmed_at = now() where lower(email) = ${lit(String(corpo.email).toLowerCase())};`); return { status: 200, body: {} }; }
  if (rota === 'link') return { status: 200, body: links.get(String(url.searchParams.get('email')).toLowerCase()) || null };
  if (rota === 'sql') { const r = psql(corpo.sql); return { status: r.ok ? 200 : 400, body: r }; }
  if (rota === 'chave_anon') return { status: 200, body: { chave: CHAVE_ANON } };
  if (rota === 'token_expirado') {
    const u = buscarUsuario(`lower(email) = ${lit(String(url.searchParams.get('email')).toLowerCase())}`);
    return { status: 200, body: { token: assinar({ aud: 'authenticated', exp: agora() - 60, iat: agora() - 3660, sub: u.id, email: u.email, role: 'authenticated' }) } };
  }
  return { status: 404, body: {} };
}

http.createServer((req, res) => {
  let dados = '';
  req.on('data', c => dados += c);
  req.on('end', () => {
    const url = new URL(req.url, 'http://localhost');
    if (config.offline && !url.pathname.startsWith('/__teste/')) { req.socket.destroy(); return; }
    let r;
    try {
      const corpo = dados ? JSON.parse(dados) : {};
      if (url.pathname.startsWith('/rest/v1/')) {
        if (req.headers.apikey !== CHAVE_ANON) r = { status: 401, body: { message: 'Invalid API key' } };
        else r = rest(req, url, corpo);
      } else if (url.pathname.startsWith('/auth/v1/')) {
        if (req.headers.apikey !== CHAVE_ANON) r = { status: 401, body: { message: 'Invalid API key' } };
        else r = auth(req, url, corpo);
      } else if (url.pathname.startsWith('/__teste/')) r = teste(req, url, corpo);
      else r = { status: 404, body: { message: 'não encontrado' } };
    } catch (e) {
      r = { status: e.status || 500, body: { code: e.code || 'XX000', message: e.message } };
    }
    res.writeHead(r.status, { 'Content-Type': 'application/json', ...(r.headers || {}) });
    res.end(r.body === null || r.status === 204 ? '' : JSON.stringify(r.body));
  });
}).listen(PORTA, '127.0.0.1', () => console.log(`Supabase local de testes em http://127.0.0.1:${PORTA}`));
