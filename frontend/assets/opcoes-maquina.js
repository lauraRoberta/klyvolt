/* Preenche os selects de máquina com as máquinas cadastradas na API. */
(() => {
 'use strict';
 if(!window.KV){console.error('api.js não foi carregado antes de opcoes-maquina.js');return;}
 async function fill(){
   let machines;
   try{machines=await KV.list('maquina');}catch(e){console.error(KV.message(e));return;}
   for (const selector of ['#maquina','#kvSensorMachine']){
     const select=document.querySelector(selector);if(!select)continue;
     const selected=select.value;
     select.querySelectorAll('option:not([value=""])').forEach(o=>o.remove());
     for(const m of machines){if(!m||!m.nome||m.id==null)continue;select.add(new Option(m.nome,String(m.id)));}
     select.value=selected;
   }
 }
 fill();
 document.addEventListener('kv:machines-changed',fill);
})();
