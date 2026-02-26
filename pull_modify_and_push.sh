#!/usr/bin/env bash
# Script tout-en-un de gestion des idées et d'enrichissement manuel (GUI)

echo "==================================================="
echo "   🚀 Pinterest Autopilot - Workflow Interactif"
echo "==================================================="

echo ""
echo "📥 1. Récupération de la dernière version du fichier (git pull)..."
git pull --autostash --rebase

echo ""
echo "🧠 2. Génération d'idées automatiques (Nouveau lot via IA)..."
if [ -f "venv/bin/python" ]; then
    venv/bin/python src/01_generate_ideas.py
else
    python3 src/01_generate_ideas.py
fi

echo ""
echo "📦 3. Vérification des dépendances interface..."
if [ -f "venv/bin/pip" ]; then
    venv/bin/pip install -q playwright playwright-stealth pandas
    venv/bin/playwright install chromium
else
    pip3 install -q playwright playwright-stealth pandas
    playwright install chromium
fi

echo ""
echo "🎨 4. Lancement de l'interface d'enrichissement (Automatisée)..."
echo "     > Cliquez sur vos liens dans l'interface native."
echo "     > Le navigateur analysera, et SE FERMERA TOUT SEUL dès un clic produit Amazon !"
echo "     > Fermez la fenêtre Mac/PC quand vous avez fini votre lot."

if [ -f "venv/bin/python" ]; then
    venv/bin/python src/01b_enrich_gui.py
else
    python3 src/01b_enrich_gui.py
fi

echo ""
echo "🚀 5. Poussée des nouvelles données enrichies vers GitHub..."
git add data/pins_ideas_to_fill.csv
git commit -m "feat: generation et enrichissement automatique d'URLs"
git push

echo ""
echo "✅ Terminé avec brio ! L'action GitHub d'autopilote continuera de piocher les nouveautés pré-remplies."
