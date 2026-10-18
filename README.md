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
