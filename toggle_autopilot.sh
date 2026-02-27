#!/usr/bin/env bash

# Script pour activer ou désactiver facilement le cron de publication Pinterest
# Usage: ./toggle_autopilot.sh [on|off]

WORKFLOW_FILE=".github/workflows/daily-pins.yml"

if [ ! -f "$WORKFLOW_FILE" ]; then
    echo "❌ Erreur : Le fichier de workflow $WORKFLOW_FILE est introuvable."
    exit 1
fi

if [ -z "$1" ]; then
    echo "Usage: ./toggle_autopilot.sh [on <nombre_de_pins> <sandbox|production> | off]"
    echo "  on <N> <mode> : Active la publication pour N pins par jour."
    echo "                  Mode doit être 'sandbox' ou 'production'."
    echo "  off           : Met en pause la publication automatique (commente le cron)"
    
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
    if [ -z "$2" ] || [ -z "$3" ]; then
        echo "❌ Erreur: Le <nombre_de_pins> et le <mode> sont obligatoires pour 'on'."
        echo "Usage: ./toggle_autopilot.sh on <nombre> <sandbox|production>"
        exit 1
    fi
    N=$2
    MODE=$3
    
    if ! [[ "$N" =~ ^[0-9]+$ ]] || [ "$N" -lt 1 ] || [ "$N" -gt 24 ]; then
        echo "❌ Erreur: Veuillez entrer un nombre entier de pins entre 1 et 24."
        exit 1
    fi
    
    if [[ "$MODE" != "sandbox" && "$MODE" != "production" ]]; then
        echo "❌ Erreur: Le mode doit être soit 'sandbox', soit 'production'."
        exit 1
    fi
    
    echo "Calcul des intervalles pour $N publication(s) par jour..."
    # Génère N heures équitablement réparties sur 24h
    HOURS=$(python3 -c "import sys; n=int(sys.argv[1]); print(','.join(str(int(i*24/n)) for i in range(n)))" "$N")
    CRON="0 $HOURS * * *"
    
    echo "Activation du cron avec la règle : $CRON"
    # Remplacer "# schedule:" par "  schedule:"
    sed -i '' 's/^#[[:space:]]*schedule:/  schedule:/g' "$WORKFLOW_FILE"
    
    # Remplacer silencieusement l'ancien cron par le nouveau (commenté ou non)
    sed -i '' "s/^[[:space:]]*#*[[:space:]]*- cron:.*/    - cron: '$CRON'/g" "$WORKFLOW_FILE"
    
    # Mettre à jour la variable d'environnement du mode (sandbox/production)
    sed -i '' "s/^[[:space:]]*CRON_PUBLISH_MODE:.*/  CRON_PUBLISH_MODE: '$MODE' # Modifié automatiquement par toggle_autopilot.sh. Valeurs: 'sandbox', 'production'/g" "$WORKFLOW_FILE"
    
    echo "✅ Cron activé dans $WORKFLOW_FILE en mode '$MODE'"
    
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

# Vérifier si le fichier a été modifié
if git diff --quiet "$WORKFLOW_FILE" && git diff --cached --quiet "$WORKFLOW_FILE"; then
    echo "ℹ️  Aucune modification détectée. L'autopilot était déjà configuré sur l'état '$ACTION'."
    exit 0
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
