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

def generate_interior_image(subject: str, image_path: str, overlay_text: str = None) -> str:
    """
    Generates a single image via HF, applies overlay, and saves it.
    Used by the autopilot workflow.
    """
    # Use exact prompt requested by user, injecting the specific subject
    prompt = f"Photorealistic vertical Pinterest image 1000x1500px, modern minimalist home interior 2026, soft natural daylight from large window, realistic textures (wood, linen, concrete, plants), cozy neutral colors (beige, white, sage green, warm wood), clean aesthetic composition, highly detailed 8K, professional interior photography style, no people, no text, no watermark, no artifacts, no distortion, sharp focus. Subject: {subject}"
    
    base_img = generate_image_hf(prompt)
    if overlay_text:
        final_img = add_text_overlay(base_img, str(overlay_text))
    else:
        # Resize to expected Pinterest 2:3 ratio (If HF couldn't honor it exactly)
        final_img = base_img.resize((1000, 1500), Image.Resampling.LANCZOS)
        
    final_img.save(image_path, "JPEG", quality=90)
    return image_path
    
def get_font(size: int) -> ImageFont.FreeTypeFont:
    """Load our custom downloaded font (Anton-Regular)"""
    font_path = BASE_DIR / "assets" / "fonts" / "Anton-Regular.ttf"
    try:
        return ImageFont.truetype(str(font_path), size)
    except IOError:
        print("Warning: Custom font not found. Using default.")
        return ImageFont.load_default()

def add_text_overlay(base_img: Image.Image, text: str) -> Image.Image:
    """
    Add a large, bold text overlay to the center of the image.
    Resizes/crops image to target 1000x1500 exactly.
    """
    # 1. Resize/Crop to 1000x1500 (2:3 Pinterest Ratio)
    w, h = base_img.size
    target_ratio = 2 / 3
    current_ratio = w / h
    
    if current_ratio > target_ratio:
        # Too wide, crop width
        new_w = int(h * target_ratio)
        left = (w - new_w) // 2
        base_img = base_img.crop((left, 0, left + new_w, h))
    elif current_ratio < target_ratio:
        # Too tall, crop height
        new_h = int(w / target_ratio)
        top = (h - new_h) // 2
        base_img = base_img.crop((0, top, w, top + new_h))
        
    img = base_img.resize((1000, 1500), Image.Resampling.LANCZOS)
    draw = ImageDraw.Draw(img)
    
    # 2. Add Text Overlay
    font_size = 140
    font = get_font(font_size)
    
    width, height = img.size
    words = str(text).upper().split()
    lines = []
    current_line = []
    
    # Text Wrap
    for word in words:
        current_line.append(word)
        line_w = draw.textlength(" ".join(current_line), font=font)
        if line_w > width - 100:  # 50px padding on each side
            current_line.pop()
            lines.append(" ".join(current_line))
            current_line = [word]
    if current_line:
        lines.append(" ".join(current_line))
        
    line_h = font_size + 10 # approximate line height
    
    # Draw Background Box for Readability
    total_text_h = len(lines) * (line_h + 10)
    box_y1 = height // 2 - (total_text_h // 2) - 60
    box_y2 = height // 2 + (total_text_h // 2) + 60
    
    overlay = Image.new('RGBA', img.size, (255, 255, 255, 0))
    d = ImageDraw.Draw(overlay)
    # Give it a nice dark cinematic background band
    d.rectangle([(0, box_y1), (width, box_y2)], fill=(0, 0, 0, 180))
    
    img = img.convert('RGBA')
    img = Image.alpha_composite(img, overlay)
    draw = ImageDraw.Draw(img)
    
    # Draw Text
    y_text = box_y1 + 50
    for line in lines:
        line_w = draw.textlength(line, font=font)
        x_text = (width - line_w) // 2
        
        # Draw nice drop shadow
        draw.text((x_text + 6, y_text + 6), line, font=font, fill=(0, 0, 0, 255))
        draw.text((x_text + 3, y_text + 3), line, font=font, fill=(0, 0, 0, 150))
        # Draw main text, maybe a slight off-white/yellow for punch
        draw.text((x_text, y_text), line, font=font, fill=(255, 248, 230, 255))
        y_text += line_h + 10
        
    return img.convert('RGB')

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
