const FIELD_LABELS={org_name:'Ragione sociale / Ente organizzatore',org_contact:'Nome e cognome referente',org_address:'Indirizzo sede legale',org_tax_code:'Codice fiscale',org_vat:'Partita IVA',org_sdi:'Codice destinatario SDI',org_phone:'Telefono organizzatore',org_email:'Email organizzatore',org_pec:'PEC organizzatore',event_name:'Nome evento',event_dates:'Data / periodo evento',event_time:'Orario evento',event_place:'Luogo evento',event_description:'Descrizione evento',reference_name:'Referente sul posto',reference_phone:'Cellulare referente',participants_public:'Spettatori / pubblico previsti',participants_athletes:'Atleti previsti',road_closure:'Modifiche alla viabilità',additional_notes:'Note organizzative'};
const STATUS_LABELS={draft:'Da compilare',pending:'Da compilare',submitted:'Ricevuta – da verificare',approved:'Approvata dalla CRI',expired:'Scaduta',cancelled:'Annullata'};
function humanLabel(k){return FIELD_LABELS[k]||k.replace(/_/g,' ').replace(/^./,c=>c.toUpperCase())}
function humanStatus(s){return STATUS_LABELS[s]||s}
function humanValue(v){return v==null||v===''?'Non indicato':Array.isArray(v)?v.join(', '):typeof v==='boolean'?(v?'Sì':'No'):String(v)}
let csrf='';let selected=0;let currentFilter='all';let currentUser={email:'',legacy_login:'',is_admin:false};const $=id=>document.getElementById(id);const esc=x=>String(x??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
function msg(s,bad=false){$('notice').className='notice '+(bad?'err':'good');$('notice').textContent=s;window.scrollTo({top:0,behavior:'smooth'})}
async function api(path,method='GET',body){let r=await fetch('/api'+path,{method,credentials:'same-origin',headers:{'Content-Type':'application/json','x-cri-csrf':csrf},body:body===undefined?undefined:JSON.stringify(body)});if(!r.ok){let e;try{e=(await r.json()).detail}catch{e=r.statusText}throw new Error(typeof e==='string'?e:JSON.stringify(e))}return r.json()}
async function init(){try{const session=await api('/session');csrf=session.csrf;onLogin(session)}catch{}}
function showSection(name){
 if(name!=='requests'&&!currentUser.is_admin)return;
 for(const [section,view,nav] of [['requests','requestsView','navRequests'],['settings','settingsPanel','navSettings'],['users','usersPanel','navUsers']]){
  $(view).classList.toggle('hidden',name!==section);
  $(nav).classList.toggle('secondary',name!==section);
  $(nav).setAttribute('aria-current',String(name===section));
 }
 if(name==='settings')loadMail();
 if(name==='users')loadUsers();
 window.scrollTo({top:0,behavior:'smooth'});
}
$('navRequests').onclick=()=>showSection('requests');
$('navSettings').onclick=()=>showSection('settings');
$('navUsers').onclick=()=>showSection('users');
function onLogin(session){
 currentUser={email:session.email,legacy_login:session.legacy_login,is_admin:session.is_admin,display_name:session.display_name};
 $('login').classList.add('hidden');$('dashboard').classList.remove('hidden');
 $('whoAmI').textContent=(session.display_name||session.email||session.legacy_login)+(session.is_admin?' · Amministratore':' · Operatore');
 document.querySelectorAll('.adminOnly').forEach(x=>x.classList.toggle('hidden',!session.is_admin));
 showSection('requests');refresh();
}
$('loginForm').onsubmit=async e=>{e.preventDefault();try{let r=await api('/login','POST',{email:$('username').value,password:$('password').value});csrf=r.csrf;$('password').value='';onLogin(r)}catch(err){msg(err.message,true)}};
$('logout').onclick=async()=>{try{await api('/logout','POST',{})}finally{location.reload()}};
$('createForm').onsubmit=async e=>{
 e.preventDefault();
 const button=$('createRequestButton');
 if(button.disabled)return;
 const email=$('customerEmail').value.trim();
 button.disabled=true;button.textContent='Creazione e invio in corso…';
 try{
  let r=await api('/requests','POST',{customer_email:email,event_name:$('newEventName').value.trim(),event_city:$('newEventCity').value.trim(),days:Number($('days').value)});
  $('customerEmail').value='';
  $('newEventName').value='';
  $('newEventCity').value='';
  $('days').value='14';
  let box=$('newLink');box.classList.remove('hidden');
  box.innerHTML='<b>Link generato (viene mostrato una sola volta):</b><p><code>'+esc(r.url)+'</code></p><button id="copylink" type="button" class="secondary">Copia link</button><p class="muted">Esito invito email: '+esc(r.invitation_status==='sent'?'inviato':r.invitation_status==='failed'?'invio fallito':r.invitation_status==='smtp_not_configured'?'SMTP non configurato':'da verificare')+'. Per una nuova richiesta inserisci una nuova email.</p>';
  $('copylink').onclick=()=>navigator.clipboard.writeText(r.url);
  refresh();
 }catch(err){msg('Non è stato possibile confermare la creazione: '+err.message+'. Prima di riprovare verifica l’elenco richieste per evitare duplicati.',true)}
 finally{button.disabled=false;button.textContent='Crea link casuale'}
};
function formatDate(value){
 if(!value)return '—';
 const date=new Date(value);
 return Number.isNaN(date.getTime())?'—':new Intl.DateTimeFormat('it-IT',{dateStyle:'short',timeStyle:'short'}).format(date);
}
async function refresh(){try{
 const rows=await api('/requests?view='+encodeURIComponent(currentFilter));
 $('requests').innerHTML=rows.map(r=>{
  const isIncomplete=['pending','draft'].includes(r.status)&&!r.archived_at;
  const expiry=isIncomplete?formatDate(r.expires_at):'—';
  const expired=isIncomplete&&r.expires_at&&new Date(r.expires_at)<new Date();
  const owner=currentUser.is_admin?'<td>'+esc(r.creator_name||'Storico CRI')+'<div class="muted">'+esc(r.creator_email||'Email non configurata')+'</div></td>':'';
  const protocol=r.protocol_number?'<b>'+esc(r.protocol_number)+'</b><div class="muted">'+esc(formatDate(r.protocol_at))+'</div>':'—';
  return '<tr><td>'+r.id+'</td><td><b>'+esc(r.event_name||'Evento non specificato')+'</b><div>'+esc(r.event_city||'Città da specificare')+'</div><div class="muted">'+esc(r.org_name||r.customer_email)+'</div></td><td>'+esc(formatDate(r.created_at))+'</td><td>'+esc(expiry)+(expired?' <span class="pill">Scaduto</span>':'')+'</td><td>'+protocol+'</td><td><span class="pill">'+esc(humanStatus(r.status))+(r.archived_at?' · Archiviata':'')+'</span></td><td>'+esc(r.mailed_at?'Inviata':(r.mail_error?'Errore invio':'Non inviata'))+'</td>'+owner+'<td><button class="secondary" data-id="'+r.id+'">Apri</button></td></tr>';
 }).join('')||'<tr><td colspan="'+(currentUser.is_admin?'9':'8')+'">Nessuna richiesta in questa sezione</td></tr>';
 document.querySelectorAll('[data-id]').forEach(b=>b.onclick=()=>openDetail(Number(b.dataset.id)));
 document.querySelectorAll('.filterView').forEach(b=>{
  const active=b.dataset.filter===currentFilter;b.classList.toggle('secondary',!active);b.setAttribute('aria-pressed',String(active));
 });
}catch(e){msg(e.message,true)}}
document.querySelectorAll('.filterView').forEach(b=>b.onclick=()=>{currentFilter=b.dataset.filter;$('detailPanel').classList.add('hidden');refresh()});
$('refresh').onclick=refresh;
async function openDetail(id){try{let r=await api('/requests/'+id);selected=id;const data=r.data;$('detailPanel').classList.remove('hidden');$('detail').innerHTML='<p><b>Stato:</b> '+esc(humanStatus(r.status))+' • <b>Email:</b> '+esc(r.customer_email)+'</p><p><b>Evento:</b> '+esc(r.planned_event_name||data.event_name||'—')+' • <b>Città:</b> '+esc(r.planned_event_city||data.event_city||'—')+'</p><p><b>Protocollo interno:</b> '+esc(r.protocol_number||'Non ancora assegnato')+' • <b>Data:</b> '+esc(formatDate(r.protocol_at))+'</p><div class="gridtable"><table><tbody>'+Object.entries(data).map(([k,v])=>'<tr><th>'+esc(humanLabel(k))+'</th><td>'+esc(humanValue(v))+'</td></tr>').join('')+'</tbody></table></div>';$('notes').value=r.notes||'';$('detailActions').innerHTML='<a href="/api/requests/'+id+'/excel" target="_blank">Scarica Piano Sanitario Excel</a> &nbsp; <a href="/api/requests/'+id+'/data" target="_blank">Esporta dati JSON</a><p><button id="approve">Approva richiesta</button> <button id="sendmail" class="secondary">Invia / reinvia email</button></p>';if(!currentUser.is_admin){$('approve').remove();$('notes').disabled=true}$('approve')?.addEventListener('click',async()=>{if(!confirm('Confermi approvazione amministrativa della richiesta? Il file richiede comunque la verifica sanitaria competente.'))return;try{await api('/requests/'+id+'/approve','POST',{notes:$('notes').value});msg('Stato aggiornato.');refresh();openDetail(id)}catch(e){msg(e.message,true)}});$('sendmail').onclick=async()=>{if(!confirm('Inviare il piano Excel ai destinatari configurati?'))return;try{let x=await api('/requests/'+id+'/send-email','POST',{});msg('Esito invio: '+x.status,x.status!=='sent');refresh()}catch(e){msg(e.message,true)}};const archive=document.createElement('button');archive.type='button';archive.className='secondary';archive.textContent=r.archived_at?'Ripristina richiesta':'Archivia richiesta';archive.onclick=async()=>{const archiveIt=!r.archived_at;if(!confirm(archiveIt?'Spostare questa richiesta in Archiviate? I dati verranno conservati.':'Riportare questa richiesta nell’elenco attivo?'))return;try{await api('/requests/'+id+'/archive?archived='+archiveIt,'POST',{});$('detailPanel').classList.add('hidden');msg(archiveIt?'Richiesta archiviata.':'Richiesta ripristinata.');refresh()}catch(e){msg(e.message,true)}};$('detailActions').appendChild(archive);$('detailPanel').scrollIntoView({behavior:'smooth'})}catch(e){msg(e.message,true)}}
async function loadMail(){try{let s=await api('/settings/mail');$('recipients').value=s.recipients;$('subject').value=s.subject;$('body').value=s.body;$('enabled').checked=s.enabled;$('smtpStatus').textContent=s.smtp_ready?'Server SMTP configurato':'Server SMTP non configurato: impostarlo in Coolify'}catch(e){msg(e.message,true)}}
$('mailForm').onsubmit=async e=>{e.preventDefault();try{await api('/settings/mail','PUT',{enabled:$('enabled').checked,recipients:$('recipients').value,subject:$('subject').value,body:$('body').value});msg('Impostazioni email salvate')}catch(err){msg(err.message,true)}};

async function loadUsers(){
 if(!currentUser.is_admin)return;
 try{
  const users=await api('/users');
  $('usersList').innerHTML=users.map(u=>'<tr><td><b>'+esc(u.display_name)+'</b><div class="muted">'+esc(u.email||'Email da configurare (accesso temporaneo: '+u.username+')')+'</div><input type="email" class="userEmail" data-user="'+u.id+'" value="'+esc(u.email||'')+'" placeholder="email@cri.it" aria-label="Email per '+esc(u.display_name)+'"><button type="button" class="secondary saveEmail" data-user="'+u.id+'">Salva email</button></td><td>'+esc(u.role==='admin'?'Amministratore':'Operatore')+'</td><td>'+esc(u.active?'Attivo':'Disattivato')+'</td><td><input type="password" class="resetPassword" data-user="'+u.id+'" autocomplete="new-password" minlength="12" placeholder="Nuova password (min. 12)" aria-label="Password per '+esc(u.display_name)+'"><button type="button" class="secondary resetButton" data-user="'+u.id+'">Reimposta</button></td><td>'+(u.role==='admin'?'—':'<button type="button" class="secondary statusButton" data-user="'+u.id+'" data-active="'+String(u.active)+'">'+(u.active?'Disattiva':'Riattiva')+'</button>')+'</td></tr>').join('');
  document.querySelectorAll('.saveEmail').forEach(b=>b.onclick=async()=>{
   const id=Number(b.dataset.user),input=document.querySelector('.userEmail[data-user="'+id+'"]');
   if(!input||!input.validity.valid||!input.value.trim()){msg('Indica un indirizzo email valido.',true);return}
   if(!confirm('Aggiornare l’email di accesso? Le sessioni esistenti verranno revocate.'))return;
   try{
    await api('/users/'+id+'/email','PUT',{email:input.value.trim()});
    const current=users.find(u=>u.id===id);
    msg('Email operatore aggiornata.');
    if(current&&(current.email===currentUser.email||(current.username===currentUser.legacy_login&&currentUser.legacy_login))){location.reload();return}
    loadUsers();
   }catch(err){msg(err.message,true)}
  });
  document.querySelectorAll('.resetButton').forEach(b=>b.onclick=async()=>{
   const id=Number(b.dataset.user),input=document.querySelector('.resetPassword[data-user="'+id+'"]');
   if(!input||input.value.length<12){msg('La password deve avere almeno 12 caratteri.',true);return}
   if(!confirm('Reimpostare la password? Le sessioni esistenti saranno revocate.'))return;
   try{
    await api('/users/'+id+'/password','PUT',{password:input.value});input.value='';
    msg('Password aggiornata. Comunicala con un canale riservato.');
    const target=users.find(u=>u.id===id);
    if(target&&(target.email===currentUser.email||(target.username===currentUser.legacy_login&&currentUser.legacy_login))){location.reload();return}
   }catch(err){msg(err.message,true)}
  });
  document.querySelectorAll('.statusButton').forEach(b=>b.onclick=async()=>{
   const id=Number(b.dataset.user),active=b.dataset.active==='true';
   if(!confirm(active?'Disattivare account e sessioni?':'Riattivare account?'))return;
   try{await api('/users/'+id+'/status','PUT',{active:!active});msg('Stato account aggiornato.');loadUsers()}catch(e){msg(e.message,true)}
  });
 }catch(err){msg(err.message,true)}
}
$('newUserForm').onsubmit=async e=>{
 e.preventDefault();
 if(!currentUser.is_admin)return;
 const button=$('newUserSubmit');if(button.disabled)return;
 button.disabled=true;
 try{
  await api('/users','POST',{email:$('newEmail').value.trim(),display_name:$('newDisplayName').value,password:$('newUserPassword').value});
  $('newUserForm').reset();msg('Operatore creato. Comunica la password iniziale tramite un canale riservato.');loadUsers();
 }catch(err){msg(err.message,true)}finally{button.disabled=false}
};

for(const name of ['loginSubmit','createRequestButton','mailSubmit','newUserSubmit']) $(name).disabled=false;
init();
