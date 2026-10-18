#!/usr/bin/env bash
set -euo pipefail
# Eseguire dalla directory del progetto sul proprio PC/server con git e gh autenticato.
cd "$(dirname "$0")"
OWNER="loprex"
NAME="cri-richieste-sanitarie"
command -v git >/dev/null || { echo 'ERRORE: git mancante'; exit 1; }
command -v gh >/dev/null || { echo 'ERRORE: gh (GitHub CLI) mancante'; exit 1; }
gh auth status >/dev/null 2>&1 || { echo 'ERRORE: autenticare gh con: gh auth login'; exit 1; }
ACTUAL="$(gh api user --jq .login)"
[ "${ACTUAL,,}" = "${OWNER,,}" ] || { echo "STOP: autenticato come $ACTUAL, atteso $OWNER"; exit 1; }
[ ! -e .env ] || { echo 'STOP: presente .env potenzialmente contenente credenziali; rimuoverlo dalla cartella di pubblicazione'; exit 1; }
if ! gh repo view "$OWNER/$NAME" >/dev/null 2>&1; then
  gh repo create "$OWNER/$NAME" --private --description 'CRI - gestione richieste assistenza sanitaria (indipendente da LOPREXAPP)' --confirm
fi
if [ ! -d .git ]; then git init -b main; fi
cat > .gitignore <<'GITIGNORE'
.env
.env.*
!.env.example
__pycache__/
*.pyc
*.db
*.sqlite*
.venv/
.pytest_cache/
GITIGNORE
git add app Dockerfile requirements.txt README.md DEPLOY-COOLIFY-TEST.md .env.example .dockerignore .gitignore pubblica-github.sh
git diff --cached --quiet || git commit -m 'Initial CRI requests TEST application'
git remote remove origin 2>/dev/null || true
git remote add origin "https://github.com/$OWNER/$NAME.git"
git push -u origin main
echo "REPOSITORY_PUBBLICATO=https://github.com/$OWNER/$NAME"
