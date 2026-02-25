#!/usr/bin/env bash

# Script pour activer ou désactiver facilement le cron de publication Pinterest
# Usage: ./toggle_autopilot.sh [on|off]

WORKFLOW_FILE=".github/workflows/daily-pins.yml"

if [ ! -f "$WORKFLOW_FILE" ]; then
    echo "❌ Erreur : Le fichier de workflow $WORKFLOW_FILE est introuvable."
    exit 1
fi

if [ -z "$1" ]; then
    echo "Usage: ./toggle_autopilot.sh [on|off]"
    echo "  on  : Active la publication automatique (décommente le cron)"
    echo "  off : Met en pause la publication automatique (commente le cron)"
    
    # Vérifier l'état actuel
    if grep -q "^    - cron:" "$WORKFLOW_FILE"; then
        echo -e "\n🟢 Statut actuel : ACTIF (Le cron est activé)"
    else
        echo -e "\n🔴 Statut actuel : EN PAUSE (Le cron est désactivé)"
    fi
    exit 0
fi

ACTION=$1

if [ "$ACTION" == "on" ]; then
    echo "Activation du cron..."
    # Remplacer "# schedule:" par "  schedule:" et "# - cron:" par "- cron:"
    sed -i '' 's/^#[[:space:]]*schedule:/  schedule:/g' "$WORKFLOW_FILE"
    sed -i '' 's/^[[:space:]]*#[[:space:]]*- cron:/    - cron:/g' "$WORKFLOW_FILE"
    echo "✅ Cron activé dans $WORKFLOW_FILE"
    
elif [ "$ACTION" == "off" ]; then
    echo "Désactivation du cron (Mise en pause)..."
    # Remplacer "schedule:" par "# schedule:" et "- cron:" par "# - cron:"
    sed -i '' 's/^[[:space:]]*schedule:/# schedule:/g' "$WORKFLOW_FILE"
    sed -i '' 's/^[[:space:]]*- cron:/    # - cron:/g' "$WORKFLOW_FILE"
    echo "⏸️  Cron désactivé dans $WORKFLOW_FILE"
    
else
    echo "❌ Action non reconnue : $ACTION"
    echo "Utilisez 'on' ou 'off'."
    exit 1
fi

# Push les changements
echo "Sauvegarde sur GitHub..."
git add "$WORKFLOW_FILE"
git commit -m "chore: toggle autopilot cron scheduling ($ACTION)"

if git push; then
    echo "🚀 Changements pushés avec succès ! L'autopilot est maintenant $ACTION."
else
    echo "⚠️ Le push a échoué. Veuillez vérifier l'état de votre dépôt (git status)."
fi
