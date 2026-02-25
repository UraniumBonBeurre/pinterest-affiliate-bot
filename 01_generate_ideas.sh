#!/bin/bash
# Script interactif pour générer des idées et les envoyer sur Github

echo "🔄 Récupération de la dernière version du fichier (git pull)..."
git pull --autostash --rebase

echo ""
# Lancer le script Python de génération
python src/01_generate_ideas.py

echo ""
echo "📝 ÉTAPE MANUELLE :"
echo "1. Ouvre le fichier 'data/pins_ideas_to_fill.csv'"
echo "2. Clique sur les liens 'search_link_amazon'"
echo "3. Trouve un produit pertinent et copie l'URL entière de la page sur la colonne 'amazon_product_url'"
echo "4. Fais ça pour toutes les nouvelles lignes que tu veux publier."

echo ""
read -p "⏳ Appuie sur [ENTRÉE] UNE FOIS QUE TU AS FINI DE REMPLIR LES URL ET SAUVEGARDÉ LE FICHIER CSV..."

echo "🚀 Poussée des modifications vers GitHub..."
git add data/pins_ideas_to_fill.csv
git commit -m "chore: Add new product urls"
git push

echo "✅ Terminé ! Le CSV est en ligne. Tu peux lancer l'action GitHub manuellement."
