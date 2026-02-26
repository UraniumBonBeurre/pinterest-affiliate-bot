#!/usr/bin/env bash
# Script pour forcer le push de data/pins_ideas_to_fill.csv systématiquement sur Git (Débogage)

echo "🚀 Forçage du push de data/pins_ideas_to_fill.csv vers GitHub..."
git add data/pins_ideas_to_fill.csv
git commit -m "fix(data): force push manual csv updates for debugging"
git push

echo "✅ Push forcé terminé. Les actions Github vont être déclenchées si le cron le demande."
