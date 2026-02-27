#!/bin/bash
# Script pour tester la génération visuelle de FLUX + PIL sur toutes les lignes du CSV

echo "🚀 Lancement de la génération visuelle de test sur l'ensemble du CSV..."
echo "Les images seront sauvegardées dans le dossier output/test_visuals/"

# Activation de l'environnement virtuel si présent
if [ -d "venv" ]; then
    source venv/bin/activate
fi

python3 test_all_visuals.py

echo "✅ Test terminé !"
