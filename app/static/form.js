const token=location.pathname.split('/').pop(),notice=document.getElementById('notice'),form=document.getElementById('form');
let previousEvents=[];
let reusedData=false;
const reuseNames={
 org_name:'Ragione sociale / Ente',
 org_contact:'Nome e cognome referente',
 org_first_name:'Nome referente',
 org_last_name:'Cognome referente',
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
 event_pause:'Pause evento',
 road_documents:'Documentazione viabilità',
 venue_context:'Ambiente e territorio',
 venue_features:'Caratteristiche luogo',
 venue_logistics:'Logistica',
 crowd_age_profile:'Età prevalente',
 crowd_density:'Densità del pubblico',
 crowd_mood:'Condizione del pubblico',
 crowd_position:'Posizione pubblico',
 involved_entities:'Altri enti coinvolti',
 involved_entities_other:'Altro ente',
 additional_notes:'Altre note'
};
const reuseFieldGroups=[
 {title:'Dati organizzatore',keys:['org_name','org_contact','org_first_name','org_last_name','org_address','org_tax_code','org_vat','org_sdi','org_phone','org_pec']},
 {title:'Dati evento',keys:['event_name','event_city','event_place','event_description','reference_name','reference_phone','event_type','recurrence','location_type','road_closure','participants_athletes','participants_public','children','elderly','disabled','risk_options','event_pause','road_documents','venue_context','venue_features','venue_logistics','crowd_age_profile','crowd_density','crowd_mood','crowd_position','involved_entities','involved_entities_other','additional_notes']}
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
function renderPreviousEvents(){
  const filter=document.getElementById('previousYearFilter').value;
  const choices=document.getElementById('previousEventChoices');
  const current=document.querySelector('input[name="previousEventChoice"]:checked');
  const selectedId=current?current.value:null;
  const matching=previousEvents.filter(item=>filter==='all'||
    (Array.isArray(item.years)&&item.years.some(year=>String(year)===filter)));
  choices.replaceChildren();
  for(const item of matching){
    const label=document.createElement('label');
    label.className='previous-event-card';
    const input=document.createElement('input');
    input.type='radio';input.name='previousEventChoice';
    input.className='previousChoice';input.value=String(item.id);
    input.checked=selectedId===String(item.id);
    const content=document.createElement('span');
    content.className='previous-event-content';
    const title=document.createElement('strong');
    title.className='previous-event-title';
    title.textContent=item.name;
    const meta=document.createElement('span');
    meta.className='previous-event-meta';
    const town=(item.data&&item.data.event_city)||'Località non indicata';
    const org=(item.data&&item.data.org_name)||'';
    const location=document.createElement('span');
    location.textContent=town;
    meta.appendChild(location);
    if(org&&org.toLocaleLowerCase('it')!==String(item.name).toLocaleLowerCase('it')){
      const organizer=document.createElement('span');
      organizer.textContent=org;meta.appendChild(organizer);
    }
    const submitted=document.createElement('span');
    const parsed=item.submitted_at?new Date(item.submitted_at):null;
    submitted.textContent='Inviata: '+(parsed&&!Number.isNaN(parsed.getTime())
      ?parsed.toLocaleDateString('it-IT'):'data non disponibile');
    meta.appendChild(submitted);
    content.append(title,meta);
    const side=document.createElement('span');
    side.className='previous-event-side';
    const year=document.createElement('span');
    year.className='previous-event-year';
    year.textContent=(Array.isArray(item.years)&&item.years.length
      ?item.years.join(' / '):'Anno n.d.');
    year.title=item.year_basis==='submission'
      ?'Anno di invio (data dell’evento non disponibile)':'Anno di svolgimento';
    const id=document.createElement('small');
    id.textContent='Richiesta #'+item.id;
    side.append(year,id);
    label.append(input,content,side);
    choices.append(label);
  }
  if(!matching.length){
    const empty=document.createElement('p');
    empty.className='previous-events-empty';
    empty.textContent='Nessun evento trovato per l’anno selezionato. Prova «Tutti gli anni».';
    choices.appendChild(empty);
  }
  document.getElementById('previousEventsCount').textContent=
    matching.length+' di '+previousEvents.length+' eventi visualizzati';
}
async function loadPreviousEvents(){
 try{
  const response=await fetch('/api/r/'+encodeURIComponent(token)+'/previous-events',{cache:'no-store'});
  if(!response.ok)return;
  const items=await response.json();
  if(!Array.isArray(items)||items.length===0)return;
  previousEvents=items;
  const yearFilter=document.getElementById('previousYearFilter');
  yearFilter.replaceChildren();
  const all=document.createElement('option');
  all.value='all';all.textContent='Tutti gli anni';
  yearFilter.appendChild(all);
  const years=[...new Set(previousEvents.flatMap(item=>
    Array.isArray(item.years)?item.years:[]))]
    .filter(year=>Number.isInteger(year))
    .sort((a,b)=>b-a);
  for(const year of years){
    const option=document.createElement('option');
    option.value=String(year);option.textContent=String(year);
    yearFilter.appendChild(option);
  }
  yearFilter.value='all';
  yearFilter.onchange=()=>{
    renderPreviousEvents();
    document.getElementById('reuseStatus').textContent='';
  };
  renderPreviousEvents();
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
 const chosen=document.querySelector('input[name="previousEventChoice"]:checked');
 const selected=new Set([...document.querySelectorAll('.reuseField:checked')].map(x=>x.value));
 const status=document.getElementById('reuseStatus');
 if(!chosen){status.textContent='Seleziona un evento precedente da cui copiare i dati.';return}
 if(!selected.size){status.textContent='Seleziona almeno un dato da copiare.';return}
 if(!confirm('Copiare i campi scelti dall’evento selezionato? L’email dell’invito, i consensi, le date e gli orari rimarranno invariati.'))return;
 let count=0;
 const source=previousEvents.find(x=>String(x.id)===chosen.value);
 if(!source){status.textContent='L’evento selezionato non è più disponibile.';return}
 for(const [key,value] of Object.entries(source.data||{})){
  if(!selected.has(key)||value===null||value===undefined||value==='')continue;
  if(multiChoiceNames.includes(key)){
   setCheckboxes(key,value);
   count++;continue;
  }
  const target=form.elements[key];
  if(!target)continue;
  target.value=typeof value==='boolean'?String(value):value;
  count++;
 }
 if(selected.has('risk_options') && source.data && Array.isArray(source.data.risk_options)
    && !Array.isArray(source.data.involved_entities)){
   const legacy=['Protezione civile','Vigili del fuoco','Forze dell’ordine'];
   setCheckboxes('involved_entities',source.data.risk_options.filter(x=>legacy.includes(x)));
 }
 // Historical records may only include the combined contact field.
 // Prefill the split inputs as a suggestion and require manual confirmation.
 if(selected.has('org_contact') && source.data && source.data.org_contact &&
    !source.data.org_first_name && !source.data.org_last_name){
   const words=source.data.org_contact.trim().split(/\s+/);
   form.elements.org_first_name.value=words.length>1?words.slice(0,-1).join(' '):words[0];
   form.elements.org_last_name.value=words.length>1?words[words.length-1]:'';
 }
 syncOrgContact();updateRoadDocumentation();
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
          const reasons={
            timeout:'La ricerca indirizzi è troppo lenta (timeout del servizio).',
            rate_limited:'Il servizio indirizzi ha limitato temporaneamente le richieste.',
            provider_http:'Il servizio indirizzi sta rispondendo con un errore.',
            connection:'Il server non riesce a collegarsi al servizio indirizzi.',
            invalid_response:'Il servizio indirizzi ha restituito una risposta non valida.'
          };
          report((reasons[data.reason]||'Il servizio indirizzi non è momentaneamente disponibile.')+
            ' Puoi inserire l’indirizzo manualmente.');
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
const fields=['org_name','org_contact','org_first_name','org_last_name','org_address','org_tax_code','org_vat','org_sdi','org_phone','org_email','org_pec' ,'event_name','event_city','event_place','event_description','reference_name','reference_phone','event_type','recurrence','location_type','road_closure','participants_athletes','participants_public','children','elderly','disabled','road_documents','event_pause','crowd_age_profile','crowd_density','crowd_mood','crowd_position','involved_entities_other','additional_notes'];const risks=['Prevista vendita/consumo di alcool','Possibile consumo di droghe','Presenza categorie fragili','Evento ampiamente pubblicizzato','Presenza figure politiche/religiose','Possibili difficoltà nella viabilità','Tensioni socio-politiche','Ambiente acquatico','Palco o ponteggio temporaneo','Presenza di recinzioni','Servizi igienici','Disponibilità acqua'];document.getElementById('risks').innerHTML=risks.map((r,i)=>'<label class="check"><input type="checkbox" name="risk_options" value="'+r+'">'+r+'</label>').join('');const checkboxOptionGroups={
 venue_context:{id:'venueContextChoices',values:['In città','In periferia/paesi o piccoli centri urbani','In ambiente acquatico (lago, fiume, mare, piscina)','Altro (montano, impervio o rurale)']},
 venue_features:{id:'venueFeaturesChoices',values:['Al coperto',"All'aperto",'Localizzato e ben definito','Esteso oltre un campo da calcio','Non delimitato da recinzioni','Delimitato da recinzioni','Presenza di scale in entrata e/o uscita','Recinzioni temporanee','Ponteggio temporaneo, palco o coperture','Percorso isolato','Percorso su strada']},
 venue_logistics:{id:'venueLogisticsChoices',values:['Servizi igienici disponibili',"Disponibilità d'acqua",'Punto di ristoro']},
 involved_entities:{id:'involvedEntitiesChoices',values:['Protezione civile','Vigili del fuoco','Forze dell’ordine','Altro']}
};
const multiChoiceNames=['risk_options',...Object.keys(checkboxOptionGroups)];
for(const [name,group] of Object.entries(checkboxOptionGroups)){
 const container=document.getElementById(group.id);
 for(const value of group.values){
  const label=document.createElement('label');label.className='check';
  const input=document.createElement('input');input.type='checkbox';input.name=name;input.value=value;
  label.append(input,document.createTextNode(' '+value));container.append(label);
 }
}
function setCheckboxes(name,values){
 const selected=new Set(Array.isArray(values)?values:[]);
 document.querySelectorAll('[name="'+name+'"]').forEach(box=>box.checked=selected.has(box.value));
}
function checkedChoices(name){
 return [...document.querySelectorAll('[name="'+name+'"]:checked')].map(box=>box.value);
}
function syncOrgContact(){
 const first=form.elements.org_first_name.value.trim();
 const last=form.elements.org_last_name.value.trim();
 if(first&&last)form.elements.org_contact.value=first+' '+last;
}
function updateRoadDocumentation(){
 const onRoad=form.elements.road_closure.value==='true' ||
  form.elements.location_type.value==='Percorso su strada' ||
  checkedChoices('venue_features').includes('Percorso su strada');
 document.getElementById('roadDocumentsField').classList.toggle('hidden',!onRoad);
 form.elements.road_documents.required=onRoad;
}
form.elements.road_closure.addEventListener('change',updateRoadDocumentation);
form.elements.location_type.addEventListener('change',updateRoadDocumentation);
document.getElementById('venueFeaturesChoices').addEventListener('change',updateRoadDocumentation);
updateRoadDocumentation();
function message(m,bad=false){notice.className='notice '+(bad?'err':'good');notice.textContent=m;window.scrollTo({top:0,behavior:'smooth'})}async function init(){try{const r=await fetch('/api/r/'+token);if(!r.ok)throw Error('Link non valido, scaduto o già chiuso');const x=await r.json();if(x.status==='submitted'||x.status==='approved'){form.classList.add('hidden');message('Questa richiesta è già stata inviata e non può essere riutilizzata.');return}form.elements.org_email.value=x.customer_email||'';form.elements.event_name.value=x.event_name||'';form.elements.event_city.value=x.event_city||'';loadPreviousEvents();if(x.status==='draft'){if(Array.isArray(x.data.event_slots)&&x.data.event_slots.length){slotContainer.replaceChildren();x.data.event_slots.forEach(x=>addSlot(x.date,x.start,x.end))}for(const [k,v]of Object.entries(x.data)){if(multiChoiceNames.includes(k)){setCheckboxes(k,v)}else if(form.elements[k]){if(form.elements[k].type==='checkbox')form.elements[k].checked=!!v;else form.elements[k].value=v}}}if(x.status==='draft'&&Array.isArray(x.data.risk_options)&&!Array.isArray(x.data.involved_entities)){setCheckboxes('involved_entities',x.data.risk_options.filter(k=>['Protezione civile','Vigili del fuoco','Forze dell’ordine'].includes(k)))}if(x.status==='draft'&&x.data.org_contact&&!x.data.org_first_name){const words=x.data.org_contact.trim().split(/\s+/);form.elements.org_first_name.value=words.length>1?words.slice(0,-1).join(' '):words[0];form.elements.org_last_name.value=words.length>1?words[words.length-1]:''}updateRoadDocumentation()}catch(err){form.classList.add('hidden');message(err.message,true)}}form.onsubmit=async e=>{e.preventDefault();
 const submit=e.submitter||form.querySelector('[type=submit]');
 if(submit?.disabled)return;
if(!confirm('Confermi invio definitivo? Dopo l’invio non potrai modificare la richiesta con questo link.'))return;if(!validateTax()){form.reportValidity();return}syncOrgContact();updateRoadDocumentation();if(!form.reportValidity())return;let slots;try{slots=readSlots()}catch(err){message(err.message,true);return}const values={event_slots:slots,event_dates:slots.map(x=>x.date).join(', '),event_time:slots.map(x=>x.date+' '+x.start+'–'+x.end).join('; ')};for(const k of fields){let el=form.elements[k];values[k]=el.value}for(const k of ['participants_athletes','participants_public','children','elderly','disabled'])values[k]=Number(values[k]||0);values.road_closure=values.road_closure==='true';for(const name of multiChoiceNames)values[name]=checkedChoices(name);values.privacy_ack=form.elements.privacy_ack.checked;values.declaration=form.elements.declaration.checked;if(submit){submit.disabled=true;submit.textContent='Invio in corso…'}
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
