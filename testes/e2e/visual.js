// Regressão visual: compara capturas da versão integrada (5500) com o design aprovado original (KV_ORIGINAL, padrão 5600).
// Compara a página inicial inteira e o topo (menu + título + barra de busca) das páginas internas, em 1440 px e 390 px, tema escuro e claro.
// Os cards de dados não entram na comparação: no original eram exemplos fixos; agora vêm do banco.
const { chromium } = require(process.env.PLAYWRIGHT_PATH || 'playwright');
const fs = require('fs'), path = require('path'), { execFileSync } = require('child_process');
const OUT = process.env.KV_OUT || path.join(__dirname, '..', 'capturas', 'visual'); fs.mkdirSync(OUT, { recursive: true });
const FA = process.env.FA_PATH || path.join(__dirname, 'node_modules/@fortawesome/fontawesome-free');
const NOVO = 'http://127.0.0.1:5500', ORIG = process.env.KV_ORIGINAL || 'http://127.0.0.1:5600';
const EMAIL = process.env.KV_EMAIL || 'ana@confeccoesqa.com.br', SENHA = process.env.KV_SENHA || 'NovaSenha2026';
const paginas = [['inicio', '/index.html', '/index.html', null],
  ...['consumos', 'sensores', 'leituras', 'setores', 'decisoes'].map(p => [p, `/pages/${p}/index.html`, `/pages/${p}.html`, 300])];

async function contexto(browser, largura, tema) {
  const ctx = await browser.newContext({ viewport: { width: largura, height: 900 }, colorScheme: tema, locale: 'pt-BR', reducedMotion: 'reduce' });
  await ctx.route(/cdnjs\.cloudflare\.com|fonts\.googleapis\.com|fonts\.gstatic\.com/, r => {
    const u = new URL(r.request().url());
    if (u.pathname.endsWith('all.min.css')) return r.fulfill({ path: FA + '/css/all.min.css', contentType: 'text/css' });
    if (u.pathname.includes('/webfonts/')) return r.fulfill({ path: FA + '/webfonts/' + path.basename(u.pathname), contentType: 'font/woff2' });
    return r.fulfill({ body: '', contentType: 'text/css' });
  });
  await ctx.addInitScript(t => { try { localStorage.setItem('klyvolt.theme', t); } catch (e) {} }, tema);
  return ctx;
}
async function captura(p, url, altura, arquivo) {
  await p.goto(url); await p.waitForLoadState('networkidle'); await p.waitForTimeout(900);
  await p.evaluate(() => document.querySelectorAll('.reveal').forEach(e => e.classList.add('visible', 'is-visible', 'in')));
  await p.waitForTimeout(300);
  await p.screenshot({ path: arquivo, fullPage: !altura, clip: altura ? { x: 0, y: 0, width: p.viewportSize().width, height: altura } : undefined });
}

(async () => {
  const browser = await chromium.launch(), linhas = [];
  for (const largura of [1440, 390]) for (const tema of ['dark', 'light']) {
    const cn = await contexto(browser, largura, tema), co = await contexto(browser, largura, tema);
    const pn = await cn.newPage(), po = await co.newPage();
    await pn.goto(NOVO + '/pages/entrar.html?entrar=1'); await pn.fill('#loginEmail', EMAIL); await pn.fill('#loginSenha', SENHA);
    await pn.click('#formLogin button[type=submit]'); await pn.waitForURL(/painel/);
    for (const [nome, uo, un, alt] of paginas) {
      const base = path.join(OUT, `${nome}-${largura}-${tema}`);
      await captura(po, ORIG + uo, alt, base + '-original.png');
      await captura(pn, NOVO + un, alt, base + '-integrado.png');
      const r = execFileSync('python3', [path.join(__dirname, 'diff.py'), base + '-original.png', base + '-integrado.png', base + '-diff.png']).toString().trim();
      linhas.push(`${nome.padEnd(10)} ${String(largura).padStart(4)} ${tema.padEnd(5)} ${r}`); console.log(linhas.at(-1));
    }
    await cn.close(); await co.close();
  }
  fs.writeFileSync(path.join(OUT, 'resultado.txt'), linhas.join('\n') + '\n');
  await browser.close();
})();
