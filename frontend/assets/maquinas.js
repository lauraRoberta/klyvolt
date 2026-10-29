/* KLYVOLT máquinas: lista, cadastro e edição pela API (window.KV, em api.js).
   Máquina não tem DELETE no backend (apagaria sensores, consumos e leituras em cascata). */
(() => {
 'use strict';
 const root=document.getElementById('machineList');
 const modal=document.getElementById('machineModal');
 const dialog=modal?.querySelector('.modal-content');
 const form=document.getElementById('machineForm');
 const search=document.getElementById('machineSearch');
 if(!root||!modal||!form)return;
 if(!window.KV){console.error('api.js não foi carregado antes de maquinas.js');return;}
 const emptyEl=root.querySelector('.kv-empty-state');
 let machines=[], sectors=[], editing=null, opener=null, loaded=false, loadError='';
 function txt(tag,klass,value){const e=document.createElement(tag);if(klass)e.className=klass;if(value!=null)e.textContent=String(value);return e;}
 async function load(){
   loadError='';
   try{[machines,sectors]=await Promise.all([KV.list('maquina'),KV.list('setor')]);}
   catch(e){loadError=KV.message(e);}
   loaded=true;render();
   document.dispatchEvent(new CustomEvent('kv:machines-changed'));
 }
 function populateSectors(selected=''){
   const select=document.getElementById('machineSector');select.replaceChildren(new Option('Não vinculado',''));
   for(const s of sectors)select.add(new Option(s.nome,String(s.id)));
   select.value=selected==null?'':String(selected);
 }
 function open(mode='create',record=null){
   opener=document.activeElement;editing=mode==='edit'&&record?Number(record.id):null;
   form.reset();populateSectors(record?.idSetor??'');
   const val=(field,value)=>{form.elements[field].value=value??'';};
   if(record){for(const field of ['nome','codigo','potencia','localizacao'])val(field,record[field]);}
   document.getElementById('machineModalTitle').textContent=editing==null?'Adicionar máquina':'Editar máquina';
   modal.classList.add('kv-open');document.body.classList.add('kv-modal-open');
   requestAnimationFrame(()=>form.elements.nome.focus({preventScroll:true}));
 }
 function close(){modal.classList.remove('kv-open');document.body.classList.remove('kv-modal-open');opener?.focus?.({preventScroll:true});}
 function makeRow(box,ico,label){const p=txt('p','');const i=txt('i','fa-solid '+ico);p.append(i,document.createTextNode(' '+label));box.append(p);}
 function render(){
   const q=(search.value||'').toLocaleLowerCase('pt-BR').trim();
   root.querySelectorAll('.decision-card').forEach(e=>e.remove());
   let shown=0;
   for(const m of machines){
     if(q && ![m.nome,m.codigo,m.localizacao].join(' ').toLocaleLowerCase('pt-BR').includes(q))continue;
     shown++;
     const card=txt('div','decision-card');
     const head=txt('div','card-header');head.append(txt('span','id-badge','#'+String(m.id).padStart(2,'0')),txt('span','status-badge status-executada','Cadastrada'));
     card.append(head);const body=txt('div','card-body');
     body.append(txt('p','rule-name',m.nome));
     makeRow(body,'fa-hashtag','Código: '+m.codigo);
     if(m.potencia!==''&&m.potencia!=null)makeRow(body,'fa-bolt','Potência nominal: '+Number(m.potencia).toLocaleString('pt-BR')+' W');
     const sector=sectors.find(s=>String(s.id)===String(m.idSetor));
     if(sector)makeRow(body,'fa-layer-group','Setor: '+sector.nome);
     if(m.localizacao)makeRow(body,'fa-location-dot','Localização: '+m.localizacao);
     card.append(body);
     const actions=txt('div','card-actions');
     const edit=txt('button','btn-action btn-view','Editar');edit.type='button';edit.addEventListener('click',()=>open('edit',m));
     actions.append(edit);card.append(actions);root.append(card);
   }
   if(emptyEl){
     emptyEl.hidden=shown>0;
     emptyEl.textContent=!loaded?'Carregando máquinas...':loadError?('Não foi possível carregar as máquinas. '+loadError):machines.length?'Nenhuma máquina corresponde à pesquisa.':'Nenhuma máquina cadastrada.';
   }
 }
 form.addEventListener('submit',async e=>{
   e.preventDefault();
   const values={};for(const field of ['nome','codigo','potencia','idSetor','localizacao'])values[field]=form.elements[field].value.trim();
   if(!values.nome||!values.codigo){form.reportValidity();return;}
   if(values.potencia!==''&&(!Number.isFinite(Number(values.potencia))||Number(values.potencia)<0)){alert('Informe uma potência válida.');return;}
   if(machines.some(r=>String(r.codigo).toLowerCase()===values.codigo.toLowerCase()&&Number(r.id)!==editing)){alert('Esse código já pertence a uma máquina cadastrada.');form.elements.codigo.focus();return;}
   const submit=form.querySelector('[type="submit"]');if(submit)submit.disabled=true;
   try{
     if(editing==null)await KV.create('maquina',values);else await KV.update('maquina',editing,values);
     close();await load();
   }catch(err){alert(KV.message(err));}
   finally{if(submit)submit.disabled=false;}
 });
 document.getElementById('kvMachineAdd')?.addEventListener('click',()=>open());
 document.querySelectorAll('a.kv-add-machine').forEach(link=>link.addEventListener('click',e=>{e.preventDefault();open();}));
 document.getElementById('closeMachineModal')?.addEventListener('click',close);
 document.getElementById('cancelMachineModal')?.addEventListener('click',close);
 modal.addEventListener('pointerdown',e=>{if(e.target===modal)close();});
 document.addEventListener('keydown',e=>{
   if(!modal.classList.contains('kv-open'))return;
   if(e.key==='Escape'){e.preventDefault();close();}
   if(e.key==='Tab'){
     const fields=[...dialog.querySelectorAll('button:not([disabled]),input:not([disabled]),select:not([disabled])')].filter(el=>el.getClientRects().length);
     if(e.shiftKey&&document.activeElement===fields[0]){e.preventDefault();fields.at(-1).focus();}
     else if(!e.shiftKey&&document.activeElement===fields.at(-1)){e.preventDefault();fields[0].focus();}
   }
 });
 search.addEventListener('input',render);
 render();
 load().then(()=>{if(new URLSearchParams(location.search).has('adicionar'))open();});
})();
