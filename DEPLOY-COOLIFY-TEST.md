# CRI Richieste Sanitarie — pubblicazione TEST su Coolify

Questa procedura non modifica LOPREXAPP. Per il primo collaudo usare **dati inventati** e **SMTP disabilitato**.

## 1 — Repository separato
Creare su GitHub, nel profilo `loprex` (non nell'organizzazione LOPREXAPP), un repository **privato** denominato `cri-richieste-sanitarie`. Caricare nella radice i contenuti della directory `cri-piano-sanitario-app` dell'archivio fornito, inclusi `Dockerfile`, `requirements.txt` e `app/`. Non caricare `.env` con credenziali.

## 2 — Nuove risorse Coolify
- Creare progetto autonomo `CRI-RICHIESTE` e ambiente `test`.
- Creare servizio PostgreSQL dedicato `cri-richieste-db-test`, senza porte pubbliche; annotare le credenziali e il nome DNS interno effettivamente assegnato da Coolify.
- Creare Application da repository GitHub privato, branch `main`, build pack `Dockerfile`, porta applicativa `8000`.
- Assegnare un sottodominio TEST sotto controllo proprio, abilitando HTTPS. Non usare il dominio o l'SSO di LOPREXAPP.
- Se il database non è sulla stessa rete privata, collegare la risorsa app alla rete corretta tramite impostazioni Coolify; mai esporre il DB su Internet.

## 3 — Variabili ambiente (Coolify Secrets)
```
ADMIN_PASSWORD=<generare stringa casuale forte >=24 caratteri>
SESSION_SECRET=<generare stringa casuale forte >=32 caratteri>
PUBLIC_BASE_URL=https://<dominio-test>
DATABASE_URL=postgresql+psycopg://<utente>:<password>@<hostname-interno>:5432/<nome_db>
COOKIE_SECURE=true
DATA_DIR=/data
```
Per generare due segreti separati da una macchina affidabile: `python3 -c 'import secrets; print(secrets.token_urlsafe(48)); print(secrets.token_urlsafe(48))'`. Non incollare segreti nella chat o nel repository. Se la password del DB contiene caratteri speciali, codificarli nell'URL (`%40` per `@`, ecc.).

SMTP: **non impostare inizialmente** `SMTP_HOST`, `SMTP_FROM` e credenziali; lasciare la funzione email disabilitata. Solo dopo il test, configurare SMTP sicuro tramite le variabili di `.env.example` e impostare uno o più destinatari nella schermata admin. Le email reali non sono state ancora collaudate.

## 4 — Collaudo TEST
1. `https://<dominio-test>/health` deve rispondere `{"status":"ok"}`.
2. Accesso amministratore con la password impostata.
3. Impostazioni email: verificare `enabled=false`.
4. Creare richiesta destinata ad email **fittizia** e copiare il link generato (mostrato una volta).
5. Aprire il link in navigazione privata; compilare con soli dati sintetici; salvare bozza e poi inviare definitivamente.
6. Riprovare a inviare: deve dare conflitto/impedire una seconda compilazione.
7. Da admin verificare richiesta e scaricare Excel e JSON; controllare la corrispondenza dati.
8. Confrontare Excel generato e modello originale *visivamente in Excel*: la libreria openpyxl può perdere oggetti grafici o disegni; esaminare inoltre tutte le formule e le celle mappate.
9. Testare la modifica dello stato ad approvato: il flusso non costituisce approvazione sanitaria ufficiale.
10. Abilitare email *solo* con mailbox di test e SMTP sicuro; controllare consegna, destinatari, oggetto e allegato senza dati reali.

## 5 — Condizioni per pubblicazione a clienti reali
**NON pubblicare il link del questionario a clienti reali** prima di aver completato: informativa privacy adeguata agli organizzatori (il PDF allegato riguarda soci/associati); completamento dell'intero Allegato 4; verifica ufficiale della mappatura Excel e conservazione grafica; hardening accesso admin (MFA, limiti tentativi, rete/VPN); backup cifrati e prova restore del DB; politica conservazione e cancellazione; sicurezza email/destinazione dati personali; eventuale processo formale di firma e validazione sanitaria. Gli invii via mail saranno documenti *BOZZA NON APPROVATA*.

## 6 — Rollback
Disabilitare il route pubblico su Coolify, mantenere il servizio DB e uno snapshot cifrato, quindi ripristinare la versione Docker precedente. Non modificare risorse LOPREXAPP.
