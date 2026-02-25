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
        response = requests.post(API_URL, headers=headers, json=payload)
        
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
    if output_path is None:
        output_path = image_path.replace(".png", "_with_text.png")
        if output_path == image_path:
             output_path = image_path.replace(".jpg", "_with_text.jpg")
    
    img = Image.open(image_path).convert("RGB")
    draw = ImageDraw.Draw(img)
    
    # Police (utilise une police système ou télécharge "Montserrat-Bold.ttf" dans ton repo)
    try:
        font_path = BASE_DIR / "assets" / "fonts" / "Anton-Regular.ttf"
        font = ImageFont.truetype(str(font_path), 120)
    except:
        try:
           font = ImageFont.truetype("arialbd.ttf", 120)
        except:
           font = ImageFont.load_default()
    
    # Wrap text if it is too wide
    words = str(texte).upper().split()
    lines = []
    current_line = []
    for word in words:
        current_line.append(word)
        line_w = draw.textlength(" ".join(current_line), font=font)
        if line_w > img.width - 100:
            current_line.pop()
            lines.append(" ".join(current_line))
            current_line = [word]
    if current_line:
        lines.append(" ".join(current_line))
        
    line_h = 130 # approximate line height
    total_h = len(lines) * line_h
    
    # Centrage vertical
    start_y = (img.height - total_h) // 2
    
    # Dessiner un fond semi-transparent pour la lisibilité
    max_line_w = max(draw.textlength(line, font=font) for line in lines) if lines else 0
    box_padding_x = 60
    box_padding_y = 60
    
    box_x1 = max(0, (img.width - max_line_w) // 2 - box_padding_x)
    box_y1 = max(0, start_y - box_padding_y)
    box_x2 = min(img.width, (img.width + max_line_w) // 2 + box_padding_x)
    box_y2 = min(img.height, start_y + (len(lines) - 1) * line_h + 120 + box_padding_y)
    
    overlay = Image.new('RGBA', img.size, (255, 255, 255, 0))
    d = ImageDraw.Draw(overlay)
    
    # Fond noir semi-transparent (140/255 d'opacité)
    d.rectangle([box_x1, box_y1, box_x2, box_y2], fill=(0, 0, 0, 140))
    img = img.convert('RGBA')
    img = Image.alpha_composite(img, overlay)
    draw = ImageDraw.Draw(img)
    
    y = start_y
    for line in lines:
        line_w = draw.textlength(line, font=font)
        x = (img.width - line_w) // 2
        
        # Ombre noire douce (2 passes pour effet pro)
        draw.text((x+4, y+4), line, font=font, fill=(0, 0, 0, 180))
        draw.text((x+2, y+2), line, font=font, fill=(0, 0, 0, 220))
        
        # Texte blanc principal
        draw.text((x, y), line, font=font, fill=(255, 255, 255))
        y += line_h
    
    img = img.convert('RGB')
    img.save(output_path, "JPEG", quality=95)
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
