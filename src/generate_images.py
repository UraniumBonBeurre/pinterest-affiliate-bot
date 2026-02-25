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
    
    font_size = 160 # Taille augmentée pour police manuscrite
    try:
        font_path = BASE_DIR / "assets" / "fonts" / "Caveat-Bold.ttf"
        font = ImageFont.truetype(str(font_path), font_size)
    except:
        try:
           font = ImageFont.truetype("arialbd.ttf", font_size)
        except:
           font = ImageFont.load_default()
    
    # Wrap text (pas de uppercase() pour garder le style handwriting)
    words = str(texte).split()
    lines = []
    current_line = []
    
    char_spacing = 8 # Espacement horizontal ajouté (tracking)
    
    for word in words:
        current_line.append(word)
        joined_line = " ".join(current_line)
        line_w = 0
        for char in joined_line:
            line_w += draw.textlength(char, font=font) + char_spacing
        
        if line_w > img.width - 150: # Marges
            current_line.pop()
            lines.append(" ".join(current_line))
            current_line = [word]
    if current_line:
        lines.append(" ".join(current_line))
        
    line_h = int(font_size * 1.5) # Interligne très aéré
    total_h = len(lines) * line_h
    
    y = max(0, (img.height - total_h) // 2)
    
    for line in lines:
        line_w = 0
        for char in line:
            line_w += draw.textlength(char, font=font) + char_spacing
        line_w -= char_spacing # retirer l'espacement du dernier caractère
        
        x = (img.width - line_w) // 2
        
        for char in line:
            cw = draw.textlength(char, font=font)
            
            # Contour léger (stroke) pour lisibilité sans boîte
            stroke_color = (0, 0, 0, 160)
            stroke_w = 3
            for dx in range(-stroke_w, stroke_w + 1, 2):
                for dy in range(-stroke_w, stroke_w + 1, 2):
                    if dx != 0 or dy != 0:
                        draw.text((x + dx, y + dy), char, font=font, fill=stroke_color)
                        
            # Ombre portée de profondeur
            shadow = (0, 0, 0, 220)
            draw.text((x+6, y+6), char, font=font, fill=shadow)
            draw.text((x+4, y+4), char, font=font, fill=shadow)
            draw.text((x+2, y+2), char, font=font, fill=shadow)

            # Texte au premier plan
            draw.text((x, y), char, font=font, fill=(255, 255, 255))
            
            x += cw + char_spacing
            
        y += line_h
    
    img.save(output_path, "JPEG", quality=98, optimize=True)
    return output_path

def generate_interior_image(subject: str, image_path: str, overlay_text: str = None) -> str:
    """
    Generates a single image via HF, and adds Python PIL overlay.
    Used by the autopilot workflow.
    """
    prompt = f"""
    Photorealistic vertical Pinterest image 1000x1500, modern minimalist home interior 2026, soft natural daylight from large window, realistic textures wood linen concrete plants, cozy neutral colors beige white sage green warm wood tones, clean aesthetic composition, highly detailed 8K, professional interior photography style, no people, no text, no watermark, no artifacts, sharp focus, highly pinnable
    """
    
    base_img = generate_image_hf(prompt)
    # Resize to expected Pinterest 2:3 ratio (If HF couldn't honor it exactly)
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
