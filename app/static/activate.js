const form=document.getElementById('activationForm');
const notice=document.getElementById('activateNotice');
const button=document.getElementById('activateSubmit');
const token=location.pathname.split('/').pop();
const recovering=location.pathname.startsWith('/reset/');
if(recovering){
 document.querySelector('.sub').textContent='Recupero password operatore';
 document.querySelector('main h1').textContent='Imposta una nuova password';
}
function feedback(message,bad=false){
  notice.textContent=message;
  notice.className='notice '+(bad?'err':'good');
}
form.addEventListener('submit',async event=>{
  event.preventDefault();
  if(button.disabled)return;
  const password=document.getElementById('newPassword').value;
  const confirm=document.getElementById('confirmPassword').value;
  if(password.length<12||password!==confirm){
    feedback('Le due password devono coincidere e contenere almeno 12 caratteri.',true);
    return;
  }
  button.disabled=true;button.textContent='Attivazione in corso…';
  try{
    const response=await fetch((recovering?'/api/password/reset/':'/api/activate/')+encodeURIComponent(token),{
      method:'POST',cache:'no-store',headers:{'Content-Type':'application/json'},
      body:JSON.stringify({password})
    });
    if(!response.ok){
      const obj=await response.json().catch(()=>({}));
      throw Error(typeof obj.detail==='string'?obj.detail:'Link scaduto o non valido');
    }
    form.classList.add('hidden');
    feedback('Password aggiornata correttamente. Ora puoi accedere con la tua email e la nuova password.');
    history.replaceState(null,'','/');
  }catch(error){feedback(error.message,true)}
  finally{button.disabled=false;button.textContent='Imposta password'}
});
button.disabled=false;button.textContent='Imposta password';
