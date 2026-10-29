/* Company details in this frontend remain local-only, not a Supabase account. */
(() => {
  'use strict';
  const form=document.querySelector('main.card-container form.form-content');
  if(!form)return;
  const key='klyvolt.company.profile.v1';
  try{
    const saved=JSON.parse(localStorage.getItem(key)||'null');
    if(saved && typeof saved==='object') for(const name of ['cnpj','nome','email','telefone']){
      const input=form.querySelector('#'+name);if(input&&typeof saved[name]==='string')input.value=saved[name];
    }
  }catch(_){}
  form.querySelector('#senha')?.setAttribute('autocomplete','new-password');
  form.addEventListener('submit',e=>{
    e.preventDefault();
    const profile={};for(const id of ['cnpj','nome','email','telefone'])profile[id]=form.querySelector('#'+id)?.value.trim()||'';
    if(!profile.nome || !profile.email){alert('Informe o nome e o e-mail da empresa.');return;}
    try{localStorage.setItem(key,JSON.stringify(profile));form.querySelector('#senha').value='';alert('Dados da empresa atualizados neste navegador. A integração com o Supabase ainda não está configurada.');}
    catch(_){alert('Não foi possível salvar os dados neste navegador.');}
  });
})();
