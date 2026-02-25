#!/usr/bin/env python3
import os
import csv
import json
from google import genai
from pydantic import BaseModel
from typing import List
from config import GEMINI_API_KEY, DATA_DIR
from utils import now_ts

class PinIdea(BaseModel):
    slug: str
    title: str
    overlay_text: str
    description: str
    niche: str
    keywords: str

class PinList(BaseModel):
    pins: List[PinIdea]

def generate_ideas():
    print("==================================================")
    print("🤖 GÉNÉRATEUR D'IDÉES DE PINS AVEC GEMINI")
    print("==================================================\n")
    
    import subprocess
    print("🔄 Récupération de la dernière version du fichier (git pull)...")
    subprocess.run(["git", "pull"], check=False)
    
    if not GEMINI_API_KEY:
        print("❌ Erreur: GEMINI_API_KEY n'est pas configurée dans le fichier .env")
        return

    niche = input("👉 Quelle est ta niche ou le thème pour ces produits ? (ex: 'décoration bureau télétravail')\n> ")
    if not niche.strip():
        niche = "décoration d'intérieur astucieuse"
        print(f"Aucune niche saisie. Utilisation par défaut : '{niche}'")

    count_str = input("👉 Combien d'idées veux-tu générer ? (Défaut: 5)\n> ")
    try:
        count = int(count_str.strip()) if count_str.strip() else 5
    except ValueError:
        count = 5
        print("Entrée invalide. Utilisation de 5 par défaut.")

    print(f"\n⏳ Génération de {count} idées pour la niche '{niche}' en cours via Gemini...")
    
    client = genai.Client(api_key=GEMINI_API_KEY)
    
    prompt = f"""
    Agis comme un expert Pinterest et affilié Amazon.
    Génère {count} idées d'épingles Pinterest très attractives pour la niche : "{niche}".
    Chaque épingle fera la promotion d'un produit physique spécifique qu'on peut trouver sur Amazon.
    
    Pour chaque épingle, fournis :
    - slug : identifiant unique (ex: pin_{niche.split()[0][:5]}_001)
    - title : Titre accrocheur optimisé SEO (max 90 caractères)
    - overlay_text : Texte très court et percutant pour écrire SUR l'image (2 à 5 mots max)
    - description : Description d'environ 200-300 caractères qui donne envie d'acheter. Termine TOUJOURS par "[LIEN_AFFILIATE]". Ne mets PAS de guillemets.
    - niche : La catégorie du produit
    - keywords : 5 à 10 mots clés pertinents, séparés par des virgules (ex: accessoire bureau, productivité)
    """

    try:
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt,
            config=dict(
                response_mime_type="application/json",
                response_schema=PinList,
            ),
        )
        
        data = json.loads(response.text)
        pins = data.get("pins", [])
        
        output_file = DATA_DIR / "pins_ideas_to_fill.csv"
        file_exists = os.path.isfile(output_file)
        
        import urllib.parse
        with open(output_file, 'a', encoding='utf-8', newline='') as f:
            fieldnames = ["slug", "title", "overlay_text", "description", "search_link_amazon", "asin", "niche", "keywords"]
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            if not file_exists:
                writer.writeheader()
            
            for pin in pins:
                # Créer un lien de recherche Amazon pertinent basé sur le titre généré
                search_query = pin["title"]
                encoded_query = urllib.parse.quote_plus(search_query)
                search_link = f"https://www.amazon.fr/s?k={encoded_query}"
                
                row = {
                    "slug": pin["slug"],
                    "title": pin["title"],
                    "overlay_text": pin["overlay_text"],
                    "description": pin["description"],
                    "search_link_amazon": search_link,
                    "asin": "", # Colonne vide à remplir par l'utilisateur
                    "niche": pin["niche"],
                    "keywords": pin["keywords"]
                }
                writer.writerow(row)
                
        print("\n✅ GÉNÉRATION TERMINÉE ! 🎉")
        print(f"📁 Fichier mis à jour : {output_file}")
        print("\n📝 ÉTAPE MANUELLE :")
        print("1. Ouvre le fichier 'data/pins_ideas_to_fill.csv'")
        print("2. Clique sur les liens 'search_link_amazon'")
        print("3. Trouve un produit pertinent et copie son 'ASIN'")
        print("4. Colle cet ASIN dans la colonne 'asin' pour les nouvelles lignes.")
        
        input("\n⏳ Appuie sur [ENTRÉE] UNE FOIS QUE TU AS FINI DE REMPLIR LES ASIN ET SAUVEGARDÉ LE FICHIER CSV...")
        
        print("\n🚀 Poussée des modifications vers GitHub...")
        subprocess.run(["git", "add", "data/pins_ideas_to_fill.csv"], check=False)
        subprocess.run(["git", "commit", "-m", "chore: Add new product ideas and ASINs"], check=False)
        subprocess.run(["git", "push"], check=False)
        print("\n✅ Terminé ! Le CSV est en ligne. Tu peux lancer l'action GitHub manuellement.")
        
    except Exception as e:
        print(f"\n❌ Erreur lors de l'appel à Gemini : {e}")

if __name__ == "__main__":
    generate_ideas()
