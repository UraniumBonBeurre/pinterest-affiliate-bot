#!/usr/bin/env python3
import os
import csv
import json
import re
import urllib.parse
from huggingface_hub import InferenceClient
from config import HF_TOKEN, DATA_DIR
from utils import now_ts

def extract_json(text: str) -> dict:
    match = re.search(r'```json\s*(.*?)\s*```', text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except:
            pass
    try:
        return json.loads(text)
    except Exception as e:
        print(f"Failed to parse JSON: {e}")
        return {"pins": []}

def generate_ideas():
    print("==================================================")
    print("🤖 GÉNÉRATEUR D'IDÉES DE PINS AVEC DEEPSEEK-V3")
    print("==================================================\n")
    
    if not HF_TOKEN:
        print("❌ Erreur: HF_TOKEN n'est pas configurée dans le fichier .env")
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

    print(f"\n⏳ Génération de {count} idées pour la niche '{niche}' en cours via DeepSeek-V3 sur Hugging Face...")
    
    client = InferenceClient(api_key=HF_TOKEN)
    
    system_prompt = """You are a Pinterest expert and Amazon affiliate. You output ONLY valid JSON.
Your JSON must be an object with a 'pins' array containing objects with the following keys:
- slug: unique identifier string (e.g. pin_word_001)
- title: Catchy SEO title string (max 90 chars)
- overlay_text: Very short punchy text string for the image overlay (2-5 words)
- description: Engaging description string (200-300 chars) ending exactly with "[LIEN_AFFILIATE]"
- niche: Category string
- keywords: 5-10 relevant keywords string, comma separated
"""
    
    user_prompt = f"Génère {count} idées d'épingles Pinterest très attractives pour la niche : \"{niche}\". Ne retourne strictement QUE le JSON valide, sans aucune autre explication."

    try:
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        
        response = client.chat_completion(
            model="deepseek-ai/DeepSeek-V3",
            messages=messages,
            max_tokens=4000
        )
        
        reply_content = response.choices[0].message.content
        data = extract_json(reply_content)
        pins = data.get("pins", [])
        
        if not pins:
            print("❌ Aucune idée générée ou format de réponse invalide.")
            print("Réponse brute reçue :", reply_content)
            return
            
        output_file = DATA_DIR / "pins_ideas_to_fill.csv"
        file_exists = os.path.isfile(output_file)
        
        with open(output_file, 'a', encoding='utf-8', newline='') as f:
            fieldnames = ["slug", "title", "overlay_text", "description", "search_link_amazon", "amazon_product_url", "asin", "niche", "keywords"]
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            if not file_exists:
                writer.writeheader()
            
            for pin in pins:
                search_query = pin.get("title", "")
                encoded_query = urllib.parse.quote_plus(search_query)
                search_link = f"https://www.amazon.fr/s?k={encoded_query}"
                
                row = {
                    "slug": pin.get("slug", ""),
                    "title": pin.get("title", ""),
                    "overlay_text": pin.get("overlay_text", ""),
                    "description": pin.get("description", ""),
                    "search_link_amazon": search_link,
                    "amazon_product_url": "", # Empty for manual fill
                    "asin": "", # Empty for manual fill
                    "niche": pin.get("niche", ""),
                    "keywords": pin.get("keywords", "")
                }
                writer.writerow(row)
                
        print("\n✅ GÉNÉRATION TERMINÉE ! 🎉")
        print(f"📁 Fichier mis à jour avec {len(pins)} nouvelles lignes : {output_file}")
        
    except Exception as e:
        print(f"\n❌ Erreur API : {e}")

if __name__ == "__main__":
    generate_ideas()
