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

    system_prompt = """You are an elite Pinterest growth strategist and Amazon affiliate expert with a proven track record of creating viral pins generating 50k+ monthly views. It is 2026. You specialize in home decor, organization, and lifestyle products.

You output **ONLY** valid JSON. No explanations, no markdown preamble, no extra text. Nothing outside the JSON.

The JSON must be: {"pins": [ {...}, {...} ]}

Each pin object must have EXACTLY these 6 keys:

───────────────────────────────────────────
KEY 1 — "title"
Catchy, benefit-driven Pinterest title in English. Max 72 characters.
Style: Aspirational problem/solution. Examples:
  ✓ "Cable Chaos Gone in Seconds"
  ✓ "The Storage Ottomans Your Living Room Needs"
  ✗ "Buy This Cable Organizer Box"

───────────────────────────────────────────
KEY 2 — "amazon_search_query"
A precise 3–6 word search query to find THIS EXACT product on Amazon.fr.

CRITICAL DISAMBIGUATION RULE:
The query must be specific enough that Amazon returns the correct product category.
Add niche context words to remove ambiguity.
Examples of BAD (too generic) vs GOOD (niche-specific) queries:
  ✗ "wooden charging station" → returns phone/tablet chargers
  ✓ "cordless drill battery station workshop" → returns tool chargers
  ✗ "storage box" → returns anything
  ✓ "acrylic sock drawer divider organizer" → returns the right product
  ✗ "magnetic holder" → too vague
  ✓ "magnetic tool strip workshop wall" → correct workshop product
  ✗ "organizer bins" → too generic
  ✓ "small parts hardware screw organizer bins" → exact product

Always include 1-2 words that UNIQUELY IDENTIFY the product category within the niche.


───────────────────────────────────────────
KEY 3 — "overlay_text"
**CRITICAL — This text will be printed BIG on the pin image.**
STRICT RULES:
  • 2–4 words MAXIMUM. No exceptions. Never more.
  • Must be punchy, scroll-stopping, create immediate emotional desire.
  • Use contractions or power words freely.
  • Do NOT write a full sentence.
PERFECT EXAMPLES (copy this style exactly):
  ✓ "Clutter? Solved."
  ✓ "Walls That Work"
  ✓ "Hidden Storage Hack"
  ✓ "Style Meets Order"
  ✓ "Tidy Tech Now"
  ✓ "Wire Mess Fixed"
  ✓ "Space Maximizer"
  ✓ "Cozy Corner Found"
BAD EXAMPLES (never do this):
  ✗ "Transform Your Living Room With Storage"
  ✗ "Great For Organization And Style"

───────────────────────────────────────────
KEY 4 — "description"
A persuasive, conversational Pinterest description in 3 parts, each on its own line:
  Part 1: 1–2 sentences of desire-driven emotional copy. Create FOMO, aspiration, urgency. (max 150 chars)
  Part 2: A clear CTA with an emoji and [LIEN_AFFILIATE] at the end.
    Examples: "🛒 Grab yours here → [LIEN_AFFILIATE]"
              "✨ Find it on Amazon → [LIEN_AFFILIATE]"
              "💡 Link in profile! [LIEN_AFFILIATE]"
              "👇 Shop the look → [LIEN_AFFILIATE]"
  Part 3: Exactly 5 relevant hashtags.
    Examples: "#homedecor #storageideas #homeorganization #livingroomdecor #minimalisthome"

PERFECT EXAMPLE of a complete description:
"Finally, a storage solution that's as stylish as it is practical. These woven baskets transform messy rooms in seconds.
🛒 Grab yours here → [LIEN_AFFILIATE]
#homedecor #livingroomdecor #storageideas #organizedhome #basketdecor"

───────────────────────────────────────────
KEY 5 — "niche"
Short snake_case category. Choose from:
living_room_storage, bedroom_essentials, cable_management, desk_organization,
cozy_lighting, small_space_solutions, bathroom_storage, kitchen_organization,
entryway_decor, outdoor_living

───────────────────────────────────────────
KEY 6 — "image_description_for_llm"
Extremely detailed image generation prompt for FLUX.1-schnell.
MUST start with: "Photorealistic vertical Pinterest image 1000x1500,"
Describe a premium aspirational home interior with:
  • Soft golden-hour or morning natural daylight (large windows)
  • Realistic high-end surfaces: light oak, linen, ceramic, matte metal
  • Warm neutral palette: beige, ivory, warm white, sage green, taupe
  • Product integrated naturally and beautifully into the scene
  • A sense of calm, order, and luxury that makes viewers want to PIN immediately
  • 8K photorealistic, professional interior photography style
  • NO people, NO text, NO watermarks, NO dark rooms, NO cluttered scenes
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

        # Fallback chain: try each model in order until one succeeds
        MODELS = [
            "deepseek-ai/DeepSeek-V3",
            "Qwen/Qwen2.5-72B-Instruct",
            "meta-llama/Llama-3.3-70B-Instruct",
        ]
        response = None
        for model in MODELS:
            try:
                print(f"   🤖 Essai avec {model}...")
                response = client.chat_completion(
                    model=model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    max_tokens=4500,
                    temperature=0.7
                )
                print(f"   ✅ Réponse obtenue via {model}")
                break  # success — stop trying
            except Exception as model_err:
                print(f"   ⚠️  {model} indisponible : {str(model_err)[:120]}")
                continue

        if response is None:
            print("❌ Tous les modèles ont échoué pour ce batch.")
            continue

        try:
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
                        "amazon_product_url": "",
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
            print(f"❌ Erreur lors du traitement de la réponse : {e}")

    print(f"\n🎉 GÉNÉRATION TERMINÉE ! {total_generated} idées générées dans {output_file}")


if __name__ == "__main__":
    generate_ideas()