/* Tela "Novo registro": cadastra o consumo de uma máquina pela API (POST /consumo). */
(() => {
 'use strict';
 const form=document.querySelector('main.card-container form.form-content');
 if(!form)return;
 if(!window.KV){console.error('api.js não foi carregado antes de registrar-consumo.js');return;}
 const buttons=[...form.querySelectorAll('.button-group button')];
 const get=id=>document.getElementById(id)?.value.trim()||'';
 buttons[0]?.addEventListener('click',async()=>{
   const start=get('data_inicio'),end=get('data_fim'),v=get('consumo').replace(',','.');
   const kwh=Number(v),idMaquina=get('maquina');
   if(!start||!end||v===''||!Number.isFinite(kwh)||kwh<0||!idMaquina){alert('Preencha datas, consumo válido e selecione uma máquina cadastrada.');return;}
   // O formulário só tem datas; o backend recebe o dia inteiro.
   const inicio=start+'T00:00',fim=end+'T23:59';
   if(new Date(fim)<new Date(inicio)){alert('A data final deve ser igual ou posterior à data inicial.');return;}
   buttons[0].disabled=true;
   try{
     await KV.create('consumo',{inicio,fim,kwh,idMaquina});
     window.location.assign('../consumos/index.html');
   }catch(e){alert(KV.message(e));buttons[0].disabled=false;}
 });
 buttons[1]?.addEventListener('click',()=>{alert('Para editar um consumo existente, abra a aba Consumos e escolha Detalhes > Editar.');});
 buttons[2]?.addEventListener('click',()=>{window.location.href='../consumos/index.html';});
})();
