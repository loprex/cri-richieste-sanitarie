
let previousEvents=[];
async function loadPreviousEvents(){
 try{
  const response=await fetch('/api/r/'+encodeURIComponent(token)+'/previous-events');
  if(!response.ok)return;
  previousEvents=await response.json();
  const box=document.getElementById('previousEventsBox'),select=document.getElementById('previousEvent');
  if(!previousEvents.length)return;
  for(const event of previousEvents){const opt=document.createElement('option');opt.value=String(event.id);opt.textContent=event.name+' (richiesta #'+event.id+')';select.appendChild(opt)}
  box.classList.remove('hidden');
 }catch(e){/* Keep manual compilation available if history is unavailable. */}
}
document.getElementById('reuseEvent').onclick=()=>{
 const chosen=previousEvents.find(x=>String(x.id)===document.getElementById('previousEvent').value);
 if(!chosen)return;
 if(!confirm('Recuperare i dati dell’evento precedente? Date e orari attuali resteranno invariati.'))return;
 for(const [key,value] of Object.entries(chosen.data)){
   if(key==='risk_options'){document.querySelectorAll('[name=risk_options]').forEach(c=>c.checked=Array.isArray(value)&&value.includes(c.value));continue}
   const el=form.elements[key];
   if(el)el.value=typeof value==='boolean'?String(value):value;
 }
 message('Informazioni evento recuperate. Inserisci le nuove date e fasce orarie e controlla i dati prima dell’invio.');
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
 const even='ABCDEFGHIJKLMNOPQRSTUVWXYZ', odd='BAKPLCQDREVOSFTGUHMINJWZYX';
 let sum=0;for(let i=0;i<15;i++){const c=s[i];const n=/\d/.test(c)?Number(c):even.indexOf(c);sum+=(i%2===0)?([1,0,5,7,9,13,15,17,19,21][n]??odd.indexOf(c)):(/\d/.test(c)?n:even.indexOf(c));}
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
let placeController=null,placeTimer=null;
const placeInput=form.elements.event_place,suggestions=document.getElementById('placeSuggestions');
placeInput.addEventListener('input',()=>{
 clearTimeout(placeTimer);if(placeController)placeController.abort();suggestions.replaceChildren();
 const query=placeInput.value.trim();if(query.length<3)return;
 placeTimer=setTimeout(async()=>{
  placeController=new AbortController();
  try{
   const response=await fetch('https://photon.komoot.io/api/?limit=5&lang=it&q='+encodeURIComponent(query),{signal:placeController.signal});
   if(!response.ok)return;
   const body=await response.json();suggestions.replaceChildren();
   for(const feature of (body.features||[])){
    const p=feature.properties||{}, address=[p.name,p.street,p.housenumber,p.postcode,p.city,p.state,p.country].filter(Boolean).join(', ');
    if(!address)continue;const button=document.createElement('button');button.type='button';button.className='secondary';button.style.cssText='display:block;width:100%;margin:4px 0;text-align:left';button.textContent=address;button.onclick=()=>{placeInput.value=address;suggestions.replaceChildren()};suggestions.appendChild(button);
   }
  }catch(e){if(e.name!=='AbortError')suggestions.replaceChildren()}
 },450);
});
const token=location.pathname.split('/').pop(),notice=document.getElementById('notice'),form=document.getElementById('form');const fields=['org_name','org_contact','org_address','org_tax_code','org_vat','org_sdi','org_phone','org_email','org_pec','event_name','event_place','event_description','reference_name','reference_phone','event_type','recurrence','location_type','road_closure','participants_athletes','participants_public','children','elderly','disabled','additional_notes'];const risks=['Prevista vendita/consumo di alcool','Possibile consumo di droghe','Presenza categorie fragili','Evento ampiamente pubblicizzato','Presenza figure politiche/religiose','Possibili difficoltà nella viabilità','Tensioni socio-politiche','Ambiente acquatico','Palco o ponteggio temporaneo','Presenza di recinzioni','Servizi igienici','Disponibilità acqua','Protezione civile','Vigili del fuoco','Forze dell’ordine'];document.getElementById('risks').innerHTML=risks.map((r,i)=>'<label class="check"><input type="checkbox" name="risk_options" value="'+r+'">'+r+'</label>').join('');function message(m,bad=false){notice.className='notice '+(bad?'err':'good');notice.textContent=m;window.scrollTo({top:0,behavior:'smooth'})}async function init(){try{const r=await fetch('/api/r/'+token);if(!r.ok)throw Error('Link non valido, scaduto o già chiuso');const x=await r.json();if(x.status==='submitted'||x.status==='approved'){form.classList.add('hidden');message('Questa richiesta è già stata inviata e non può essere riutilizzata.');return}form.elements.org_email.value=x.customer_email||'';loadPreviousEvents();if(x.status==='draft'){if(Array.isArray(x.data.event_slots)&&x.data.event_slots.length){slotContainer.replaceChildren();x.data.event_slots.forEach(x=>addSlot(x.date,x.start,x.end))}for(const [k,v]of Object.entries(x.data)){if(k==='risk_options'){document.querySelectorAll('[name=risk_options]').forEach(c=>c.checked=v.includes(c.value))}else if(form.elements[k]){if(form.elements[k].type==='checkbox')form.elements[k].checked=!!v;else form.elements[k].value=v}}}}catch(err){form.classList.add('hidden');message(err.message,true)}}form.onsubmit=async e=>{e.preventDefault();if(!confirm('Confermi invio definitivo? Dopo l’invio non potrai modificare la richiesta con questo link.'))return;if(!validateTax()){form.reportValidity();return}let slots;try{slots=readSlots()}catch(err){message(err.message,true);return}const values={event_slots:slots,event_dates:slots.map(x=>x.date).join(', '),event_time:slots.map(x=>x.date+' '+x.start+'–'+x.end).join('; ')};for(const k of fields){let el=form.elements[k];values[k]=el.value}for(const k of ['participants_athletes','participants_public','children','elderly','disabled'])values[k]=Number(values[k]||0);values.road_closure=values.road_closure==='true';values.risk_options=[...form.querySelectorAll('[name=risk_options]:checked')].map(x=>x.value);values.privacy_ack=form.elements.privacy_ack.checked;values.declaration=form.elements.declaration.checked;try{const r=await fetch('/api/r/'+token,{method:'PUT',headers:{'Content-Type':'application/json'},body:JSON.stringify(values)});if(!r.ok){const j=await r.json();throw Error(typeof j.detail==='string'?j.detail:'Controlla i campi obbligatori')}form.classList.add('hidden');message('Richiesta inviata correttamente. Il Comitato riceverà i dati per la revisione. Conserva questa conferma.')}catch(err){message(err.message,true)}};init();
