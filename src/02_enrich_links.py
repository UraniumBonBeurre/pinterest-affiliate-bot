#!/usr/bin/env python3
import csv
import re
from config import DATA_DIR, AMAZON_ASSOCIATE_TAG
from utils import now_ts

def extract_asin(url: str) -> str:
    url = str(url).strip()
    if len(url) == 10 and url.isalnum():
        return url
    match = re.search(r'/(?:dp|product|ASIN)/([a-zA-Z0-9]{10})(?:[/?]|$)', url)
    if match:
        return match.group(1)
    return ""

def generate_amazon_link(raw_input: str) -> str:
    asin = extract_asin(raw_input)
    if not asin:
        return ""
    return f"https://www.amazon.fr/dp/{asin}?tag={AMAZON_ASSOCIATE_TAG}&linkCode=ogi"

def enrich_links():
    print("==================================================")
    print("🔗 ENRICHISSEMENT DES LIENS AFFILIÉS AMAZON")
    print("==================================================\n")
    
    # Modification pour lire depuis full_products_links.txt
    asin_file = DATA_DIR / "full_products_links.txt"
    input_file = DATA_DIR / "pins_ideas_to_fill.csv"
    output_file = DATA_DIR / "pins_input.csv"
    
    if not input_file.exists():
        print(f"❌ Erreur : Le fichier {input_file} est introuvable.")
        return
        
    if not asin_file.exists():
        print("❌ Erreur : Le fichier full_products_links.txt est introuvable. J'en déduis que tu n'as pas encore rempli tes liens.")
        return
        
    if not AMAZON_ASSOCIATE_TAG:
        print("⚠️ Attention: AMAZON_ASSOCIATE_TAG n'est pas défini dans le fichier .env")
        print("Les liens seront générés sans tag affilié !")
        
    try:
        # 1. Lire la liste des ASINs
        with open(asin_file, 'r', encoding='utf-8') as f:
            lines = f.read().splitlines()
            
        # Nettoyer les lignes (ignorer commentaires # et lignes vides)
        asins = [line.strip() for line in lines if line.strip() and not line.strip().startswith('#')]
        
        # 2. Lire le CSV généré par Gemini
        with open(input_file, 'r', encoding='utf-8') as infile:
            reader = csv.DictReader(infile)
            rows = list(reader)
            
        if len(asins) != len(rows):
            print(f"⚠️ ATTENTION : Nombre de liens fournis ({len(asins)}) différent du nombre de pins ({len(rows)}).")
            print("Le script va associer ce qu'il peut, mais vérifie ton fichier data/full_products_links.txt !")
            
        valid_rows = []
        
        # 3. Réconcilier et générer les liens
        for i, row in enumerate(rows):
            if i < len(asins):
                current_input = asins[i]
                link = generate_amazon_link(current_input)
                if not link:
                    print(f"⚠️ Impossible d'extraire l'ASIN pour la ligne {i+1} : {current_input}")
                row['affiliate_url'] = link
                if 'asin' in row:
                    del row['asin'] # Au cas où
                valid_rows.append(row)
            else:
                print(f"❌ Pas de lien fourni pour la ligne {i+1} : {row.get('title')}. Ligne ignorée.")

        if not valid_rows:
            print("\n❌ Aucun croisement n'a pu être fait. Arrêt du script.")
            return

        with open(output_file, 'w', encoding='utf-8', newline='') as outfile:
            fieldnames = list(valid_rows[0].keys())
            writer = csv.DictWriter(outfile, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(valid_rows)
            
        print(f"\n✅ TERMINÉ ! {len(valid_rows)} liens affiliés générés à partir du fichier texte.")
        print(f"📁 Fichier prêt pour la publication : {output_file}")
        print("\n🚀 PROCHAINE ÉTAPE :")
        print("Lance la génération des images avec : python src/generate_images.py")
            
    except Exception as e:
        print(f"\n❌ Erreur : {e}")

if __name__ == "__main__":
    enrich_links()
