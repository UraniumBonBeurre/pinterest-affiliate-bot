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
    
    if not GEMINI_API_KEY:
        print("❌ Erreur: GEMINI_API_KEY n'est pas configurée dans le fichier .env")
        return

    niche = input("👉 Quelle est ta niche ou le thème pour ces 10 produits ? (ex: 'décoration bureau télétravail')\n> ")
    if not niche.strip():
        niche = "décoration d'intérieur astucieuse et pas chère"
        print(f"Aucune niche saisie. Utilisation par défaut : '{niche}'")

    print(f"\n⏳ Génération de 10 idées pour la niche '{niche}' en cours via Gemini...")
    
    client = genai.Client(api_key=GEMINI_API_KEY)
    
    prompt = f"""
    Agis comme un expert Pinterest et affilié Amazon.
    Génère 10 idées d'épingles Pinterest très attractives pour la niche : "{niche}".
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
        
        with open(output_file, 'w', encoding='utf-8', newline='') as f:
            fieldnames = ["slug", "title", "overlay_text", "description", "asin", "niche", "keywords"]
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            
            for pin in pins:
                row = {
                    "slug": pin["slug"],
                    "title": pin["title"],
                    "overlay_text": pin["overlay_text"],
                    "description": pin["description"],
                    "asin": "", # Colonne vide à remplir par l'utilisateur
                    "niche": pin["niche"],
                    "keywords": pin["keywords"]
                }
                writer.writerow(row)
                
        print("\n✅ GÉNÉRATION TERMINÉE ! 🎉")
        print(f"📁 Fichier créé : {output_file}")
        print("\n📝 PROCHAINE ÉTAPE :")
        print("1. Ouvre le fichier 'data/pins_ideas_to_fill.csv'")
        print("2. Cherche chaque produit sur Amazon")
        print("3. Copie l'ASIN (10 caractères, ex: B0CXYZ1234) dans la colonne 'asin'")
        print("4. Lance ensuite : python src/02_enrich_links.py")
        
    except Exception as e:
        print(f"\n❌ Erreur lors de l'appel à Gemini : {e}")

if __name__ == "__main__":
    generate_ideas()
