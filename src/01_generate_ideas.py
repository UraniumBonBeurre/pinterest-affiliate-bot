#!/usr/bin/env python3
import os
import csv
import json
import re
import urllib.parse
from huggingface_hub import InferenceClient
from config import HF_TOKEN, DATA_DIR
from utils import now_ts
from niche_selector import pick_niche, mark_used

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

    raw_niche = input(
        "👉 Thème / niche principale ? "
        "(appuyez sur Entrée pour le choix automatique multi-niches intelligent)\n"
        "  ex: bedroom accessories, living room organization, bricolage\n> "
    ).strip()

    count_str = input("👉 Combien d'idées veux-tu générer au total ? (recommandé: 8-12)\n> ")
    count = int(count_str) if count_str.strip().isdigit() else 10

    # ── Sélection des niches ──────────────────────────────────────────
    if raw_niche:
        niches_to_run = [(raw_niche, count)]
        print(f"🎯 Niche manuelle : {raw_niche}")
    else:
        # Prend les 3 meilleures niches saisonnières et répartit les idées
        from niche_selector import pick_niche_multi
        top_niches = pick_niche_multi(n=3, verbose=True)
        # Distribution proportionnelle : +1 pour les niches de tête
        base = count // len(top_niches)
        remainder = count % len(top_niches)
        niches_to_run = [
            (n, base + (1 if i < remainder else 0))
            for i, n in enumerate(top_niches)
        ]
        print(f"\n📊 Répartition : { {n: c for n, c in niches_to_run} }")

    print(f"\n🚀 Génération de {count} idées au total...")

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
**CRITICAL — This text will be printed BIG on the pin image. It must STOP the scroll.**
STRICT RULES:
  • 2–4 words MAXIMUM. Never more. Ever.
  • Must trigger an IMMEDIATE emotional reaction: desire, curiosity, FOMO, or relief.
  • Feel like a secret tip, a satisfying discovery, or a bold promise.
  • Use power words: Got It. Fixed. Done. Finally. Zero. Perfect. Never Again. Yes.
  • Do NOT write a generic label like the category name.
  • Do NOT describe the product literally.
PERFECT EXAMPLES (copy this energy exactly):
  ✓ "Finally. Done."
  ✓ "Never Again."
  ✓ "Want It Now."
  ✓ "Zero Clutter."
  ✓ "This Changes Everything."
  ✓ "Obsessed. Obviously."
  ✓ "That's The One."
  ✓ "My Life, Fixed."
  ✓ "Hidden Gem Found."
  ✓ "Say Yes To This."
BAD EXAMPLES (never do this):
  ✗ "Smart Home Security" (generic category label — nobody will click)
  ✗ "Jewelry Organization" (product description — too bland)
  ✗ "Always Know Who's There" (too long AND too obvious)

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

⚠️ MOST IMPORTANT RULE: The image MUST directly show the ACTUAL PRODUCT being sold.
The product is the HERO of the image. It must be front-and-center and immediately recognizable.
Never generate a generic interior that could match any product.

RULES:
  1. PRODUCT FIRST: Name the specific product explicitly (e.g. "a video doorbell mounted on a front door frame", "a white rotating jewelry organizer tower on a bedroom dresser", "a bamboo shoe rack in an entryway"). This is non-negotiable.
  2. CORRECT SETTING: Place the product in its natural, real-world location (front door → doorbell, bathroom counter → beauty organizer, kitchen counter → spice rack, entryway → shoe rack, etc.). NEVER use a car interior, office, or unrelated generic room.
  3. LIFESTYLE CONTEXT: Show the product in use or beautifully styled in a premium aspirational home interior.
  4. LIGHTING: Soft golden-hour or morning natural daylight, large windows, warm and inviting.
  5. SURFACES: Realistic high-end materials — light oak, linen, ceramic, matte metal, marble.
  6. PALETTE: Warm neutrals — beige, ivory, warm white, sage green, taupe. Avoid cold blues or dark corporate backgrounds.
  7. MOOD: Calm, ordered, luxurious. A scene that makes viewers want to PIN immediately.
  8. TECHNICAL: 8K photorealistic, professional interior photography style, shallow depth of field.
  9. FORBIDDEN: NO people, NO text, NO watermarks, NO car seats, NO dark rooms, NO cluttered chaotic scenes, NO abstract art backgrounds.

PRACTICAL EXAMPLES:
  Product: video doorbell
  ✓ "Photorealistic vertical Pinterest image 1000x1500, a sleek black video doorbell mounted on a light-colored rendered exterior wall beside a modern front door with frosted glass panels. Warm morning sunlight. Clean minimalist porch with a potted plant. 8K photorealistic professional architectural photography. No text, no people."
  ✗ "Photorealistic vertical Pinterest image 1000x1500, a cozy bedroom with soft lighting" (WRONG — must show the actual product)

  Product: rotating jewelry organizer
  ✓ "Photorealistic vertical Pinterest image 1000x1500, a white rotating jewelry tower organizer on a light oak dresser in a bright minimalist bedroom. Earrings, necklaces and bracelets arranged elegantly on it. Morning light through sheer curtains. Warm neutral palette. 8K photorealistic interior photography. No text, no people."
  ✗ "Photorealistic vertical Pinterest image 1000x1500, a luxurious master bedroom" (WRONG — no product visible)

───────────────────────────────────────────
KEY 7 — "french_hint"
3 to 5 French words that describe the product simply so a French speaker can understand what it is at a glance.
Examples:
  English title: "Never Lose Another Screw Again" → french_hint: "Organisateur d'outils roulant"
  English title: "The Bedside Tray That Organizes Your Nightly Routine" → french_hint: "Plateau de chevet en bois"
  English title: "Silicone Lids That Make Food Storage Beautiful" → french_hint: "Couvercles silicone réutilisables"
Never translate the marketing copy literally — just name the PRODUCT in plain French.
"""

    output_file = DATA_DIR / "pins_ideas_to_fill.csv"
    total_generated = 0

    for niche, niche_count in niches_to_run:
        print(f"\n{'='*50}")
        print(f"📦 Niche : {niche} — {niche_count} idées")
        print('='*50)

        batch_size = 10
        batches = [batch_size] * (niche_count // batch_size)
        if niche_count % batch_size > 0:
            batches.append(niche_count % batch_size)

        for b_idx, b_count in enumerate(batches):
            print(f"\n🔄 Batch {b_idx+1}/{len(batches)} → {b_count} idées...")

            user_prompt = f"""Generate {b_count} highly converting Pinterest pin ideas for the niche: "{niche}".

All content (titles, overlay_text, descriptions) must be in **English**.
Focus on premium home accessories and organization products."""

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
                    break
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

                FIELDNAMES = ["search_link_amazon", "amazon_product_url", "title",
                              "overlay_text", "description", "niche",
                              "french_hint", "image_description_for_llm"]

                # Smart header check: auto-migrate if header is outdated
                needs_header = True
                if os.path.isfile(output_file) and os.path.getsize(output_file) > 0:
                    with open(output_file, 'r', encoding='utf-8', newline='') as _fh:
                        existing_header = next(csv.reader(_fh))
                    if existing_header == FIELDNAMES:
                        needs_header = False
                    else:
                        # Old header → migrate all existing rows to new schema
                        print(f"  ⚠️  Header CSV obsolète ({existing_header}) → migration...")
                        with open(output_file, 'r', encoding='utf-8', newline='') as _fr:
                            old_rows = list(csv.reader(_fr))[1:]
                        with open(output_file, 'w', encoding='utf-8', newline='') as _fw:
                            _w = csv.DictWriter(_fw, fieldnames=FIELDNAMES, quoting=csv.QUOTE_ALL)
                            _w.writeheader()
                            for old_row in old_rows:
                                d = {existing_header[i]: (old_row[i] if i < len(old_row) else '') for i in range(len(existing_header))}
                                _w.writerow({fn: d.get(fn, '') for fn in FIELDNAMES})
                        needs_header = False
                        print("  ✅ Migration terminée")

                with open(output_file, 'a', encoding='utf-8', newline='') as f:
                    writer = csv.DictWriter(f, fieldnames=FIELDNAMES, quoting=csv.QUOTE_ALL)
                    if needs_header:
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
                            "description": pin.get("description", "").replace("LIEN_AFFILIARE", "LIEN_AFFILIATE"),
                            "niche": pin.get("niche", niche),
                            "french_hint": pin.get("french_hint", ""),
                            "image_description_for_llm": pin.get("image_description_for_llm", "")
                        }
                        writer.writerow(row)

                total_generated += len(pins)
                print(f"✅ {len(pins)} idées ajoutées")

            except Exception as e:
                print(f"❌ Erreur lors du traitement de la réponse : {e}")

        mark_used(niche)

    print(f"\n🎉 GÉNÉRATION TERMINÉE ! {total_generated} idées générées dans {output_file}")
    if total_generated > 0:
        print("📌 Niches enregistrées pour la rotation.")

    # ── Interleave niches in CSV (évite bloc groupé par niche) ─────────────────
    if len(niches_to_run) > 1 and total_generated > 0:
        try:
            import pandas as pd
            import random as _random
            df_all = pd.read_csv(output_file)
            groups = {n: list(g.index) for n, g in df_all.groupby('niche', sort=False)}
            niches_present = [k for k in groups if groups[k]]
            _random.shuffle(niches_present)
            order = []
            while any(groups[k] for k in niches_present):
                for k in niches_present:
                    if groups[k]:
                        order.append(groups[k].pop(0))
            df_shuffled = df_all.loc[order].reset_index(drop=True)
            df_shuffled.to_csv(output_file, index=False, quoting=__import__('csv').QUOTE_ALL)
            print(f"🔀 Lignes mélangées par niche en round-robin dans {output_file.name}")
        except Exception as e:
            print(f"⚠️  Mélange impossible : {e}")



if __name__ == "__main__":
    generate_ideas()