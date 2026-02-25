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
- overlay_text: ULTRA catchy text for the image overlay. Rules: max 7 words, emotional + immediate benefit, capitalize only important words. Must make people want to click and "see more".
- description: Engaging description string (200-300 chars) ending exactly with "[LIEN_AFFILIATE]"
- niche: Category string
- keywords: 5-10 relevant keywords string, comma separated
"""
    
    batch_size = 15
    batches = [batch_size] * (count // batch_size)
    if count % batch_size > 0:
        batches.append(count % batch_size)

    output_file = DATA_DIR / "pins_ideas_to_fill.csv"
    total_generated = 0
    
    for b_idx, b_count in enumerate(batches):
        print(f"\n🔄 Lot {b_idx+1}/{len(batches)} : Génération de {b_count} idées...")
        user_prompt = f"Génère {b_count} idées d'épingles Pinterest très attractives pour la niche : \"{niche}\". **IMPORTANT : Le contenu généré (titres, textes, descriptions, mots-clés) doit absolument être en ANGLAIS.** Ne retourne strictement QUE le JSON valide, sans aucune autre explication."

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
                print("❌ Aucune idée générée ou format de réponse invalide pour ce lot.")
                print("Réponse brute reçue (tronquée) :", reply_content[:500], "...")
                continue
                
            file_exists = os.path.isfile(output_file)
            
            with open(output_file, 'a', encoding='utf-8', newline='') as f:
                # Reordered fieldnames as requested (removed slug)
                fieldnames = ["search_link_amazon", "amazon_product_url", "title", "overlay_text", "description", "niche", "keywords"]
                writer = csv.DictWriter(f, fieldnames=fieldnames, quoting=csv.QUOTE_ALL)
                if not file_exists:
                    writer.writeheader()
                
                for pin in pins:
                    search_query = pin.get("title", "")
                    encoded_query = urllib.parse.quote_plus(search_query)
                    search_link = f"https://www.amazon.fr/s?k={encoded_query}"
                    
                    row = {
                        "search_link_amazon": search_link,
                        "amazon_product_url": "", # Empty for manual fill
                        "title": pin.get("title", ""),
                        "overlay_text": pin.get("overlay_text", ""),
                        "description": pin.get("description", ""),
                        "niche": pin.get("niche", ""),
                        "keywords": pin.get("keywords", "")
                    }
                    writer.writerow(row)
            
            total_generated += len(pins)
            print(f"✅ {len(pins)} idées enregistrées pour ce lot.")
                    
        except Exception as e:
            print(f"\n❌ Erreur API sur ce lot : {e}")

    print("\n✅ GÉNÉRATION TERMINÉE ! 🎉")
    print(f"📁 Fichier mis à jour avec un total de {total_generated} nouvelles lignes : {output_file}")

if __name__ == "__main__":
    generate_ideas()
