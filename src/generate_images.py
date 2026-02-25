#!/usr/bin/env python3
import warnings
warnings.filterwarnings("ignore", category=UserWarning, module="PIL")

import os
import base64
import pandas as pd
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont
import requests
import time
from tenacity import retry, wait_fixed, stop_after_attempt, retry_if_exception_type
from config import HF_TOKEN, DATA_DIR, IMAGES_DIR, BASE_DIR

class GenerationError(Exception):
    pass

@retry(stop=stop_after_attempt(5), wait=wait_fixed(15), retry=retry_if_exception_type(GenerationError))
def generate_image_hf(prompt: str) -> Image.Image:
    """
    Generate an image using Hugging Face Inference API (Flux.1-schnell).
    """
    if not HF_TOKEN:
        raise GenerationError("HF_TOKEN is not set in .env")
        
    API_URL = "https://router.huggingface.co/hf-inference/models/black-forest-labs/FLUX.1-schnell"
    headers = {"Authorization": f"Bearer {HF_TOKEN}"}
    
    # Exact user specified prompt architecture
    payload = {
        "inputs": prompt,
        "parameters": {
            "negative_prompt": "cartoon, anime, illustration, painting, blurry, low quality, deformed, ugly, extra objects, text, watermark, people, faces, animals, fantasy, overexposed, underexposed",
            "width": 1000,
            "height": 1500
        }
    }
    
    try:
        # Add explicit timeout so it doesn't hang forever if HF is stuck
        response = requests.post(API_URL, headers=headers, json=payload, timeout=60)
        
        # Check if model is still loading (commonly returns 503)
        if response.status_code == 503:
            print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] HF API 503: Model loading. {response.text}")
            raise GenerationError(f"Model is loading, retrying... {response.json()}")
            
        if response.status_code != 200:
            print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] HF API Error {response.status_code}: {response.text}")
            raise GenerationError(f"HF API Error {response.status_code}: {response.text}")
            
        image = Image.open(BytesIO(response.content))
        return image.convert("RGB")
    except Exception as e:
        if isinstance(e, GenerationError):
            raise
        raise GenerationError(f"HF Request Error: {e}")

def add_text_overlay(image_path: str, texte: str, output_path: str = None) -> str:
    """
    Ajoute un texte overlay Pinterest stylisé à la main (Caveat).
    """
    if output_path is None:
        output_path = image_path.replace(".png", "_final.png")
        if output_path == image_path:
             output_path = image_path.replace(".jpg", "_final.jpg")
    
    img = Image.open(image_path).convert("RGB")
    draw = ImageDraw.Draw(img)
    
    # On cherche dynamiquement la taille de police idéale (très grande pour le cursif)
    font_path = BASE_DIR / "assets" / "fonts" / "Kalam-Bold.ttf"
    
    max_font_size = 350
    min_font_size = 150
    margin = 120 # Marge totale (gauche + droite)
    max_width = img.width - margin
    
    font_size = max_font_size
    font = None
    lines = []
    
    # Wrap text and dynamically reduce font size if even the longest word doesn't fit
    words = str(texte).split()
    while font_size >= min_font_size:
        try:
            font = ImageFont.truetype(str(font_path), font_size)
        except Exception as e:
            print(f"🚨 WARNING: Failed to load font {font_path} (Error: {e})")
            try:
                font = ImageFont.truetype("arialbd.ttf", font_size)
            except:
                print("🚨 CRITICAL WARNING: Falling back to 10px binary default font! Text will be unreadable.")
                font = ImageFont.load_default()
                
        # Tentative de wrap avec cette taille
        lines = []
        current_line = []
        word_too_long = False
        
        for word in words:
            if draw.textlength(word, font=font) > max_width:
                word_too_long = True
                break
                
            current_line.append(word)
            line_w = draw.textlength(" ".join(current_line), font=font)
            if line_w > max_width:
                current_line.pop()
                if current_line:
                    lines.append(" ".join(current_line))
                current_line = [word]
                
        if word_too_long:
            font_size -= 20
            continue
            
        if current_line:
            lines.append(" ".join(current_line))
            
        break # Si on arrive ici, le wrap a fonctionné avec cette taille
        
    line_h = int(font_size * 1.1)
    total_h = len(lines) * line_h
    
    y = max(0, (img.height - total_h) // 2) - 50 # Centrage + léger ajustement optique
    
    for line in lines:
        line_w = draw.textlength(line, font=font)
        x = (img.width - line_w) // 2
        
        # Contour léger (stroke) pour lisibilité sans casser les liaisons
        stroke_color = (0, 0, 0, 180) # Légèrement plus opaque
        stroke_w = 6 # Épaisseur augmentée
        for dx in range(-stroke_w, stroke_w + 1, 2):
            for dy in range(-stroke_w, stroke_w + 1, 2):
                if dx != 0 or dy != 0:
                    draw.text((x + dx, y + dy), line, font=font, fill=stroke_color)
                        
        # Ombre portée de profondeur
        shadow = (0, 0, 0, 240)
        draw.text((x+8, y+8), line, font=font, fill=shadow)

        # Texte au premier plan (dessiné d'un seul bloc pour garder l'effet cursif lié intact)
        draw.text((x, y), line, font=font, fill=(255, 255, 255))
        
        y += line_h
    
    img.save(output_path, "JPEG", quality=98, optimize=True)
    return output_path

# Configuration Together AI
TOGETHER_API_URL = "https://api.together.xyz/v1/images/generations"

@retry(stop=stop_after_attempt(3), wait=wait_fixed(10), retry=retry_if_exception_type(GenerationError))
def generate_image_together(prompt: str) -> Image.Image:
    from config import TOGETHER_API_KEY
    if not TOGETHER_API_KEY:
        raise GenerationError("No Together API key found")
        
    headers = {
        "Authorization": f"Bearer {TOGETHER_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "black-forest-labs/FLUX.1-schnell-Free",
        "prompt": prompt,
        "width": 1024,
        "height": 1024, # Together free tier limit
        "steps": 4,
        "n": 1,
        "response_format": "url" # On recupère un URL qu'on va dl
    }
    
    try:
        response = requests.post(TOGETHER_API_URL, headers=headers, json=payload, timeout=60)
        
        if response.status_code != 200:
            raise GenerationError(f"Together API Error: {response.text}")
            
        data = response.json()
        image_url = data['data'][0]['url']
        
        # Télécharger l'image depuis l'url fourni
        img_response = requests.get(image_url, timeout=30)
        img_response.raise_for_status()
        
        image = Image.open(BytesIO(img_response.content))
        return image.convert("RGB")
        
    except Exception as e:
        raise GenerationError(f"Together Request Error: {e}")

def generate_interior_image(subject: str, image_path: str, overlay_text: str = None) -> str:
    """
    Generates a single image via Together (fallback HF), and adds Python PIL overlay.
    Used by the autopilot workflow.
    """
    prompt = f"""
    Photorealistic vertical Pinterest image 1000x1500, {subject}, modern minimalist home interior 2026, soft natural daylight from large window, realistic textures wood linen concrete plants, cozy neutral colors beige white sage green warm wood tones, clean aesthetic composition, highly detailed 8K, professional interior photography style, no people, no text, no watermark, no artifacts, sharp focus, highly pinnable
    """
    
    try:
        print("Tentative de génération avec Together AI...")
        base_img = generate_image_together(prompt)
    except Exception as e:
        print(f"⚠️ Échec Together AI ({e}). Fallback sur Hugging Face...")
        base_img = generate_image_hf(prompt)
        
    # Resize to expected Pinterest 2:3 ratio
    final_img = base_img.resize((1000, 1500), Image.Resampling.LANCZOS)
        
    final_img.save(image_path, "JPEG", quality=90)
    
    if overlay_text and overlay_text.strip() and str(overlay_text).lower() != "nan":
         add_text_overlay(image_path, overlay_text, image_path)
         
    return image_path

def process_batch():
    input_path = DATA_DIR / "pins_input.csv"
    output_csv = DATA_DIR / "pins_ready.csv"
    
    if not input_path.exists():
        print(f"Error: {input_path} not found.")
        return
        
    df = pd.read_csv(input_path)
    results = []
    
    for idx, row in df.iterrows():
        slug = row.get("slug")
        title = row.get("title")
        overlay_text = row.get("overlay_text", "")
        description = row.get("description", "")
        affiliate_url = row.get("affiliate_url", "")
        keywords = row.get("keywords", "")
        
        print(f"[{now_ts()}] Processing {slug}...")
        
        image_path = IMAGES_DIR / f"{slug}.jpg"
        status = "success"
        
        if not image_path.exists():
            try:
                # Prompt tuning for FLUX
                prompt = f"Pinterest style aesthetic product photo, vertical orientation, brightly lit, high quality professional photography, highly realistic, 8k resolution. Subject: {title}"
                generate_interior_image(prompt, str(image_path), str(overlay_text) if pd.notna(overlay_text) else title)
                print(f"[{now_ts()}] -> Saved successfully")
            except Exception as e:
                import tenacity
                if isinstance(e, tenacity.RetryError):
                    e = e.last_attempt.exception()
                print(f"[{now_ts()}] -> Error: {e}")
                status = f"error: {str(e)}"
        else:
            print(f"[{now_ts()}] -> Image already exists, skipping")
        
        results.append({
            "slug": slug,
            "title": title,
            "description": str(description).replace("[LIEN_AFFILIATE]", str(affiliate_url)) if pd.notna(description) else "",
            "affiliate_url": affiliate_url,
            "image_path": str(image_path),
            "keywords": keywords,
            "status": status
        })
        
    df_ready = pd.DataFrame(results)
    df_ready.to_csv(output_csv, index=False)
    print(f"\nBatch processing complete. Wrote to {output_csv}")

if __name__ == "__main__":
    process_batch()
