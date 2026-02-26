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
    
    # 1. Dynamic Font Size and Selection
    text_len = len(str(texte))
    if text_len < 20:
        font_size = 130
        font_name = "Caveat-Bold.ttf"
    elif text_len < 40:
        font_size = 115
        font_name = "Caveat-Bold.ttf"
    else:
        font_size = 95
        font_name = "Caveat-Regular.ttf"

    try:
        font_path = BASE_DIR / "assets" / "fonts" / font_name
        font = ImageFont.truetype(str(font_path), font_size)
    except:
        try:
           font = ImageFont.truetype("arialbd.ttf", font_size)
        except:
           font = ImageFont.load_default()
    
    # Wrap text
    words = str(texte).upper().split()
    lines = []
    current_line = []
    
    # 2. Add padding/margins
    margin = 80
    max_width = img.width - (margin * 2)
    
    # We need a dummy draw object just to measure text
    dummy_draw = ImageDraw.Draw(img)
    
    for word in words:
        current_line.append(word)
        line_w = dummy_draw.textlength(" ".join(current_line), font=font)
        if line_w > max_width:
            current_line.pop()
            if current_line:
                lines.append(" ".join(current_line))
            current_line = [word]
    if current_line:
        lines.append(" ".join(current_line))
        
    line_spacing = 1.10
    line_h = int(font_size * line_spacing)
    total_h = len(lines) * line_h
    
    # 3. Vertical Positioning: Top third, dynamic, safety margin
    # Ideal between 12% and 28% height from top. We aim for ~18%
    start_y = int(img.height * 0.18)
    # Ensure it's not too close to top
    if start_y < 120:
        start_y = 120
        
    # 4. Create separate shadow layer
    from PIL import ImageFilter
    shadow_layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    shadow_draw = ImageDraw.Draw(shadow_layer)
    
    y = start_y
    for line in lines:
        line_w = dummy_draw.textlength(line, font=font)
        x = (img.width - int(line_w)) // 2
        
        # Shadow: offset 5px down/right, black with ~230 opacity
        shadow_draw.text((x + 5, y + 5), line, font=font, fill=(0, 0, 0, 230))
        y += line_h
        
    # Apply Gaussian blur on shadow only
    shadow_layer = shadow_layer.filter(ImageFilter.GaussianBlur(radius=1.5))
    
    # Paste shadow onto image
    img = img.convert("RGBA")
    img = Image.alpha_composite(img, shadow_layer)
    
    # Now draw the main text with stroke
    draw = ImageDraw.Draw(img)
    
    y = start_y
    textColor = (255, 255, 255, 255) # Pure White
    strokeColor = (255, 255, 255, 255) # Pure White stroke as requested: 2-3px
    stroke_w = 2
    
    for line in lines:
        line_w = draw.textlength(line, font=font)
        x = (img.width - int(line_w)) // 2
        
        # Simulate stroke with multiple text drawings around the center
        for dx in range(-stroke_w, stroke_w + 1):
            for dy in range(-stroke_w, stroke_w + 1):
                if dx != 0 or dy != 0:
                    draw.text((x + dx, y + dy), line, font=font, fill=strokeColor)
                    
        # Main Text
        draw.text((x, y), line, font=font, fill=textColor)
        y += line_h
    
    img = img.convert("RGB") # Repasser en RGB pour JPEG
    img.save(output_path, "JPEG", quality=98, optimize=True)
    return output_path

def generate_interior_image(image_description: str, image_path: str, overlay_text: str = None) -> str:
    """
    Generates a single image via HF, and adds Python PIL overlay.
    Used by the autopilot workflow.
    """
    prompt = image_description
    
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
        image_description = row.get("image_description_for_llm", title)
        
        print(f"[{now_ts()}] Processing {slug}...")
        
        image_path = IMAGES_DIR / f"{slug}.jpg"
        status = "success"
        
        if not image_path.exists():
            try:
                # Use the ultra-specific LLM prompt provided in the CSV
                if pd.isna(image_description) or not str(image_description).strip():
                    image_description = f"Pinterest style aesthetic product photo, vertical orientation, brightly lit, high quality professional photography, highly realistic, 8k resolution. Subject: {title}"
                
                generate_interior_image(str(image_description), str(image_path), str(overlay_text) if pd.notna(overlay_text) else title)
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
