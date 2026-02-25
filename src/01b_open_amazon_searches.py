#!/usr/bin/env python3
import csv
import webbrowser
import urllib.parse
import time
from config import DATA_DIR
from utils import now_ts

def open_amazon_searches():
    print("==================================================")
    print("🛒 RECHERCHE AMAZON SEMI-AUTOMATISÉE")
    print("==================================================\n")
    
    input_file = DATA_DIR / "pins_ideas_to_fill.csv"
    
    if not input_file.exists():
        print(f"❌ Erreur : Le fichier {input_file} est introuvable.")
        return
        
    try:
        with open(input_file, 'r', encoding='utf-8') as infile:
            reader = csv.DictReader(infile)
            rows = list(reader)
            
        print(f"[{now_ts()}] Ouverture de {len(rows)} onglets de recherche Amazon...")
        print("Note : ils vont s'ouvrir un par un avec une seconde d'intervalle.")
        print("-" * 50)
            
        for i, row in enumerate(rows, 1):
            title = row.get('title', '')
            keywords = row.get('keywords', '')
            
            # On combine le titre (sans les mots vides) et les premiers mots-clés
            # pour faire une recherche pertinente
            search_query = f"{title} {keywords.split(',')[0] if keywords else ''}"
            
            # Encoder pour l'URL
            encoded_query = urllib.parse.quote(search_query)
            amazon_url = f"https://www.amazon.fr/s?k={encoded_query}"
            
            print(f"{i}. 🔍 Ouvre recherche pour : {title[:50]}...")
            webbrowser.open_new_tab(amazon_url)
            
            # Petite pause pour ne pas saturer le navigateur
            time.sleep(1)
            
        print("-" * 50)
        print("\n✅ Tous les onglets ont été ouverts !")
        print("\n📝 PROCHAINE ÉTAPE :")
        print("1. Dans chaque onglet Chrome, clique sur le produit qui te plaît.")
        print("2. Récupère son ASIN (dans l'URL, c'est la suite de 10 caractères après /dp/ : e.g., B0CXYZ1234).")
        print("3. Ouvre le fichier : data/full_products_links.txt (je viens de te le renommer).")
        print("4. Colle les liens complets de tes 10 produits, un par ligne, dans le même ordre.")
        print("5. Lance ensuite : python src/02_enrich_links.py")
        
    except Exception as e:
        print(f"\n❌ Erreur : {e}")

if __name__ == "__main__":
    open_amazon_searches()
