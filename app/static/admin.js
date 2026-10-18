const FIELD_LABELS={org_name:'Ragione sociale / Ente organizzatore',org_contact:'Nome e cognome referente',org_address:'Indirizzo sede legale',org_tax_code:'Codice fiscale',org_vat:'Partita IVA',org_sdi:'Codice destinatario SDI',org_phone:'Telefono organizzatore',org_email:'Email organizzatore',org_pec:'PEC organizzatore',event_name:'Nome Evento / Società organizzatrice',event_dates:'Data / periodo evento',event_time:'Orario evento',event_place:'Luogo evento',event_description:'Descrizione evento',reference_name:'Referente sul posto',reference_phone:'Cellulare referente',participants_public:'Pubblico / spettatori / visitatori previsti',participants_athletes:'Partecipanti attivi previsti',road_closure:'Modifiche alla viabilità',additional_notes:'Note organizzative'};
const STATUS_LABELS={draft:'Da compilare',pending:'Da compilare',submitted:'Ricevuta – da verificare',approved:'Approvata dalla CRI',expired:'Scaduta',cancelled:'Annullata'};
function humanLabel(k){return FIELD_LABELS[k]||k.replace(/_/g,' ').replace(/^./,c=>c.toUpperCase())}
function humanStatus(s){return STATUS_LABELS[s]||s}
const MAIL_STATUS={disabled:'Invio automatico disattivato',no_recipients:'Nessun destinatario valido',smtp_not_configured:'SMTP non configurato',smtp_send_failed:'Errore SMTP',excel_generation_failed:'Errore nella generazione Excel',not_submitted:'Richiesta non ancora compilata',already_sent:'Già inviata',sent:'Email accettata dal server SMTP',failed:'Invio fallito'};
function mailStatus(code){return MAIL_STATUS[code]||code||'Non inviata'}
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
 currentUser={id:session.user_id,email:session.email,legacy_login:session.legacy_login,is_admin:session.is_admin,display_name:session.display_name};
 $('login').classList.add('hidden');$('dashboard').classList.remove('hidden');
 $('whoAmI').textContent=(session.display_name||session.email||session.legacy_login)+(session.is_admin?' · Amministratore':' · Operatore');
 document.querySelectorAll('.adminOnly').forEach(x=>x.classList.toggle('hidden',!session.is_admin));
 showSection('requests');refresh();
 const requestedId=new URLSearchParams(location.search).get('request');
 if(requestedId&&/^[1-9][0-9]{0,8}$/.test(requestedId))openDetail(Number(requestedId));
}
$('loginForm').onsubmit=async e=>{e.preventDefault();try{let r=await api('/login','POST',{email:$('username').value,password:$('password').value});csrf=r.csrf;$('password').value='';onLogin(r)}catch(err){msg(err.message,true)}};
$('showForgotPassword').onclick=()=>{
 const panel=$('forgotPasswordPanel');
 const opened=panel.classList.contains('hidden');
 panel.classList.toggle('hidden',!opened);
 $('showForgotPassword').setAttribute('aria-expanded',String(opened));
 if(opened){
   $('forgotPasswordEmail').value=$('username').value.includes('@')?$('username').value:'';
   $('forgotPasswordEmail').focus();
 }
};
$('forgotPasswordForm').onsubmit=async e=>{
 e.preventDefault();
 const button=$('forgotPasswordSubmit');
 if(button.disabled)return;
 button.disabled=true;
 $('forgotPasswordStatus').textContent='Elaborazione richiesta in corso…';
 try{
  const result=await api('/password/forgot','POST',{email:$('forgotPasswordEmail').value.trim()});
  $('forgotPasswordStatus').textContent=result.message;
 }catch(err){
  $('forgotPasswordStatus').textContent='Impossibile completare la richiesta. Riprova più tardi.';
 }finally{button.disabled=false}
};
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
  return '<tr><td>'+r.id+'</td><td><b>'+esc(r.event_name||'Evento non specificato')+'</b><div>'+esc(r.event_city||'Città da specificare')+'</div><div class="muted">'+esc(r.org_name||r.customer_email)+'</div></td><td>'+esc(formatDate(r.created_at))+'</td><td>'+esc(expiry)+(expired?' <span class="pill">Scaduto</span>':'')+'</td><td>'+protocol+'</td><td><span class="pill">'+esc(humanStatus(r.status))+(r.archived_at?' · Archiviata':'')+'</span></td><td>'+esc(r.mailed_at?'Inviata':(r.mail_error?mailStatus(r.mail_error):'Non inviata'))+'</td>'+owner+'<td><button class="secondary" data-id="'+r.id+'">Apri</button></td></tr>';
 }).join('')||'<tr><td colspan="'+(currentUser.is_admin?'9':'8')+'">Nessuna richiesta in questa sezione</td></tr>';
 document.querySelectorAll('[data-id]').forEach(b=>b.onclick=()=>openDetail(Number(b.dataset.id)));
 document.querySelectorAll('.filterView').forEach(b=>{
  const active=b.dataset.filter===currentFilter;b.classList.toggle('secondary',!active);b.setAttribute('aria-pressed',String(active));
 });
}catch(e){msg(e.message,true)}}
document.querySelectorAll('.filterView').forEach(b=>b.onclick=()=>{currentFilter=b.dataset.filter;$('detailPanel').classList.add('hidden');refresh()});
$('refresh').onclick=refresh;
async function openDetail(id){try{let r=await api('/requests/'+id);selected=id;const data=r.data;const emailState=r.mailed_at?'Email inviata il '+formatDate(r.mailed_at):mailStatus(r.mail_error);$('detailPanel').classList.remove('hidden');$('detail').innerHTML='<p><b>Stato:</b> '+esc(humanStatus(r.status))+' • <b>Email:</b> '+esc(r.customer_email)+'</p><p><b>Notifica CRI:</b> '+esc(emailState)+'</p><p><b>Evento:</b> '+esc(r.planned_event_name||data.event_name||'—')+' • <b>Città:</b> '+esc(r.planned_event_city||data.event_city||'—')+'</p><p><b>Protocollo interno:</b> '+esc(r.protocol_number||'Non ancora assegnato')+' • <b>Data:</b> '+esc(formatDate(r.protocol_at))+'</p><div class="gridtable"><table><tbody>'+Object.entries(data).map(([k,v])=>'<tr><th>'+esc(humanLabel(k))+'</th><td>'+esc(humanValue(v))+'</td></tr>').join('')+'</tbody></table></div>';$('notes').value=r.notes||'';$('detailActions').innerHTML='<a href="/api/requests/'+id+'/excel" target="_blank">Scarica Piano Sanitario Excel</a> &nbsp; <a href="/api/requests/'+id+'/data" target="_blank">Esporta dati JSON</a><p><button id="approve">Approva richiesta</button> <button id="sendmail" class="secondary">Invia / reinvia email</button></p>';if(!currentUser.is_admin){$('approve').remove();$('notes').disabled=true}$('approve')?.addEventListener('click',async()=>{if(!confirm('Confermi approvazione amministrativa della richiesta? Il file richiede comunque la verifica sanitaria competente.'))return;try{await api('/requests/'+id+'/approve','POST',{notes:$('notes').value});msg('Stato aggiornato.');refresh();openDetail(id)}catch(e){msg(e.message,true)}});$('sendmail').onclick=async()=>{if(!confirm('Inviare il piano Excel ai destinatari configurati?'))return;try{let x=await api('/requests/'+id+'/send-email','POST',{});msg('Notifica CRI: '+mailStatus(x.status),x.status!=='sent');refresh();openDetail(id)}catch(e){msg(e.message,true)}};const archive=document.createElement('button');archive.type='button';archive.className='secondary';archive.textContent=r.archived_at?'Ripristina richiesta':'Archivia richiesta';archive.onclick=async()=>{const archiveIt=!r.archived_at;if(!confirm(archiveIt?'Spostare questa richiesta in Archiviate? I dati verranno conservati.':'Riportare questa richiesta nell’elenco attivo?'))return;try{await api('/requests/'+id+'/archive?archived='+archiveIt,'POST',{});$('detailPanel').classList.add('hidden');msg(archiveIt?'Richiesta archiviata.':'Richiesta ripristinata.');refresh()}catch(e){msg(e.message,true)}};$('detailActions').appendChild(archive);$('detailPanel').scrollIntoView({behavior:'smooth'})}catch(e){msg(e.message,true)}}
async function loadMail(){try{
 const cfg=await api('/settings/mail');
 $('recipients').value=cfg.recipients;$('subject').value=cfg.subject;
 $('body').value=cfg.body;$('enabled').checked=cfg.enabled;
 $('smtpStatus').textContent=(cfg.smtp_ready?'SMTP configurato':'SMTP NON configurato in Coolify')+
   ' · '+(cfg.enabled?'Invio automatico attivo':'Invio automatico DISATTIVATO: nessuna notifica alla compilazione')+
   (cfg.administration_mail_paused?' · amministrazione@crivenezia.it: INVIO SOSPESO FINO ALLA PRODUZIONE':'');
 if(!$('testEmail').value){
   $('testEmail').value=currentUser.email||
     (cfg.recipients||'').split(/[,;\n]/).map(x=>x.trim()).find(Boolean)||'';
 }
}catch(e){msg(e.message,true)}}
$('mailForm').onsubmit=async e=>{
 e.preventDefault();
 try{
  await api('/settings/mail','PUT',{enabled:$('enabled').checked,
   recipients:$('recipients').value,subject:$('subject').value,body:$('body').value});
  msg('Impostazioni email salvate.');loadMail();
 }catch(err){msg(err.message,true)}
};
$('testMailButton').onclick=async()=>{
 const button=$('testMailButton'),recipient=$('testEmail').value.trim();
 if(!recipient||!$('testEmail').checkValidity()){
   $('testMailStatus').textContent='Inserisci un indirizzo email valido.';return;
 }
 button.disabled=true;$('testMailStatus').textContent='Invio email di prova in corso…';
 try{
  const result=await api('/settings/mail/test','POST',{to:recipient});
  $('testMailStatus').textContent='Il server SMTP ha accettato l’email per '+result.recipient+
    '. Controlla anche Spam e posta indesiderata.';
 }catch(err){$('testMailStatus').textContent='Test non riuscito: '+err.message;}
 finally{button.disabled=false}
};

async function loadUsers(){
 if(!currentUser.is_admin)return;
 try{
  const users=await api('/users');
  $('usersList').innerHTML=users.map(u=>{
   const self=Number(u.id)===Number(currentUser.id);
   const lockedManually=!u.active;
   const lockedAutomatically=!!u.auto_locked_at;
   const state=lockedManually?'Bloccato manualmente':
     lockedAutomatically?'Bloccato dopo 3 errori':
     u.password_setup_required?'In attesa di password':'Attivo';
   const attempts=lockedManually||lockedAutomatically?'':(' · '+(u.failed_login_attempts||0)+'/3 errori');
   const actions=self?'Account in uso':
     '<button type="button" class="secondary statusButton" data-user="'+u.id+
     '" data-active="'+String(u.active)+'">'+(lockedManually?'Sblocca accesso':'Blocca accesso')+'</button>'+
     (lockedAutomatically&&u.active?
      ' <button type="button" class="secondary unlockButton" data-user="'+u.id+
      '">Sblocca dopo errori</button>':'');
   return '<tr><td><b>'+esc(u.display_name)+'</b><div class="muted">'+
     esc(u.email||'Email da configurare (accesso temporaneo: '+u.username+')')+
     '</div><input type="email" class="userEmail" data-user="'+u.id+
     '" value="'+esc(u.email||'')+'" placeholder="email@cri.it" aria-label="Email per '+
     esc(u.display_name)+'"><button type="button" class="secondary saveEmail" data-user="'+u.id+
     '">Salva email</button></td><td>'+esc(u.role==='admin'?'Amministratore':'Operatore')+
     '</td><td><span class="'+(lockedManually||lockedAutomatically?'account-locked':'')+'">'+
     esc(state)+'</span><div class="muted">'+esc(attempts)+'</div></td><td>'+
     '<button type="button" class="secondary sendSetup" data-user="'+u.id+'">'+
     (u.password_setup_required?'Reinvia link':'Invia reset password')+
     '</button></td><td>'+actions+'</td></tr>';
  }).join('');
  document.querySelectorAll('.saveEmail').forEach(b=>b.onclick=async()=>{
   const id=Number(b.dataset.user),input=document.querySelector('.userEmail[data-user="'+id+'"]');
   if(!input||!input.validity.valid||!input.value.trim()){msg('Indica un indirizzo email valido.',true);return}
   if(!confirm('Aggiornare l’email di accesso? Le sessioni esistenti verranno revocate.'))return;
   try{
    await api('/users/'+id+'/email','PUT',{email:input.value.trim()});
    const current=users.find(u=>u.id===id);
    msg('Email operatore aggiornata.');if(current&&current.id===currentUser.id){location.reload();return}
    loadUsers();
   }catch(err){msg(err.message,true)}
  });
  document.querySelectorAll('.sendSetup').forEach(b=>b.onclick=async()=>{
   const id=Number(b.dataset.user),user=users.find(u=>u.id===id);
   if(!user?.email){msg('Configura prima l’email dell’operatore.',true);return}
   if(!confirm('Inviare un nuovo link via email? Il link precedente e la password attuale, se presente, saranno revocati.'))return;
   b.disabled=true;
   try{
    const result=await api('/users/'+id+'/send-setup','POST',{});
    msg(result.activation_status==='sent'?'Link inviato all’operatore.':'Account in attesa: invio email non riuscito. Verifica SMTP e utilizza Reinvia link.',result.activation_status!=='sent');
    loadUsers();
   }catch(err){msg(err.message,true)}finally{b.disabled=false}
  });
  document.querySelectorAll('.statusButton').forEach(b=>b.onclick=async()=>{
   const id=Number(b.dataset.user),active=b.dataset.active==='true';
   if(!confirm(active?'Bloccare manualmente questo account e revocare tutte le sessioni?':'Sbloccare questo account e consentire nuovamente l’accesso?'))return;
   b.disabled=true;
   try{
    await api('/users/'+id+'/status','PUT',{active:!active});
    msg(active?'Account bloccato manualmente.':'Account sbloccato.');
    loadUsers();
   }catch(e){msg(e.message,true)}finally{b.disabled=false}
  });
  document.querySelectorAll('.unlockButton').forEach(b=>b.onclick=async()=>{
   const id=Number(b.dataset.user);
   if(!confirm('Azzera i 3 errori e sblocca questo account? Le sessioni precedenti rimarranno revocate.'))return;
   b.disabled=true;
   try{
    await api('/users/'+id+'/unlock','POST',{});
    msg('Blocco automatico rimosso.');loadUsers();
   }catch(e){msg(e.message,true)}finally{b.disabled=false}
  });
 }catch(err){msg(err.message,true)}
}
$('newUserForm').onsubmit=async e=>{
 e.preventDefault();
 if(!currentUser.is_admin)return;
 const button=$('newUserSubmit');if(button.disabled)return;
 button.disabled=true;
 try{
  const result=await api('/users','POST',{email:$('newEmail').value.trim(),display_name:$('newDisplayName').value});
  $('newUserForm').reset();
  msg(result.activation_status==='sent'?'Operatore creato: link di attivazione inviato via email (48 ore).':'Operatore creato, ma il link non è stato recapitato. Controlla SMTP e usa Reinvia link.',result.activation_status!=='sent');
  loadUsers();
 }catch(err){msg(err.message,true)}finally{button.disabled=false}
};

for(const name of ['loginSubmit','createRequestButton','mailSubmit','newUserSubmit']) $(name).disabled=false;
init();
