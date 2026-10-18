# CRI — Richieste assistenza sanitaria (MVP)
Applicazione **indipendente da LOPREXAPP**. Accesso multiutente, link casuale per singola richiesta, modulo organizzatore, DB, generazione Excel e invio email a destinatari configurabili.

## Funzionamento
1. Admin accede e crea un link per una nuova manifestazione (token casuale 288 bit, memorizzato **solo come hash SHA-256**; il link appare una sola volta).
2. Invia personalmente il link al richiedente. Scadenza 1–60 giorni.
3. Organizzatore compila il questionario; dopo invio definitivo il link **non è riutilizzabile per modificare o inviare**.
4. I dati sono registrati in PostgreSQL. Si genera una copia dell'Excel originale, compilando solo i campi mappati; formule, grafica e sezioni di approvazione restano nel documento.
5. Se l'amministratore ha abilitato la funzione e configurato SMTP, il piano **BOZZA NON APPROVATA** viene inviato automaticamente ai destinatari email configurabili (massimo 20), con oggetto e testo modificabili. L'amministratore può reinviare manualmente.
6. CRI verifica il piano in Excel e approva la richiesta dall'area admin. L'approvazione del workflow **non equivale** ad attestazione sanitaria, firma o autorizzazione dell'evento.

## Account operatori e migrazione
- Al primo avvio dopo l'aggiornamento, l'app crea l'account **admin** con la password già impostata in `ADMIN_PASSWORD`. Il nuovo login richiede **username + password**.
- L'amministratore può creare operatori, disattivarli e reimpostarne la password (minimo 12 caratteri). Le password sono salvate come hash PBKDF2-SHA256 con sale; il reset invalida le sessioni dell'operatore.
- Ciascun operatore accede soltanto alle richieste create dal suo account, inclusi dettagli ed esportazioni. L'amministratore vede tutte le richieste e l'utente creatore; le richieste precedenti al passaggio multiutente rimangono accessibili esclusivamente ad admin.
- Le migrazioni aggiungono `app_users` e `requests.owner_user_id`, senza eliminare le richieste esistenti.
- Prima del deploy eseguire backup del database, poi verificare su staging login admin, creazione operatore, isolamento richieste e reset password.
- Dopo la creazione di un link l'email nel form viene cancellata e il pulsante resta temporaneamente disabilitato per evitare doppi invii.
- Per sicurezza tutti i form usano `POST` e i pulsanti si attivano solo quando gli handler JavaScript sono caricati, impedendo l'esposizione dei dati nella query string.
- Test automatici di sicurezza disponibili in `tests/test_access_control.py` (dipendenze `requirements-test.txt`).

## Sicurezza account: blocco e recupero password
- **Gestione amministrativa**: da **Utenti e password** un amministratore può usare `Blocca accesso` e `Sblocca accesso` sugli altri utenti, compresi gli altri amministratori. Non può bloccare l'account con cui è collegato. Il blocco manuale revoca immediatamente le sessioni e non può essere aggirato con il recupero password.
- **Tre tentativi consecutivi**: `failed_login_attempts` viene salvato in `app_users`. Il terzo inserimento errato della password imposta `auto_locked_at`, revoca le sessioni tramite `auth_version` e impedisce l'accesso anche con la password corretta. Un accesso riuscito prima del terzo errore azzera il contatore. Non sono bloccati per questa regola gli account non ancora attivati.
- **Sblocco dopo errori**: l'amministratore usa `Sblocca dopo errori` senza cambiare la password; l'utente può anche usare **Password dimenticata?** per ricevere un collegamento via email e impostare una nuova password. Il completamento del reset azzera il contatore e rimuove esclusivamente il blocco automatico. L'accesso resta vietato se l'amministratore aveva applicato un blocco manuale.
- **Recupero autonomo**: richiesta a `POST /api/password/forgot`, collegamento `/reset/<token>`, conferma a `POST /api/password/reset/<token>`. Il token casuale viene memorizzato solo come hash, dura 48 ore, è monouso e revoca tutte le sessioni quando la password viene modificata. La richiesta non interrompe la password precedente prima che il link venga utilizzato.
- **Protezione contro abusi**: la pagina restituisce lo stesso messaggio per email conosciute e sconosciute; massimo 5 richieste/15 minuti per IP, oltre a 10 minuti di attesa tra richieste di reset dello stesso account. Restano i limiti dei tentativi di login per IP già implementati. Prima di andare in produzione valutare un rate limiter condiviso tra container/repliche e un controllo a livello WAF.
- **Casella Amministrazione in TEST**: la regola già concordata rimane assoluta: `amministrazione@crivenezia.it` non riceve notifiche, inviti, email di attivazione né di recupero password finché non si abilita esplicitamente la produzione. Per questo l'account può restare in attesa di attivazione durante lo staging; non considerarlo un errore SMTP.
- **Prima del deploy** eseguire backup PostgreSQL, verificare il funzionamento dell'account amministratore primario e che abbia un'email funzionante per la procedura di recupero. Se anche l'unico admin attivo viene bloccato, servirà il recupero email o un intervento amministrativo controllato sui dati, non un reset indiscriminato.

## Eventi, protocollo interno ed email degli operatori
- Ogni nuova richiesta registra subito **nome evento, città, email del destinatario e giorni di validità**; nome evento e città sono mostrati nell'elenco e precompilati nel modulo ricevuto.
- L'invio definitivo assegna in modo atomico il **protocollo gestionale interno** `CRI-VE/AAAA/NNNNNN` e la data/ora di ricezione nel fuso `Europe/Rome`. Il protocollo è unico e immutabile e **non sostituisce la protocollazione ufficiale CRI**, se prevista. Le richieste precedenti restano senza numero, non viene inventato un protocollo retroattivo.
- La lista visualizza data di creazione, scadenza del link quando ancora da compilare, protocollo/data dopo l'invio e, per admin, email e nome dell'operatore che ha creato la richiesta.
- I nuovi operatori accedono con **email e password**; admin assegna/modifica l'email e reimposta le password. Gli account legacy privi di email possono temporaneamente entrare con il vecchio username; dopo l'associazione dell'email lo username non è più un metodo di accesso.
- Il primo amministratore viene migrato senza perdere la password corrente. Per assegnargli automaticamente l'email alla prima migrazione, è possibile impostare `CRI_ADMIN_EMAIL` nel servizio Coolify (opzionale), oppure utilizzare la pagina amministrativa "Utenti e password". Non usare l'indirizzo SMTP come email amministrativa per impostazione predefinita senza consenso.
- Con **Invio automatico Piano Sanitario abilitato**, la bozza XLSX viene inviata in una sola email all'unione senza duplicati di: indirizzi admin configurati, email degli amministratori attivi e email dell'operatore creatore. **Non viene inviata automaticamente al cliente/organizzatore.** SMTP deve essere operativo, l'amministratore deve avere un destinatario configurato e l'operatore creatore deve avere un'email associata. Eventuali errori sono registrati senza perdere il protocollo e la richiesta.
- Il reset password e la modifica email invalidano le sessioni aperte.
- Prima del deploy in staging eseguire il backup del database, controllare i test automatici, verificare che tutti i destinatari email siano appropriati e usare solo dati di prova.

## Protocolli annuali e riutilizzo eventi (dal 2026)
- **Protocollo interno CRI**: al solo **invio definitivo** viene assegnato `CRI-VE/ANNO/NNNNNN`, dove l'anno è quello del momento della registrazione secondo `Europe/Rome` e la sequenza si azzera a ogni cambio di anno. Per esempio, il primo del 2027 sarà **`CRI-VE/2027/000001`**. Le bozze non consumano numeri.
- **Preservazione dello storico**: i protocolli del 2026 già registrati non vengono ricalcolati o rinumerati. Per il primo protocollo successivo a questa modifica nello stesso anno, il contatore riparte dal massimo progressivo già assegnato in quell'anno più uno. La tabella `protocol_counters` viene creata senza cancellare dati; PostgreSQL/SQLite usano una scrittura transazionale unica per impedire numeri duplicati durante invii concorrenti.
- **Eventi precedenti**: ciascun nuovo invito mostra solo le richieste completate della stessa email e dello stesso operatore CRI (massimo 200 tra le più recenti). L'utente può selezionare **un evento alla volta**, visualizzato come scheda con titolo, comune, organizzatore, data invio e ID. Il filtro `Tutti gli anni / anno` si basa sulle date dell'evento (anche più anni, se ci sono più giornate); per i documenti storici senza date rilevabili usa l'anno di registrazione. La selezione dei campi da copiare resta indipendente e non copia mai date, consensi, email dell'invito o protocollo.
- In TEST, dopo backup e deploy, verificare un protocollo nuovo per l'anno corrente e non simulare il rollover cambiando data/ora del server di produzione. Il rollover può essere provato tramite i test automatici.

## Email: quando arriva una notifica e come provarla
- Alla **creazione del link**, il messaggio con il link di compilazione viene inviato all'**organizzatore** tramite SMTP (l'esito di accettazione dal server viene mostrato subito).
- Alla **compilazione definitiva**, se **Impostazioni email → Abilita invio automatico** è selezionato, parte **una sola notifica automatica (trigger sul passaggio a `submitted`)**, con protocollo, data, collegamento riservato ed Excel precompilato allegato. In TEST si avvisano gli altri destinatari CRI configurati, gli amministratori attivi e l'operatore creatore (se con email valida), escludendo sempre **amministrazione@crivenezia.it**. Dopo un passaggio in produzione autorizzato, l'indirizzo amministrativo ufficiale potrà essere incluso tramite attivazione esplicita. La bozza non attiva notifiche e l'invio definitivo non può essere ripetuto dallo stesso link. Non inviare documenti all'organizzatore automaticamente.
- Il link nella notifica ha il formato `/?request=ID`: la richiesta viene aperta dopo il login se e solo se l'operatore ha i permessi necessari. **Non usare il token pubblico** nei messaggi interni.
- L'Excel porta nel nome **data e protocollo interno**; il documento è una **BOZZA DA VERIFICARE**. La registrazione della richiesta viene salvata anche se la notifica fallisce.
- Il blocco di invio ora mostra e memorizza motivazioni sintetiche: `disabled`, `no_recipients`, `smtp_not_configured`, `smtp_send_failed`, `excel_generation_failed`. Sono visibili nell'elenco e nel dettaglio.
- In Impostazioni email esiste una **prova SMTP** senza allegati. La mail di prova può essere inviata soltanto a un indirizzo CRI amministrativo o già incluso nei destinatari configurati; fino a 5 prove per amministratore ogni 15 minuti. Un esito positivo significa accettazione dal server SMTP, **non** consegna certa; controllare anche la posta indesiderata.
- Le richieste compilate prima dell'attivazione delle notifiche si possono reinviare dal rispettivo dettaglio con **Invia / reinvia email**.
- `amministrazione@crivenezia.it` conserva il **ruolo amministratore**, ma ogni email diretta a questa casella è sospesa per tutta la fase TEST: report, inviti, email di attivazione e prove SMTP. I tentativi di inviare il link di attivazione o la prova SMTP a questa email sono bloccati prima di generare/inviare il messaggio. Nessun account viene disattivato dal blocco di posta. Soltanto per il **passaggio in produzione**, impostare **entrambe** le variabili protette `CRI_DEPLOYMENT_ENV=production` e `CRI_ENABLE_ADMINISTRATION_EMAIL=true` nel servizio di produzione e poi eseguire il deploy. Tutti gli altri valori, o una sola variabile, mantengono il blocco. Non abilitarle in staging.
- Per problemi di recapito controllare le variabili protette `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_FROM`, `SMTP_PASSWORD`, `SMTP_SSL` e i log di Coolify. Non inviare mai credenziali SMTP nei ticket.

## Autocompletamento indirizzi (Photon)
- La ricerca usa `https://photon.komoot.io/api`, servizio pubblico dimostrativo **senza SLA** e soggetto a limiti. Nessun errore di geocoding deve impedire di scrivere manualmente.
- Cache volatile di 3 minuti per le ricerche ripetute, tempo massimo di risposta 8 secondi. Le richieste di ricerca non sono registrate nei log; i log riportano solo categoria dell'errore o codice HTTP.
- In caso di problema, il modulo mostra ora una causa distinta tra **timeout**, **limite di richieste**, **errore HTTP**, **problema di connessione/DNS** e **risposta non valida**. Dopo il deploy leggere il messaggio e, se persiste, verificare da Coolify la connettività HTTPS in uscita del container verso `photon.komoot.io:443`.
- L'assenza di connessione esterna o l'indisponibilità del servizio demo non può essere risolta dalla sola modifica al formulario; in produzione valutare un geocoder contrattualizzato/affidabile con disponibilità garantita.

## Deploy Coolify
- Repository GitHub dedicato / servizio nuovo, senza collegamento a Portal/SSO/LOPREXAPP.
- Crea database **PostgreSQL dedicato**, utente e password dedicati e impostane `DATABASE_URL` (vedi `.env.example`).
- Crea applicazione Dockerfile nella medesima rete privata del DB; esponi porta 8000 dietro dominio HTTPS.
- Imposta `PUBLIC_BASE_URL`, `ADMIN_PASSWORD` (>=24 caratteri casuali), `SESSION_SECRET` (>=32 caratteri casuali), `COOKIE_SECURE=true` e `SMTP_*` tramite secret environment di Coolify.
- Rendi il database accessibile **solo internamente**; limita l'accesso admin tramite reverse proxy, VPN o allow-list se possibile; abilita backup cifrati e aggiornamenti.
- Non caricare `.env` né credenziali su GitHub.
- Prima di attivare invii reali, configura SMTP e prova l'invio con dati sintetici. Usa una mailbox protetta: l'Excel allegato contiene dati personali.

## Avvio locale (sviluppo)
```bash
python -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
export ADMIN_PASSWORD='password-casuale-lunga-almeno-24-caratteri'
export SESSION_SECRET='chiave-casuale-lunga-almeno-32-caratteri'
export COOKIE_SECURE=false
uvicorn app.main:app --reload
```
Per comodità locale si usa SQLite nel volume `/data`; **in produzione configurare PostgreSQL**.

## Non ancora incluso / prima del go-live
- Validazione DPO/ufficio privacy: il PDF informativo ricevuto riguarda i soci CRI e non necessariamente i clienti; serve informativa corretta e base giuridica per organizzatori.
- Non è stata implementata una firma elettronica conforme per il piano: eventuale sottoscrizione richiede procedimento dedicato.
- Verificare con ufficio sanitario **tutti i campi** e la mappatura della cartella Excel; questa versione trasferisce solo i campi certamente individuati (`app/excel.py`). Le parti che comportano valutazione/rischio clinico rimangono in carico alla CRI.
- Completare questionario Allegato 4 (densità, durata, logistica, posizione partecipanti, età, enti coinvolti ecc.) con UI strutturata anziché note generiche.
- Implementare limite tentativi/rate-limiting, MFA amministratore, procedure formali di retention e cancellazione, audit più dettagliato, controllo antivirus/allegati se futuri upload, politiche di backup e test ripristino.
- SMTP sincrono: per elevati volumi prevedere code/outbox con retry e idempotenza; verificare GDPR per inoltro dati personali tramite email e valutare download sicuro anziché allegato.
- Il token può restare leggibile nella cronologia del browser del destinatario, ma non nei log applicativi perché non viene registrato in DB in chiaro; fare attenzione ai log del reverse proxy. Nessuna difesa contro chi ottenga il link: inviare solo con canali affidabili.

## Sicurezza
Il link è casuale e non parlante: questo riduce i tentativi di indovinare l'URL, ma **non sostituisce autenticazione e autorizzazione**. L'accesso admin è protetto da sessione HttpOnly e CSRF; per uso pubblico adottare controlli aggiuntivi indicati sopra.
