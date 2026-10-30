// Testes ponta a ponta do KLYVOLT no navegador (Chromium):
// página (127.0.0.1:5500) → JavaScript → FastAPI (127.0.0.1:8000) → Supabase local → Postgres com RLS.
// Pré-requisito: testes/subir_ambiente.sh. Uso: KV_OUT=./capturas node testes/e2e/run.js
const { chromium } = require(process.env.PLAYWRIGHT_PATH || 'playwright');
const fs = require('fs'), path = require('path');
const OUT = process.env.KV_OUT || path.join(__dirname, '..', 'capturas'); fs.mkdirSync(OUT, { recursive: true });
const FA = process.env.FA_PATH || path.join(__dirname, 'node_modules/@fortawesome/fontawesome-free');
const SITE = 'http://127.0.0.1:5500', API = 'http://127.0.0.1:8000', SUPA = 'http://127.0.0.1:54321';
const results = [], consoleErrors = [];

async function sup(rota, corpo) {
  const r = await fetch(SUPA + rota, corpo ? { method: 'POST', headers: { 'content-type': 'application/json' }, body: JSON.stringify(corpo) } : {});
  return r.json();
}
const sql = async q => (await sup('/__teste/sql', { sql: q })).out;
async function contexto(browser, opcoes = {}) {
  const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 }, locale: 'pt-BR', timezoneId: 'America/Sao_Paulo', colorScheme: 'dark', acceptDownloads: true, ...opcoes });
  // Recursos externos (fontes e ícones) servidos localmente; a API e o site são acessados de verdade.
  await ctx.route(/cdnjs\.cloudflare\.com|fonts\.googleapis\.com|fonts\.gstatic\.com/, route => {
    const u = new URL(route.request().url());
    if (u.pathname.endsWith('all.min.css')) return route.fulfill({ path: FA + '/css/all.min.css', contentType: 'text/css' });
    if (u.pathname.includes('/webfonts/')) return route.fulfill({ path: FA + '/webfonts/' + path.basename(u.pathname), contentType: 'font/woff2' });
    return route.fulfill({ body: '', contentType: 'text/css' });
  });
  return ctx;
}
async function pagina(ctx, nome) {
  const p = await ctx.newPage();
  p.on('pageerror', e => consoleErrors.push(`[${nome}] pageerror: ${e.message}`));
  p.on('console', m => {
    const t = m.text();
    if (m.type() === 'error' && !/Failed to load resource/.test(t)) consoleErrors.push(`[${nome}] ${t}`);
  });
  return p;
}
async function step(nome, fn) {
  try { const det = await fn(); results.push({ nome, ok: true, det: det == null ? '' : String(det) }); console.log('✔', nome, det ?? ''); }
  catch (e) { results.push({ nome, ok: false, det: String(e.message || e).split('\n')[0] }); console.log('✘', nome, '→', String(e.message || e).split('\n')[0]); }
}
const assert = (c, m) => { if (!c) throw new Error(m || 'falhou'); };
const esperarToast = async (p, re) => {
  await p.waitForFunction(r => [...document.querySelectorAll('.kv-toast')].some(t => new RegExp(r).test(t.innerText)), re.source, { timeout: 8000 });
  return (await p.locator('.kv-toast').allInnerTexts()).filter(t => re.test(t)).pop().trim();
};
const estavel = p => p.waitForFunction(() => !document.querySelector('[aria-busy]'), null, { timeout: 8000 });
const limparToasts = p => p.evaluate(() => document.querySelectorAll('.kv-toast').forEach(t => t.remove()));
const ir = async (p, rel) => { await p.goto(SITE + rel); await p.waitForLoadState('networkidle'); await p.waitForTimeout(250); };
const cards = p => p.locator('.decision-card:visible');
const hoje = () => { const d = new Date(), z = n => String(n).padStart(2, '0'); return `${d.getFullYear()}-${z(d.getMonth() + 1)}-${z(d.getDate())}`; };
const foto = (p, nome) => p.screenshot({ path: path.join(OUT, nome + '.png'), fullPage: true });

(async () => {
  await sup('/__teste/config', { confirmarEmail: false, offline: false });
  const browser = await chromium.launch();
  const ctxA = await contexto(browser);
  const p = await pagina(ctxA, 'A');
  const A = { email: 'ana@confeccoesqa.com.br', senha: 'Energia2026' };

  await step('01 Página inicial pública: menu com Painel e Máquinas, botão "Entrar" para visitantes', async () => {
    await ir(p, '/index.html');
    const links = await p.locator('.kv-nav-links a').allInnerTexts();
    assert(links.includes('Painel') && links.includes('Máquinas'), links.join());
    const acao = (await p.locator('.kv-action').innerText()).trim();
    assert(acao === 'Entrar', acao);
    return links.join(' · ') + ' | ação: ' + acao;
  });
  await step('02 Página interna sem login redireciona para Entrar', async () => {
    await ir(p, '/pages/consumos.html');
    await p.waitForURL(/entrar\.html\?entrar=1&voltar=consumos/, { timeout: 6000 });
    assert(await p.locator('#formLogin').isVisible());
    return p.url().replace(SITE, '');
  });
  await step('03 Cadastro: validação de CNPJ no navegador', async () => {
    await p.click('#tabA');
    await p.fill('#cnpj', '11222333000182'); await p.fill('#nome', 'Confecções QA'); await p.fill('#responsavel', 'Ana Souza');
    await p.fill('#email', A.email); await p.fill('#telefone', '44999998888'); await p.fill('#senha', A.senha);
    await p.click('#formCadastro button[type=submit]');
    return esperarToast(p, /CNPJ inválido/);
  });
  await step('04 Cadastro da empresa pela API (POST /empresas) → sessão → volta à página pedida', async () => {
    await limparToasts(p);
    await p.fill('#cnpj', '11222333000181');
    assert(await p.inputValue('#cnpj') === '11.222.333/0001-81' && await p.inputValue('#telefone') === '(44) 99999-8888', 'máscaras');
    await p.click('#formCadastro button[type=submit]');
    await p.waitForURL(/consumos\.html/, { timeout: 8000 });
    await esperarToast(p, /Bem-vindo/);
    return await sql("select cnpj||' | '||nome_empresa||' | '||(select tipo_usuario from usuario u where u.id_empresa=e.id_empresa) from empresa e where email_empresa='ana@confeccoesqa.com.br';");
  });
  await step('05 Consumos sem registros: estado vazio, KPIs ocultos', async () => {
    await estavel(p);
    const vazio = await p.locator('.kv-empty-state').first().innerText();
    assert(/Nenhum consumo/.test(vazio) && await p.locator('.kpi-grid:visible').count() === 0, vazio);
    await foto(p, 'consumos-vazio-escuro'); return vazio;
  });

  // ---------------- Setores
  await step('06 Setores: cadastrar (responsável vem de GET /usuarios)', async () => {
    await ir(p, '/pages/setores.html');
    await p.click('.btn-add');
    assert((await p.locator('#idResponsavel option').allInnerTexts()).some(o => /Ana Souza/.test(o)), 'responsável');
    await p.fill('#nomeSetor', 'Costura Principal'); await p.selectOption('#divisaoSetor', 'costura');
    await p.click('#modalActions .btn-confirm');
    const t = await esperarToast(p, /Setor cadastrado/); await p.waitForSelector('.decision-card');
    return t + ' | cards: ' + await cards(p).count();
  });
  await step('07 Setores: nome repetido → 409 com mensagem clara', async () => {
    await limparToasts(p);
    await p.click('.btn-add'); await p.fill('#nomeSetor', 'Costura Principal'); await p.click('#modalActions .btn-confirm');
    const t = await esperarToast(p, /Já existe um setor/); await p.click('#modalActions .btn-cancel'); return t;
  });
  await step('08 Setores: editar (PUT), filtrar e buscar sem quebrar o layout', async () => {
    await limparToasts(p);
    await p.click('.decision-card .btn-view'); await p.click('#modalActions .btn-confirm');
    await p.fill('#nomeSetor', 'Costura Reta'); await p.click('#modalActions .btn-confirm');
    await esperarToast(p, /Setor atualizado/); await p.waitForTimeout(300);
    assert(/Costura Reta/.test(await p.locator('.decision-card .rule-name').innerText()));
    await p.click('.tab:has-text("Corte")'); const n1 = await cards(p).count();
    await p.click('.tab:has-text("Costura")'); const n2 = await cards(p).count();
    await p.click('.tab:has-text("Todos")'); await p.fill('#searchInput', 'zzz'); await p.dispatchEvent('#searchInput', 'keyup');
    const n3 = await cards(p).count(); await p.fill('#searchInput', ''); await p.dispatchEvent('#searchInput', 'keyup');
    const disp = await p.locator('.decision-card').evaluate(e => getComputedStyle(e).display);
    assert(n1 === 0 && n2 === 1 && n3 === 0 && disp === 'flex', `${n1}/${n2}/${n3}/${disp}`);
    return `corte=${n1} costura=${n2} busca=${n3} display=${disp}`;
  });
  await step('09 Setores: segundo setor', async () => {
    await limparToasts(p);
    await p.click('.btn-add'); await p.fill('#nomeSetor', 'Corte'); await p.selectOption('#divisaoSetor', 'corte'); await p.click('#modalActions .btn-confirm');
    await esperarToast(p, /Setor cadastrado/); await estavel(p); return await cards(p).count() + ' setores';
  });

  // ---------------- Máquinas
  await step('10 Máquinas: cadastrar (POST /maquinas)', async () => {
    await ir(p, '/pages/maquinas.html');
    assert(/Nenhuma máquina/.test(await p.locator('.kv-empty-state').innerText()));
    await p.click('.btn-add');
    await p.fill('#nomeMaquina', 'Overloque 01'); await p.fill('#descricaoMaquina', 'Overloque industrial 4 fios');
    await p.fill('#potenciaNominal', '550'); await p.fill('#numeroSerieMaquina', 'OVL-001');
    await p.selectOption('#idSetor', { label: 'Costura Reta' });
    await p.click('#modalActions .btn-confirm'); const t = await esperarToast(p, /Máquina cadastrada/); await p.waitForTimeout(300);
    assert(/Nenhum sensor vinculado/.test(await p.locator('.decision-card').innerText())); return t;
  });
  await step('11 Máquinas: validação de potência e segunda máquina', async () => {
    await limparToasts(p);
    await p.click('.btn-add'); await p.fill('#nomeMaquina', 'Galoneira 02'); await p.fill('#descricaoMaquina', 'Galoneira'); await p.fill('#potenciaNominal', '-5');
    await p.selectOption('#idSetor', { label: 'Corte' }); await p.click('#modalActions .btn-confirm');
    const t = await esperarToast(p, /maior que zero/);
    await limparToasts(p); await p.fill('#potenciaNominal', '600'); await p.click('#modalActions .btn-confirm'); await esperarToast(p, /Máquina cadastrada/); await estavel(p);
    await p.click('.tab:has-text("Sem sensor")'); const n = await cards(p).count(); await p.click('.tab:has-text("Todas")');
    return `${t} | sem sensor=${n}`;
  });

  // ---------------- Sensores
  await step('12 Sensores: cadastro com máquina e token (token nunca volta da API)', async () => {
    await ir(p, '/pages/sensores.html');
    await p.click('.btn-add');
    await p.fill('#numeroSerie', 'SN-QA-001'); await p.fill('#fabricante', 'Siemens');
    await p.fill('#macAddress', '0e4b517a9c3f'); await p.dispatchEvent('#macAddress', 'input');
    assert(await p.inputValue('#macAddress') === '0E:4B:51:7A:9C:3F');
    await p.fill('#token', 'tk_sensor_qa_0001'); await p.selectOption('#idMaquina', { label: 'Overloque 01' });
    await p.click('#modalActions .btn-confirm'); const t = await esperarToast(p, /Sensor cadastrado/); await p.waitForTimeout(300);
    assert(/Máquina: Overloque 01/.test(await p.locator('.decision-card').innerText()));
    await p.click('.decision-card .btn-view'); assert(await p.inputValue('#token') === '', 'token exposto'); await p.click('.close-btn');
    assert(await sql("select token_autenticacao from sensor where numero_serie='SN-QA-001';") === 'tk_sensor_qa_0001');
    return t;
  });
  await step('13 Sensores: IP inválido recusado', async () => {
    await limparToasts(p);
    await p.click('.btn-add'); await p.fill('#numeroSerie', 'SN-X'); await p.fill('#macAddress', 'AA:00:00:00:00:99'); await p.fill('#enderecoIp', '999.1.1.1');
    await p.selectOption('#idMaquina', { label: 'Overloque 01' }); await p.click('#modalActions .btn-confirm');
    const t = await esperarToast(p, /IP inválido/); await p.click('#modalActions .btn-cancel'); return t;
  });

  // ---------------- Decisões
  await step('14 Decisões: cadastrar regras de leitura e de consumo', async () => {
    await ir(p, '/pages/decisoes.html');
    for (const [nome, crit, op, lim] of [['Leitura alta', 'valor_medido_kwh', '>', '10'], ['Consumo diário alto', 'consumo_kwh', '>=', '20']]) {
      await limparToasts(p);
      await p.click('.btn-add'); await p.fill('#nomeDecisao', nome); await p.selectOption('#criterioDecisao', crit);
      await p.selectOption('#operadorDecisao', op); await p.fill('#limiteDecisao', lim); await p.click('#modalActions .btn-confirm');
      await esperarToast(p, /Regra cadastrada/); await p.waitForTimeout(250);
    }
    await p.click('.tab:has-text("Maior")'); const n = await cards(p).count(); await p.click('.tab:has-text("Todas")');
    assert(n === 2, 'filtro ' + n); return `${await cards(p).count()} regras; filtro ">" = ${n}`;
  });

  // ---------------- Leituras
  await step('15 Leituras: leitura acima do limite → aviso do motor de decisão', async () => {
    await ir(p, '/pages/leituras.html');
    await p.click('.btn-add'); await p.fill('#dataLeitura', hoje() + 'T09:00'); await p.fill('#valorMedido', '12.5'); await p.selectOption('#idSensor', { index: 1 });
    await p.click('#modalActions .btn-confirm');
    return await esperarToast(p, /Regra de decisão acionada/);
  });
  await step('16 Leituras: segunda leitura e KPIs calculados', async () => {
    await limparToasts(p);
    await p.click('.btn-add'); await p.fill('#dataLeitura', hoje() + 'T10:00'); await p.fill('#valorMedido', '4'); await p.selectOption('#idSensor', { index: 1 });
    await p.click('#modalActions .btn-confirm'); await esperarToast(p, /Leitura registrada/); await estavel(p);
    const k = (await p.locator('.kpi-grid').innerText()).replace(/\s+/g, ' ');
    assert(/LEITURAS HOJE 2/i.test(k), k); return k;
  });
  await step('17 Leituras: mesmo sensor e horário → 409', async () => {
    await limparToasts(p);
    await p.click('.btn-add'); await p.fill('#dataLeitura', hoje() + 'T10:00'); await p.fill('#valorMedido', '1'); await p.selectOption('#idSensor', { index: 1 });
    await p.click('#modalActions .btn-confirm'); const t = await esperarToast(p, /mesmo horário/); await p.click('#modalActions .btn-cancel'); return t;
  });

  // ---------------- Consumos
  await step('18 Consumos: cálculo pelas leituras (GET /consumos/calcular) e registro', async () => {
    await ir(p, '/pages/consumos.html');
    await p.click('.btn-add'); await p.selectOption('#idMaquina', { label: 'Overloque 01' });
    await p.fill('#dataInicio', hoje() + 'T00:00'); await p.dispatchEvent('#dataInicio', 'change');
    await p.fill('#dataFim', hoje() + 'T23:59'); await p.dispatchEvent('#dataFim', 'change');
    await p.waitForFunction(() => document.getElementById('consumoKwh').value !== '', null, { timeout: 6000 });
    const v = await p.inputValue('#consumoKwh'); assert(v === '16.50', v);
    await p.click('#modalActions .btn-confirm'); await esperarToast(p, /Consumo registrado/); await estavel(p);
    return v + ' kWh';
  });
  await step('19 Consumos: KPIs reais e aviso de tarifa não definida', async () => {
    const k = (await p.locator('.kpi-grid').first().innerText()).replace(/\s+/g, ' ');
    const k2 = (await p.locator('#kpiCustos').innerText()).replace(/\s+/g, ' ');
    assert(/16,50/.test(k) && /Defina a tarifa/i.test(k2), k + ' | ' + k2);
    assert(/2 leituras agregadas/.test(await p.locator('.decision-card').innerText()));
    return k;
  });
  await step('20 Leituras agregadas automaticamente pelo banco', async () => {
    await ir(p, '/pages/leituras.html');
    const b = await p.locator('.status-badge').allInnerTexts();
    assert(b.length === 2 && b.every(x => x === 'Agregada'), b.join()); return b.join(', ');
  });

  // ---------------- Empresa, tarifa e custos
  await step('21 Empresa: dados e tarifa (PUT /empresas/{id})', async () => {
    await ir(p, '/pages/empresa.html');
    assert(await p.inputValue('#perfilCnpj') === '11.222.333/0001-81');
    await p.fill('#perfilTarifa', '0,90'); await p.click('#botaoSalvarEmpresa');
    const t = await esperarToast(p, /atualizados/); await foto(p, 'empresa-dados-escuro'); return t;
  });
  await step('22 Consumos: custo com a tarifa (16,50 × 0,90 = R$ 14,85)', async () => {
    await ir(p, '/pages/consumos.html');
    const k2 = (await p.locator('#kpiCustos').innerText()).replace(/\s+/g, ' ');
    assert(/14,85/.test(k2) && /R\$\s?14,85/.test(await p.locator('.decision-card').innerText()), k2);
    await foto(p, 'consumos-com-dados-escuro'); return k2;
  });
  await step('23 Máquinas: consumo e custo por máquina', async () => {
    await ir(p, '/pages/maquinas.html');
    const t = await p.locator('.decision-card', { hasText: 'Overloque 01' }).innerText();
    assert(/16,50 kWh/.test(t) && /14,85/.test(t), t); return 'ok';
  });
  await step('24 Novo registro: cadastrar e salvar alterações', async () => {
    await ir(p, '/pages/registrar-consumo.html');
    assert(await p.locator('#btnSalvar').isDisabled());
    const d = new Date(); d.setDate(d.getDate() - 1); const z = n => String(n).padStart(2, '0');
    const ontem = `${d.getFullYear()}-${z(d.getMonth() + 1)}-${z(d.getDate())}`;
    await p.click('#data_inicio'); await p.fill('#data_inicio', ontem); await p.click('#data_fim'); await p.fill('#data_fim', ontem);
    await p.fill('#consumo', '25,40'); await p.selectOption('#maquina', { label: 'Galoneira 02' });
    await p.click('#btnCadastrar'); const t1 = await esperarToast(p, /cadastrado/);
    await limparToasts(p); await p.fill('#consumo', '26'); await p.click('#btnSalvar'); const t2 = await esperarToast(p, /atualizado/);
    assert(await sql("select consumo_kwh from consumo c join maquina m using (id_maquina) where m.nome_maquina='Galoneira 02';") === '26.00');
    return `${t1} | ${t2}`;
  });

  // ---------------- Decisões: histórico
  await step('25 Decisões: acionamentos reais e registro do resultado (PUT /tomadas-decisao)', async () => {
    await ir(p, '/pages/decisoes.html');
    await p.locator('.decision-card', { hasText: 'Leitura alta' }).locator('.btn-view').click();
    const hist = (await p.locator('#tomadasLista').innerText()).replace(/\s+/g, ' ');
    await p.click('#tomadasLista button:has-text("Marcar executada")');
    await esperarToast(p, /executada/); await p.click('.close-btn');
    assert(await sql("select status_execucao from tomada_decisao t join decisao d using (id_decisao) where d.nome_decisao='Leitura alta';") === 'executada');
    return hist;
  });
  await step('26 Decisões: regra com histórico não é excluída', async () => {
    await limparToasts(p);
    await p.locator('.decision-card', { hasText: 'Leitura alta' }).locator('.btn-view').click();
    await p.click('#modalActions .btn-cancel'); const t = await esperarToast(p, /não pode ser excluída/); await p.click('.close-btn'); return t;
  });
  await step('27 Leituras: excluir leitura (confirmação no design) mantém o histórico', async () => {
    await ir(p, '/pages/leituras.html');
    await p.locator('.decision-card', { hasText: '12,50 kWh' }).locator('.btn-view').click();
    await p.click('#modalActions .btn-cancel'); await p.waitForSelector('.kv-confirm');
    await foto(p, 'confirmacao-exclusao');
    await p.click('.kv-confirm .btn-delete'); const t = await esperarToast(p, /Leitura excluída/); await p.waitForTimeout(300);
    assert(await sql("select count(*) from tomada_decisao t join decisao d using (id_decisao) where d.nome_decisao='Leitura alta';") === '1');
    return t + ' | histórico preservado';
  });

  // ---------------- Painel e relatórios
  await step('28 Painel: indicadores, setores, máquinas, alertas e exportação CSV', async () => {
    await ir(p, '/pages/painel.html');
    await p.waitForSelector('#conteudoPainel:not([hidden])');
    const k = (await p.locator('#kpiPrincipal').innerText()).replace(/\s+/g, ' ');
    const setores = await p.locator('#listaSetores .decision-card').count(), maquinas = await p.locator('#listaMaquinas .decision-card').count();
    assert(/CUSTO ESTIMADO/i.test(k) && setores === 2 && maquinas === 2, `${k} | ${setores} | ${maquinas}`);
    const [download] = await Promise.all([p.waitForEvent('download'), p.click('#botaoExportar')]);
    const arquivo = path.join(OUT, download.suggestedFilename()); await download.saveAs(arquivo);
    const csv = fs.readFileSync(arquivo, 'utf8');
    assert(/Consumo por máquina/.test(csv) && /Overloque 01/.test(csv), 'csv');
    await foto(p, 'painel-escuro');
    await p.click('.tab:has-text("Mês anterior")'); await p.waitForTimeout(600);
    const anterior = (await p.locator('#kpiConsumo').innerText()).trim();
    return `${k} | CSV ${download.suggestedFilename()} | mês anterior: ${anterior} kWh`;
  });
  await step('29 Persistência: dados permanecem ao recarregar e em nova aba (sessão mantida)', async () => {
    const p2 = await pagina(ctxA, 'A-aba2'); await ir(p2, '/pages/setores.html');
    const n = await cards(p2).count(); await p2.close();
    assert(n === 2, 'setores ' + n); return `${n} setores na nova aba, sem novo login`;
  });

  // ---------------- Empresa B: isolamento
  const ctxB = await contexto(browser);
  const b = await pagina(ctxB, 'B');
  await step('30 Empresa B: cadastro independente', async () => {
    await ir(b, '/pages/entrar.html?cadastro=1');
    await b.fill('#cnpj', '11444777000161'); await b.fill('#nome', 'Malharia B'); await b.fill('#responsavel', 'Bruno');
    await b.fill('#email', 'bruno@malhariab.com.br'); await b.fill('#telefone', '4432221111'); await b.fill('#senha', 'Malha2026x');
    await b.click('#formCadastro button[type=submit]'); await b.waitForURL(/painel\.html/, { timeout: 8000 }); return b.url().replace(SITE, '');
  });
  await step('31 Empresa B não vê nada da Empresa A (todas as páginas)', async () => {
    const out = [];
    for (const pg of ['setores', 'maquinas', 'sensores', 'leituras', 'consumos', 'decisoes']) {
      await ir(b, `/pages/${pg}.html`); const n = await b.locator('.decision-card').count(); out.push(`${pg}=${n}`); assert(n === 0, pg + ' vazou');
    }
    await ir(b, '/pages/painel.html'); await b.waitForSelector('#conteudoPainel:not([hidden])');
    assert((await b.locator('#kpiConsumo').innerText()).trim() === '0,00');
    return out.join(' ');
  });
  await step('32 Empresa B: ataques diretos à API com o próprio token são bloqueados', async () => {
    const idMaqA = Number(await sql("select id_maquina from maquina where nome_maquina='Overloque 01';"));
    const idSetA = Number(await sql("select id_setor from setor where nome_setor='Corte' and id_empresa=(select id_empresa from empresa where email_empresa='ana@confeccoesqa.com.br');"));
    const r = await b.evaluate(async ([m, s]) => {
      const st = async (c, met, d) => (await fetch(API_URL + c, { method: met, headers: { 'Content-Type': 'application/json', Authorization: 'Bearer ' + KV.lerSessao().access_token }, body: d ? JSON.stringify(d) : undefined })).status;
      return { get: await st(`/maquinas/${m}`, 'GET'), put: await st(`/maquinas/${m}`, 'PUT', { nome_maquina: 'hack', descricao_maquina: 'x', id_setor: s }),
        post: await st('/maquinas', 'POST', { nome_maquina: 'x', descricao_maquina: 'x', id_setor: s }), del: await st(`/setores/${s}`, 'DELETE') };
    }, [idMaqA, idSetA]);
    assert(r.get === 404 && r.put === 404 && r.post === 403 && r.del === 404, JSON.stringify(r));
    assert(await sql(`select nome_maquina from maquina where id_maquina=${idMaqA};`) === 'Overloque 01');
    return JSON.stringify(r);
  });

  // ---------------- Equipe e perfis
  await step('33 Equipe: administrador cadastra uma Visualizadora pela página Empresa', async () => {
    await ir(p, '/pages/empresa.html');
    await p.click('#tabEquipe'); await p.waitForSelector('#userList .decision-card');
    await p.click('#botaoNovoUsuario'); await p.fill('#nomeUsuario', 'Vera Visual'); await p.fill('#emailUsuario', 'vera@confeccoesqa.com.br');
    await p.selectOption('#tipoUsuario', 'Visualizador'); await p.fill('#senhaUsuario', 'Visual2026x');
    await p.click('#modalActions .btn-confirm'); const t = await esperarToast(p, /Usuário cadastrado/); await p.waitForTimeout(300);
    assert(await p.locator('#userList .decision-card').count() === 2); await foto(p, 'empresa-equipe-escuro'); return t;
  });
  await step('34 Perfil Visualizador: consulta, mas não grava (bloqueio na API)', async () => {
    const ctxV = await contexto(browser, { viewport: { width: 1280, height: 860 } }); const v = await pagina(ctxV, 'V');
    await ir(v, '/pages/entrar.html?entrar=1'); await v.fill('#loginEmail', 'vera@confeccoesqa.com.br'); await v.fill('#loginSenha', 'Visual2026x');
    await v.click('#formLogin button[type=submit]'); await v.waitForURL(/painel/);
    await ir(v, '/pages/setores.html'); const n = await cards(v).count();
    await v.click('.btn-add'); const t1 = await esperarToast(v, /administradores/);
    const st = await v.evaluate(async () => (await fetch(API_URL + '/setores', { method: 'POST', headers: { 'Content-Type': 'application/json', Authorization: 'Bearer ' + KV.lerSessao().access_token }, body: JSON.stringify({ nome_setor: 'X', id_usuario_responsavel: 1 }) })).status);
    await ctxV.close();
    assert(n === 2 && st === 403, `${n} ${st}`); return `vê ${n} setores | botão: "${t1}" | API: ${st}`;
  });

  // ---------------- Sessão
  await step('35 Logout pela página Empresa e bloqueio das páginas internas', async () => {
    await ir(p, '/pages/empresa.html');
    await p.click('#tabSair'); await p.waitForSelector('.kv-confirm'); await p.click('.kv-confirm .btn-confirm');
    await p.waitForURL(/entrar\.html\?entrar=1/); await ir(p, '/pages/setores.html'); await p.waitForURL(/voltar=setores/);
    return p.url().replace(SITE, '');
  });
  await step('36 Senha incorreta → mensagem clara (401)', async () => {
    await p.waitForTimeout(300); await limparToasts(p);
    await p.fill('#loginEmail', A.email); await p.fill('#loginSenha', 'errada123'); await p.click('#formLogin button[type=submit]');
    const t = await esperarToast(p, /incorretos/); assert(!/setores\.html/.test(p.url())); return t;
  });
  await step('37 Login correto retorna à página protegida', async () => {
    await p.fill('#loginSenha', A.senha); await p.click('#formLogin button[type=submit]');
    await p.waitForURL(/setores\.html/); return p.url().replace(SITE, '');
  });
  await step('38 Token expirado é renovado automaticamente (POST /auth/refresh)', async () => {
    const expirado = (await (await fetch(SUPA + '/__teste/token_expirado?email=' + A.email)).json()).token;
    await p.evaluate(t => { const s = KV.lerSessao(); s.access_token = t; localStorage.setItem('klyvolt.sessao', JSON.stringify(s)); }, expirado);
    await ir(p, '/pages/maquinas.html'); await p.waitForSelector('.decision-card');
    const novo = await p.evaluate(() => KV.lerSessao().access_token);
    assert(novo !== expirado && /maquinas\.html/.test(p.url())); return 'sessão renovada sem novo login';
  });
  await step('39 Recuperação de senha completa (link do e-mail → nova senha → painel)', async () => {
    await p.evaluate(() => KV.sair()); await p.waitForURL(/entrar\.html/);
    await p.click('#linkRecuperar'); await p.fill('#recEmail', A.email); await p.click('#formRecuperar button[type=submit]');
    const t1 = await esperarToast(p, /receberá um link/);
    const link = await (await fetch(SUPA + '/__teste/link?email=' + A.email)).json();
    await p.goto(`${SITE}/pages/entrar.html#access_token=${link.access_token}&refresh_token=${link.refresh_token}&type=recovery`);
    await p.waitForSelector('#formNovaSenha:not([hidden])');
    await p.fill('#novaSenha', 'NovaSenha2026'); await p.fill('#novaSenha2', 'NovaSenha2026'); await p.click('#formNovaSenha button[type=submit]');
    await p.waitForURL(/painel\.html/); await esperarToast(p, /Senha alterada/);
    await p.evaluate(() => KV.sair()); await p.waitForURL(/entrar/);
    await p.fill('#loginEmail', A.email); await p.fill('#loginSenha', 'NovaSenha2026'); await p.click('#formLogin button[type=submit]');
    await p.waitForURL(/painel\.html/); A.senha = 'NovaSenha2026';
    return `${t1} | redirect: ${link.redirect_to}`;
  });
  await step('40 Confirmação de e-mail ativa no Supabase', async () => {
    await sup('/__teste/config', { confirmarEmail: true });
    const ctxC = await contexto(browser, { viewport: { width: 1280, height: 860 } }); const c = await pagina(ctxC, 'C');
    await ir(c, '/pages/entrar.html?cadastro=1');
    await c.fill('#cnpj', '45997418000153'); await c.fill('#nome', 'Bordados C'); await c.fill('#responsavel', 'Carla');
    await c.fill('#email', 'carla@bordadosc.com.br'); await c.fill('#telefone', '44988887777'); await c.fill('#senha', 'Borda2026x');
    await c.click('#formCadastro button[type=submit]'); const t1 = await esperarToast(c, /link de confirmação/);
    await limparToasts(c); await c.fill('#loginSenha', 'Borda2026x'); await c.click('#formLogin button[type=submit]');
    const t2 = await esperarToast(c, /Confirme seu e-mail/);
    await sup('/__teste/confirmar', { email: 'carla@bordadosc.com.br' });
    await c.fill('#loginSenha', 'Borda2026x'); await c.click('#formLogin button[type=submit]'); await c.waitForURL(/painel/);
    await ctxC.close(); await sup('/__teste/config', { confirmarEmail: false });
    return `${t1.slice(0, 60)}… | ${t2}`;
  });

  // ---------------- Falhas
  await step('41 Supabase fora do ar → API responde 503 → mensagem na página', async () => {
    await ir(p, '/pages/setores.html');
    await sup('/__teste/config', { offline: true });
    await limparToasts(p);
    await p.click('.btn-add'); await p.fill('#nomeSetor', 'Sem rede'); await p.click('#modalActions .btn-confirm');
    const t = await esperarToast(p, /Supabase/); const aberto = await p.locator('#modalOverlay').isVisible();
    await sup('/__teste/config', { offline: false }); await p.click('#modalActions .btn-cancel');
    assert(aberto); return t;
  });
  await step('42 API fora do ar → mensagem sobre backend/CORS (sem travar)', async () => {
    await p.route(API + '/**', r => r.abort('connectionrefused'));
    await ir(p, '/pages/maquinas.html');
    const t = await esperarToast(p, /Não foi possível acessar a API/);
    await p.unroute(API + '/**'); return t;
  });

  // ---------------- Responsivo e tema
  await step('43 Responsivo (390 px): nenhuma página com rolagem horizontal', async () => {
    const m = await contexto(browser, { viewport: { width: 390, height: 844 }, isMobile: true }); const mp = await pagina(m, 'mobile');
    await ir(mp, '/pages/entrar.html?entrar=1'); await mp.fill('#loginEmail', A.email); await mp.fill('#loginSenha', A.senha);
    await mp.click('#formLogin button[type=submit]'); await mp.waitForURL(/painel/); await mp.waitForTimeout(500);
    const out = [];
    for (const pg of ['painel', 'consumos', 'maquinas', 'sensores', 'leituras', 'setores', 'decisoes', 'empresa', 'registrar-consumo']) {
      await ir(mp, `/pages/${pg}.html`); await mp.waitForTimeout(300);
      const w = await mp.evaluate(() => document.documentElement.scrollWidth); out.push(`${pg}=${w}`); assert(w <= 390, pg + ' ' + w);
      if (['painel', 'maquinas'].includes(pg)) await foto(mp, `${pg}-celular-390`);
    }
    await ir(mp, '/index.html'); out.push('inicio=' + await mp.evaluate(() => document.documentElement.scrollWidth));
    await m.close(); return out.join(' ');
  });
  await step('44 Tema claro nas páginas integradas', async () => {
    await ir(p, '/pages/painel.html'); await p.waitForSelector('#conteudoPainel:not([hidden])');
    await p.click('.kv-theme-toggle'); await p.waitForTimeout(700);
    assert(await p.evaluate(() => document.documentElement.dataset.theme) === 'light');
    await foto(p, 'painel-claro');
    await ir(p, '/pages/maquinas.html'); await p.locator('.decision-card .btn-view').first().click(); await p.waitForTimeout(600); await foto(p, 'maquinas-modal-claro');
    await ir(p, '/pages/entrar.html?entrar=1&motivo=x'); await foto(p, 'entrar-claro');
    await p.click('.kv-theme-toggle'); return 'ok';
  });

  fs.writeFileSync(path.join(OUT, 'resultados.json'), JSON.stringify({ results, consoleErrors }, null, 1));
  console.log(`\n${results.filter(r => r.ok).length}/${results.length} passaram. Erros de console: ${consoleErrors.length}`);
  consoleErrors.slice(0, 20).forEach(e => console.log('  ', e));
  await browser.close();
})();
