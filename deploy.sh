#!/usr/bin/env bash
# ==============================================================================
# AllLogic Online — Script Oficial de Build e Deploy do Agillex Agenda
# Domínio Oficial: agenda.agillex.com.br
# ==============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "🚀 Iniciando validação e publicação do Agillex Agenda (agenda.agillex.com.br)..."

# 1. Validação de sintaxe Python
python3 -m py_compile app.py models.py database.py config.py

# 2. Sincronizar com GitHub
echo "📤 Enviando código para o GitHub..."
git push origin main

# 3. Deploy na VPS de Produção (136.248.113.145)
SSH_KEY="$HOME/.ssh/ssh-key-2026-07-03.key"
VPS_HOST="dresler@136.248.113.145"

if [ -f "$SSH_KEY" ]; then
  echo "🚀 Atualizando container em produção na VPS..."
  ssh -i "$SSH_KEY" -o StrictHostKeyChecking=no "$VPS_HOST" "
    cd /opt/alllogic/stacks/scheduler &&
    git fetch origin main &&
    git reset --hard origin/main &&
    docker compose -f compose.yaml build scheduler &&
    docker compose -f compose.yaml up -d --force-recreate scheduler
  "
  echo "✅ Deploy em produção concluído com sucesso!"
fi

echo ""
echo "🎉 AGILLEX AGENDA PUBLICADO!"
echo "👉 https://agenda.agillex.com.br"
