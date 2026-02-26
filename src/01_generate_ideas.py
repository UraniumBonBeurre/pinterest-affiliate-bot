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
    """Extraction JSON plus robuste"""
    # Essaie d'abord le bloc ```json
    match = re.search(r'```json\s*(.*?)\s*```', text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except:
            pass
    # Essaie le texte brut
    try:
        return json.loads(text)
    except:
        # Dernier recours : cherche le premier { ... }
        match = re.search(r'(\{.*\})', text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(1))
            except:
                pass
    print("❌ Impossible de parser le JSON")
    return {"pins": []}


def generate_ideas():
    print("==================================================")
    print("🤖 GÉNÉRATEUR D'IDÉES PINS OPTIMISÉ - DEEPSEEK-V3")
    print("==================================================\n")
    
    if not HF_TOKEN:
        print("❌ Erreur: HF_TOKEN non configuré dans .env")
        return

    niche = input("👉 Thème / niche principale ? (ex: bedroom accessories, living room organization, cable management...)\n> ").strip()
    if not niche:
        niche = "home accessories and organization"
        print(f"Utilisation par défaut : {niche}")

    count_str = input("👉 Combien d'idées veux-tu générer ? (recommandé: 8-12 par batch)\n> ")
    count = int(count_str) if count_str.strip().isdigit() else 10

    print(f"\n🚀 Génération de {count} idées premium pour '{niche}'...")

    client = InferenceClient(api_key=HF_TOKEN)

    system_prompt = """You are a world-class Pinterest growth hacker and high-converting Amazon affiliate expert in 2026, specialized in home organization, bedroom, living room, desk accessories and smart storage solutions.

You output **ONLY** valid JSON. No explanations, no markdown, no extra text.

The JSON must be an object with a key "pins" containing an array of objects. Each object must have exactly these keys:

- title: Catchy, benefit-driven Pinterest title in English (max 72 characters)
- amazon_search_query: Precise 3-6 word search query optimized for Amazon.fr to find high-quality, visually appealing, well-reviewed products (example: "woven storage baskets beige living room")
- overlay_text: Extremely powerful overlay text. STRICT RULES: 4-6 words MAX, emotional + strong immediate benefit, capitalize only important words. Designed to stop the scroll and drive clicks.
- description: Persuasive, desire-driven description (195-255 characters). Must end exactly with " [LIEN_AFFILIATE]"
- niche: Short and precise category name (examples: "living_room_storage", "bedroom_essentials", "cable_management", "desk_organization", "cozy_lighting", "small_space_solutions", "storage_solutions")
- image_description_for_llm: Extremely detailed prompt for FLUX.1-schnell. Must start with "Photorealistic vertical Pinterest image 1000x1500,". Describe a premium, aspirational home interior scene with soft natural daylight from large windows, realistic high-end textures (wood, linen, wool, ceramic, metal, plants), elegant neutral color palette (beige, warm white, sage green, taupe, light oak), highly detailed 8K, professional interior photography style, no people, no text on image, no watermark, no artifacts, clean minimalist yet warm aesthetic, extremely pinnable and desirable."

Prioritize emotional desire, luxury feel, instant transformation, and visual perfection in every pin.
"""
    output_file = DATA_DIR / "pins_ideas_to_fill.csv"
    total_generated = 0

    # Batch processing
    batch_size = 10
    batches = [batch_size] * (count // batch_size)
    if count % batch_size > 0:
        batches.append(count % batch_size)

    for b_idx, b_count in enumerate(batches):
        print(f"\n🔄 Batch {b_idx+1}/{len(batches)} → {b_count} idées...")

        user_prompt = f"""Generate {b_count} highly converting Pinterest pin ideas for the niche: "{niche}".

All content (titles, overlay_text, descriptions) must be in **English**.
Focus on premium home accessories and organization products."""

        try:
            response = client.chat_completion(
                model="deepseek-ai/DeepSeek-V3",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                max_tokens=4500,
                temperature=0.7
            )

            reply_content = response.choices[0].message.content
            data = extract_json(reply_content)
            pins = data.get("pins", [])

            if not pins:
                print("❌ No valid pins in this batch")
                continue

            file_exists = os.path.isfile(output_file)

            with open(output_file, 'a', encoding='utf-8', newline='') as f:
                fieldnames = ["search_link_amazon", "amazon_product_url", "title", "overlay_text", 
                              "description", "niche", "image_description_for_llm"]
                writer = csv.DictWriter(f, fieldnames=fieldnames, quoting=csv.QUOTE_ALL)
                
                if not file_exists:
                    writer.writeheader()

                for pin in pins:
                    search_query = pin.get("amazon_search_query", "")
                    encoded_query = urllib.parse.quote_plus(search_query)
                    search_link = f"https://www.amazon.fr/s?k={encoded_query}"

                    row = {
                        "search_link_amazon": search_link,
                        "amazon_product_url": "",           # Vide pour remplissage manuel
                        "title": pin.get("title", ""),
                        "overlay_text": pin.get("overlay_text", ""),
                        "description": pin.get("description", ""),
                        "niche": pin.get("niche", ""),
                        "image_description_for_llm": pin.get("image_description_for_llm", "")
                    }
                    writer.writerow(row)

            total_generated += len(pins)
            print(f"✅ {len(pins)} idées ajoutées")

        except Exception as e:
            print(f"❌ Erreur lors du batch : {e}")

    print(f"\n🎉 GÉNÉRATION TERMINÉE ! {total_generated} idées générées dans {output_file}")


if __name__ == "__main__":
    generate_ideas()