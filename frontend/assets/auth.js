/* KLYVOLT - UI access flow. Not a production authentication service.
   Development bypass is limited to localhost and file://; password is never stored. */
(() => {
  'use strict';
  const isDev = location.protocol === 'file:' || ['localhost','127.0.0.1','[::1]'].includes(location.hostname);
  const accessKey = 'klyvolt.dev-access.v1';
  const getAccess = () => { try { return sessionStorage.getItem(accessKey) === 'enabled'; } catch (_) { return false; } };
  const setAccess = value => { try { if (value) sessionStorage.setItem(accessKey,'enabled'); else sessionStorage.removeItem(accessKey); return true; } catch (_) { return false; } };
  const backToPublic = () => { window.location.href = document.body.classList.contains('kv-internal-home') ? 'index.html' : '../../index.html'; };
  document.querySelectorAll('.kv-logout').forEach(btn => btn.addEventListener('click', () => { setAccess(false); backToPublic(); }));
  const backdrop = document.getElementById('kvAuthBackdrop');
  if (!backdrop) return;
  if (isDev && getAccess()) { window.location.replace('painel.html'); return; }
  const dialog = backdrop.querySelector('.kv-auth-dialog');
  const title = document.getElementById('kvAuthTitle');
  const tabs = [...backdrop.querySelectorAll('[data-auth-tab]')];
  const panels = [...backdrop.querySelectorAll('[data-auth-panel]')];
  const isOpen = () => backdrop.classList.contains('is-open');
  let previousFocus = null;
  const status = document.getElementById('kvAuthStatus');
  const registrationStatus = document.getElementById('kvRegisterStatus');

  function setTab(tab, focusInput = true) {
    for (const el of tabs) { const active=el.dataset.authTab===tab; el.classList.toggle('is-active',active); el.setAttribute('aria-selected',String(active)); el.tabIndex=active?0:-1; }
    for (const el of panels) { const active=el.dataset.authPanel===tab; el.classList.toggle('is-active',active); el.inert=!active; el.setAttribute('aria-hidden',String(!active)); }
    title.textContent = tab === 'login' ? 'Entrar na plataforma' : 'Criar conta empresarial';
    status.textContent=''; registrationStatus.textContent='';
    if (focusInput) requestAnimationFrame(() => backdrop.querySelector('[data-auth-panel="'+tab+'"] input')?.focus({preventScroll:true}));
  }
  const open = (tab='login') => {
    if (isOpen()) { setTab(tab); return; }
    previousFocus=document.activeElement;
    backdrop.classList.add('is-open');backdrop.setAttribute('aria-hidden','false');
    document.body.classList.add('kv-modal-open');setTab(tab);
  };
  const close = () => {
    if (!isOpen()) return;
    backdrop.classList.remove('is-open');backdrop.setAttribute('aria-hidden','true');document.body.classList.remove('kv-modal-open');
    previousFocus?.focus?.({preventScroll:true});
  };
  document.querySelectorAll('.kv-login-trigger').forEach(el => el.addEventListener('click', () => open('login')));
  document.querySelectorAll('.kv-auth-link').forEach(el => el.addEventListener('click',e => {e.preventDefault();open('login');}));
  backdrop.querySelector('.kv-auth-close')?.addEventListener('click',close);
  backdrop.addEventListener('pointerdown',e => { if (e.target===backdrop)close(); });
  tabs.forEach(t => t.addEventListener('click',() => setTab(t.dataset.authTab)));
  backdrop.querySelectorAll('[data-auth-go]').forEach(el => el.addEventListener('click',() => setTab(el.dataset.authGo)));
  document.addEventListener('keydown',e => {
    if (!isOpen())return;
    if(e.key==='Escape'){e.preventDefault();close();}
    if(e.key==='Tab'){
      const focusable=[...dialog.querySelectorAll('button:not([disabled]),input:not([disabled]),a[href]')].filter(el=>el.getClientRects().length && !el.closest('[inert]'));
      if(!focusable.length)return;
      const first=focusable[0],last=focusable.at(-1);
      if(e.shiftKey&&document.activeElement===first){e.preventDefault();last.focus();}
      else if(!e.shiftKey&&document.activeElement===last){e.preventDefault();first.focus();}
    }
  });
  function enterDevelopment(statusNode) {
    if (!isDev) { statusNode.textContent='A autenticação real ainda não está configurada neste pacote. A entrada de teste funciona somente em localhost ou abrindo os arquivos localmente.'; return; }
    if (!setAccess(true)) { statusNode.textContent='O navegador bloqueou o armazenamento da sessão. Ative-o para acessar o ambiente local.';return; }
    window.location.assign('painel.html');
  }
  document.getElementById('kvLoginForm')?.addEventListener('submit',e=>{e.preventDefault();enterDevelopment(status);});
  document.getElementById('kvRegistrationForm')?.addEventListener('submit',e=>{
    e.preventDefault();
    // No real backend was supplied. Keep profile for development; never store password.
    if(!isDev){registrationStatus.textContent='O cadastro empresarial real depende da integração segura com o Supabase. Este formulário não cria contas em produção.';return;}
    const form=e.currentTarget;
    const profile={cnpj:form.elements.cnpj.value.trim(),nome:form.elements.nome.value.trim(),email:form.elements.email.value.trim(),telefone:form.elements.telefone.value.trim()};
    if(!profile.nome || !profile.email || !form.elements.senha.value.trim()){
      registrationStatus.textContent='Informe nome da empresa, e-mail e senha para testar o cadastro.';return;
    }
    if(!form.elements.email.checkValidity()){registrationStatus.textContent='Informe um e-mail válido.';return;}
    try{localStorage.setItem('klyvolt.company.profile.v1',JSON.stringify(profile));}
    catch(_){registrationStatus.textContent='Não foi possível guardar os dados da empresa neste navegador.';return;}
    form.elements.senha.value='';enterDevelopment(registrationStatus);
  });
  // During local tests allow an existing open dev session to enter directly via the CTA;
  // the public page still displays as a landing page when visited intentionally.
})();
