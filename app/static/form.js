const token=location.pathname.split('/').pop(),notice=document.getElementById('notice'),form=document.getElementById('form');
let previousEvents=[];
let reusedData=false;
const reuseNames={
 org_name:'Ragione sociale / Ente',
 org_contact:'Nome e cognome referente',
 org_address:'Indirizzo sede legale',
 org_tax_code:'Codice fiscale',
 org_vat:'Partita IVA',
 org_sdi:'Codice univoco SDI',
 org_phone:'Telefono organizzatore',
 org_pec:'PEC',
 event_name:'Nome Evento / Società organizzatrice',
 event_city:'Città evento',
 event_place:'Luogo di svolgimento',
 event_description:'Descrizione evento',
 reference_name:'Referente sul posto',
 reference_phone:'Telefono referente',
 event_type:'Tipo evento',
 recurrence:'Frequenza',
 location_type:'Caratteristiche del luogo',
 road_closure:'Modifica della viabilità',
 participants_athletes:'Partecipanti attivi',
 participants_public:'Pubblico / spettatori / visitatori',
 children:'Bambini',
 elderly:'Anziani',
 disabled:'Persone con disabilità',
 risk_options:'Fattori di rischio',
 additional_notes:'Altre note'
};
const reuseFieldGroups=[
 {title:'Dati organizzatore',keys:['org_name','org_contact','org_address','org_tax_code','org_vat','org_sdi','org_phone','org_pec']},
 {title:'Dati evento',keys:['event_name','event_city','event_place','event_description','reference_name','reference_phone','event_type','recurrence','location_type','road_closure','participants_athletes','participants_public','children','elderly','disabled','risk_options','additional_notes']}
];
const historyChoices=[...document.querySelectorAll('input[name=historyMode]')];
function setHistoryMode(mode){
 const details=document.getElementById('previousEventsBox');
 details.classList.toggle('hidden',mode!=='copy');
 if(mode==='new'&&reusedData){
  document.getElementById('reuseStatus').textContent=
    'I dati che hai già importato rimangono nel modulo: puoi modificarli manualmente.';
 }
}
historyChoices.forEach(input=>input.addEventListener('change',()=>{
 if(input.checked)setHistoryMode(input.value);
}));
async function loadPreviousEvents(){
 try{
  const response=await fetch('/api/r/'+encodeURIComponent(token)+'/previous-events',{cache:'no-store'});
  if(!response.ok)return;
  const items=await response.json();
  if(!Array.isArray(items)||items.length===0)return;
  previousEvents=items;
  const choices=document.getElementById('previousEventChoices');
  choices.replaceChildren();
  for(const item of previousEvents){
    const label=document.createElement('label');
    label.className='check';
    const input=document.createElement('input');
    input.type='checkbox';input.className='previousChoice';input.value=String(item.id);
    const date=item.submitted_at
      ?new Date(item.submitted_at).toLocaleDateString('it-IT')
      :'data non disponibile';
    label.append(input,document.createTextNode(' '+item.name+' · '+date+' · richiesta #'+item.id));
    choices.append(label);
  }
  const fieldsBox=document.getElementById('reuseFields');
  fieldsBox.replaceChildren();
  for(const group of reuseFieldGroups){
    const section=document.createElement('section');
    section.className='reuse-field-group';
    const heading=document.createElement('h4');
    heading.textContent=group.title;
    section.appendChild(heading);
    const checkboxes=document.createElement('div');
    checkboxes.className='reuse-fields';
    for(const key of group.keys){
      const label=document.createElement('label');
      label.className='check';
      const input=document.createElement('input');
      input.type='checkbox';input.className='reuseField';input.value=key;
      // Keep the current invitation's new event name and city by default.
      // Previous email and legal acknowledgements are never eligible to copy.
      input.checked=key!=='event_name'&&key!=='event_city';
      label.append(input,document.createTextNode(' '+reuseNames[key]));
      checkboxes.appendChild(label);
    }
    section.appendChild(checkboxes);
    fieldsBox.appendChild(section);
  }
  document.getElementById('previousEventsSummary').textContent=
    'Sono presenti '+previousEvents.length+' richieste completate in precedenza per questa email.';
  document.getElementById('previousEventsChooser').classList.remove('hidden');
  setHistoryMode('new');
 }catch(error){
  // The form remains available for new data even if history cannot load.
 }
}
document.getElementById('reuseEvent').onclick=()=>{
 const ids=[...document.querySelectorAll('.previousChoice:checked')].map(x=>x.value);
 const selected=new Set([...document.querySelectorAll('.reuseField:checked')].map(x=>x.value));
 const status=document.getElementById('reuseStatus');
 if(!ids.length){status.textContent='Seleziona almeno un evento precedente.';return}
 if(!selected.size){status.textContent='Seleziona almeno un dato da copiare.';return}
 if(!confirm('Copiare i dati dell’organizzatore e dell’evento selezionati? Se gli eventi hanno valori diversi, prevale l’ultimo selezionato. L’email di invito, i consensi, le date e gli orari rimarranno invariati.'))return;
 let count=0;
 for(const id of ids){
  const source=previousEvents.find(x=>String(x.id)===id);
  if(!source)continue;
  for(const [key,value] of Object.entries(source.data||{})){
   if(!selected.has(key)||value===null||value===undefined||value==='')continue;
   if(key==='risk_options'){
    document.querySelectorAll('[name=risk_options]').forEach(box=>
      box.checked=Array.isArray(value)&&value.includes(box.value));
    count++;continue;
   }
   const target=form.elements[key];
   if(!target)continue;
   target.value=typeof value==='boolean'?String(value):value;
   count++;
  }
 }
 reusedData=count>0;
 status.textContent=count
   ?'Dati copiati nel modulo: verifica ragione sociale, contatti, codice fiscale, partita IVA e tutti i dati dell’evento. L’email dell’invito è rimasta invariata. Inserisci nuove date e orari.'
   :'Nessun valore disponibile per i campi scelti. Seleziona altri dati.';
};
const slotContainer=document.getElementById('eventSlots');
function addSlot(date='',start='',end=''){
 const row=document.createElement('div');row.style.cssText='display:flex;flex-wrap:wrap;gap:8px;align-items:end;margin:8px 0;padding:10px;border:1px solid #ddd;border-radius:8px';
 for(const [label,type,value,cls] of [['Data','date',date,'slotDate'],['Dalle','time',start,'slotStart'],['Alle','time',end,'slotEnd']]){
   const holder=document.createElement('label');holder.style.cssText='display:flex;flex-direction:column;gap:4px';holder.textContent=label;
   const input=document.createElement('input');input.type=type;input.value=value;input.required=true;input.className=cls;holder.appendChild(input);row.appendChild(holder);
 }
 const remove=document.createElement('button');remove.type='button';remove.className='secondary';remove.textContent='Rimuovi';remove.onclick=()=>{if(slotContainer.children.length>1)row.remove()};row.appendChild(remove);slotContainer.appendChild(row);
}
document.getElementById('addEventSlot').onclick=()=>addSlot();
addSlot();
function readSlots(){
 const rows=[...slotContainer.children].map(r=>({date:r.querySelector('.slotDate').value,start:r.querySelector('.slotStart').value,end:r.querySelector('.slotEnd').value}));
 if(!rows.length||rows.some(x=>!x.date||!x.start||!x.end||x.end<=x.start))throw Error('Inserisci date e fasce orarie valide: la fine deve essere successiva all’inizio.');
 return rows.sort((a,b)=>(a.date+a.start).localeCompare(b.date+b.start));
}
function fiscalCheck(s){
 s=s.trim().toUpperCase();if(!s)return true;
 if(/^\d{11}$/.test(s))return vatCheck(s);
 if(!/^[A-Z0-9]{16}$/.test(s))return false;
 const even='ABCDEFGHIJKLMNOPQRSTUVWXYZ',odd='BAKPLCQDREVOSFTGUHMINJWZYX';
 const oddDigit=[1,0,5,7,9,13,15,17,19,21];
 let sum=0;
 for(let i=0;i<15;i++){
  const c=s[i];
  if(i%2===0)sum+=/\d/.test(c)?oddDigit[Number(c)]:odd.indexOf(c);
  else sum+=/\d/.test(c)?Number(c):even.indexOf(c);
 }
 return even[sum%26]===s[15];
}
function vatCheck(s){s=s.trim().replace(/^IT/i,'');if(!s)return true;if(!/^\d{11}$/.test(s))return false;let sum=0;for(let i=0;i<10;i++){let n=Number(s[i]);if(i%2)n=n*2>9?n*2-9:n*2;sum+=n}return (10-sum%10)%10===Number(s[10])}
function validateTax(){
 const cf=form.elements.org_tax_code,vat=form.elements.org_vat;
 cf.value=cf.value.trim().toUpperCase();vat.value=vat.value.trim().toUpperCase();
 cf.setCustomValidity(fiscalCheck(cf.value)?'':'Codice fiscale non valido');
 vat.setCustomValidity(vatCheck(vat.value)?'':'Partita IVA non valida');
 document.getElementById('cfMessage').textContent=cf.validationMessage;
 document.getElementById('vatMessage').textContent=vat.validationMessage;
 return cf.checkValidity()&&vat.checkValidity();
}
form.elements.org_tax_code.addEventListener('blur',validateTax);
form.elements.org_vat.addEventListener('blur',validateTax);
for(const name of ['org_tax_code','org_vat']){
 form.elements[name].addEventListener('input',()=>{
  form.elements[name].setCustomValidity('');
  document.getElementById(name==='org_tax_code'?'cfMessage':'vatMessage').textContent='';
 });
}
// Suggestions are served by our backend so cross-origin browser failures never
// break the form. User selection is optional and keyboard accessible.
function enableAddressAutocomplete(input, list, status){
  let controller=null,timer=null,options=[],active=-1,serial=0;
  const report=message=>{status.textContent=message};
  const show=items=>{
    list.replaceChildren();options=items;active=-1;
    for(let i=0;i<items.length;i++){
      const btn=document.createElement('button');
      btn.type='button';btn.className='address-option';btn.setAttribute('role','option');
      btn.setAttribute('aria-selected','false');btn.textContent=items[i];
      btn.addEventListener('mousedown',e=>e.preventDefault());
      btn.addEventListener('click',()=>select(i));list.appendChild(btn);
    }
    list.classList.toggle('hidden',!items.length);
    input.setAttribute('aria-expanded',String(!!items.length));
  };
  const close=()=>show([]);
  const highlight=idx=>{
    if(!options.length)return;
    active=(idx+options.length)%options.length;
    [...list.children].forEach((button,i)=>{
      button.classList.toggle('active',i===active);
      button.setAttribute('aria-selected',String(i===active));
    });
  };
  const select=idx=>{
    input.value=options[idx];close();report('Indirizzo selezionato. Puoi modificarlo se necessario.');
    input.focus();input.dispatchEvent(new Event('change',{bubbles:true}));
  };
  input.addEventListener('input',()=>{
    clearTimeout(timer);if(controller)controller.abort();serial++;close();
    const q=input.value.trim();
    if(q.length<3){report('');return}
    report('Ricerca indirizzi in corso…');
    const thisSearch=serial;
    timer=setTimeout(async()=>{
      controller=new AbortController();
      try{
        const response=await fetch('/api/r/'+encodeURIComponent(token)+
          '/address-suggestions?q='+encodeURIComponent(q),{
          signal:controller.signal,cache:'no-store'});
        if(thisSearch!==serial||input.value.trim()!==q)return;
        if(response.status===429){
          report('Troppe ricerche ravvicinate. Attendi un minuto oppure inserisci l’indirizzo manualmente.');
          return;
        }
        if(!response.ok)throw Error('Servizio non disponibile');
        const data=await response.json();
        if(thisSearch!==serial||input.value.trim()!==q)return;
        if(data.available===false){
          report('Il servizio indirizzi non è momentaneamente disponibile. Puoi inserire l’indirizzo manualmente.');
          return;
        }
        const suggestions=Array.isArray(data.suggestions)?data.suggestions:[];
        show(suggestions);
        report(suggestions.length
          ?suggestions.length+' suggerimenti trovati. Selezionane uno o continua a scrivere.'
          :'Nessun indirizzo trovato. Prova ad aggiungere la città oppure inserisci l’indirizzo manualmente.');
      }catch(error){
        if(thisSearch===serial&&error.name!=='AbortError'){
          close();report('Impossibile caricare i suggerimenti. Puoi comunque compilare l’indirizzo manualmente.');
        }
      }
    },500);
  });
  input.addEventListener('keydown',e=>{
    if(!options.length)return;
    if(e.key==='ArrowDown'){e.preventDefault();highlight(active+1)}
    else if(e.key==='ArrowUp'){e.preventDefault();highlight(active-1)}
    else if(e.key==='Enter'&&active>=0){e.preventDefault();select(active)}
    else if(e.key==='Escape'){close();report('')}
  });
  input.addEventListener('blur',()=>setTimeout(close,150));
}
enableAddressAutocomplete(form.elements.org_address,
  document.getElementById('orgAddressSuggestions'),
  document.getElementById('orgAddressStatus'));
enableAddressAutocomplete(form.elements.event_place,
  document.getElementById('placeSuggestions'),
  document.getElementById('placeStatus'));
const fields=['org_name','org_contact','org_address','org_tax_code','org_vat','org_sdi','org_phone','org_email','org_pec' ,'event_name','event_city','event_place','event_description','reference_name','reference_phone','event_type','recurrence','location_type','road_closure','participants_athletes','participants_public','children','elderly','disabled','additional_notes'];const risks=['Prevista vendita/consumo di alcool','Possibile consumo di droghe','Presenza categorie fragili','Evento ampiamente pubblicizzato','Presenza figure politiche/religiose','Possibili difficoltà nella viabilità','Tensioni socio-politiche','Ambiente acquatico','Palco o ponteggio temporaneo','Presenza di recinzioni','Servizi igienici','Disponibilità acqua','Protezione civile','Vigili del fuoco','Forze dell’ordine'];document.getElementById('risks').innerHTML=risks.map((r,i)=>'<label class="check"><input type="checkbox" name="risk_options" value="'+r+'">'+r+'</label>').join('');function message(m,bad=false){notice.className='notice '+(bad?'err':'good');notice.textContent=m;window.scrollTo({top:0,behavior:'smooth'})}async function init(){try{const r=await fetch('/api/r/'+token);if(!r.ok)throw Error('Link non valido, scaduto o già chiuso');const x=await r.json();if(x.status==='submitted'||x.status==='approved'){form.classList.add('hidden');message('Questa richiesta è già stata inviata e non può essere riutilizzata.');return}form.elements.org_email.value=x.customer_email||'';form.elements.event_name.value=x.event_name||'';form.elements.event_city.value=x.event_city||'';loadPreviousEvents();if(x.status==='draft'){if(Array.isArray(x.data.event_slots)&&x.data.event_slots.length){slotContainer.replaceChildren();x.data.event_slots.forEach(x=>addSlot(x.date,x.start,x.end))}for(const [k,v]of Object.entries(x.data)){if(k==='risk_options'){document.querySelectorAll('[name=risk_options]').forEach(c=>c.checked=v.includes(c.value))}else if(form.elements[k]){if(form.elements[k].type==='checkbox')form.elements[k].checked=!!v;else form.elements[k].value=v}}}}catch(err){form.classList.add('hidden');message(err.message,true)}}form.onsubmit=async e=>{e.preventDefault();
 const submit=e.submitter||form.querySelector('[type=submit]');
 if(submit?.disabled)return;
if(!confirm('Confermi invio definitivo? Dopo l’invio non potrai modificare la richiesta con questo link.'))return;if(!validateTax()){form.reportValidity();return}let slots;try{slots=readSlots()}catch(err){message(err.message,true);return}const values={event_slots:slots,event_dates:slots.map(x=>x.date).join(', '),event_time:slots.map(x=>x.date+' '+x.start+'–'+x.end).join('; ')};for(const k of fields){let el=form.elements[k];values[k]=el.value}for(const k of ['participants_athletes','participants_public','children','elderly','disabled'])values[k]=Number(values[k]||0);values.road_closure=values.road_closure==='true';values.risk_options=[...form.querySelectorAll('[name=risk_options]:checked')].map(x=>x.value);values.privacy_ack=form.elements.privacy_ack.checked;values.declaration=form.elements.declaration.checked;if(submit){submit.disabled=true;submit.textContent='Invio in corso…'}
try{const r=await fetch('/api/r/'+encodeURIComponent(token),{method:'PUT',headers:{'Content-Type':'application/json'},body:JSON.stringify(values)});if(!r.ok){
 const j=await r.json().catch(()=>({}));
 const details=Array.isArray(j.detail)?j.detail.map(x=>((x.loc||[]).slice(-1)[0]||'Campo')+': '+x.msg).join('; '):j.detail;
 throw Error(typeof details==='string'&&details?details:'Invio non riuscito: controlla i dati e riprova.');
}
const result=await r.json();
if(result.status!=='submitted')throw Error('Il server non ha confermato l’invio: contatta CRI Venezia.');
form.classList.add('hidden');
const protocol=result.protocol_number||'';
const when=result.protocol_at?new Intl.DateTimeFormat('it-IT',{dateStyle:'long',timeStyle:'short'}).format(new Date(result.protocol_at)):'';
const emailWarning=result.mail_status==='sent'?' La bozza del Piano Sanitario è stata inviata agli operatori CRI.':' Attenzione: la notifica email non risulta inviata ('+(result.mail_status||'da verificare')+'). La richiesta è comunque registrata.';
message('Richiesta registrata correttamente. Protocollo interno: '+protocol+'. Data: '+when+'.'+emailWarning+' Non devi compilare nuovamente il modulo.');}catch(err){message('Invio non completato: '+err.message+'. I dati rimangono nel modulo: non ricaricare la pagina.',true)}
finally{if(submit){submit.disabled=false;submit.textContent='Invia definitivamente la richiesta'}}};const readySubmit=document.getElementById('sendRequest');readySubmit.disabled=false;readySubmit.textContent='Invia definitivamente la richiesta';if(location.hash==='#invio-non-registrato')message('L’invio precedente non è stato registrato: il vecchio modulo ha trasmesso i dati nell’indirizzo anziché salvarli. Usa questo modulo aggiornato per compilare e inviare la richiesta.',true);init();
