#!/usr/bin/env bash
# Script pour forcer le push de data/pins_ideas_to_fill.csv systématiquement sur Git (Débogage)

# Garde CSV
CSV_PATH="data/pins_ideas_to_fill.csv"
CSV_HEADER='"search_link_amazon","amazon_product_url","title","overlay_text","description","niche","french_hint","image_description_for_llm"'
if [ ! -s "$CSV_PATH" ]; then
  echo "📣  CSV absent ou vide — création..."
  echo "$CSV_HEADER" > "$CSV_PATH"
fi

# Correction typo [LIEN_AFFILIARE] → [LIEN_AFFILIATE]
if grep -q 'LIEN_AFFILIARE' "$CSV_PATH" 2>/dev/null; then
  sed -i '' 's/LIEN_AFFILIARE/LIEN_AFFILIATE/g' "$CSV_PATH"
  echo "✅ Typo [LIEN_AFFILIARE] corrigée dans le CSV."
fi

echo "🚀 Forçage du push de data/pins_ideas_to_fill.csv vers GitHub..."
git add data/pins_ideas_to_fill.csv
git commit -m "fix(data): force push manual csv updates for debugging"
git push

echo "✅ Push forcé terminé. Les actions Github vont être déclenchées si le cron le demande."
