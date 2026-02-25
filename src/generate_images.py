#!/usr/bin/env python3
import warnings
warnings.filterwarnings("ignore", category=UserWarning, module="PIL")

import os
import base64
import pandas as pd
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont
from tenacity import retry, wait_fixed, stop_after_attempt, retry_if_exception_type
from together import Together
from config import TOGETHER_API_KEY, DATA_DIR, IMAGES_DIR, BASE_DIR
from utils import now_ts

# Max 10000x10000 images is supported by PIL
Image.MAX_IMAGE_PIXELS = None

class GenerationError(Exception):
    pass

@retry(stop=stop_after_attempt(3), wait=wait_fixed(5), retry=retry_if_exception_type(GenerationError))
def generate_image_together(prompt: str) -> Image.Image:
    """
    Generate an image using Together AI's Flux model (black-forest-labs/FLUX.1-schnell-Free).
    It usually supports 1024x1024 or 768x1024. We'll request 768x1024.
    """
    if not TOGETHER_API_KEY:
        raise GenerationError("TOGETHER_API_KEY is not set in .env")
        
    client = Together(api_key=TOGETHER_API_KEY)
    
    try:
        response = client.images.generate(
            prompt=prompt,
            model="black-forest-labs/FLUX.1-schnell-Free",
            width=768,
            height=1024,
            steps=4,
            n=1,
            response_format="b64_json"
        )
        
        b64_data = response.data[0].b64_json
        image_bytes = base64.b64decode(b64_data)
        image = Image.open(BytesIO(image_bytes))
        return image.convert("RGB")
    except Exception as e:
        raise GenerationError(f"Together API Error: {e}")

def generate_interior_image(prompt: str, image_path: str, overlay_text: str = None) -> str:
    """
    Generates a single image via Together, applies overlay, and saves it.
    Used by the autopilot workflow.
    """
    base_img = generate_image_together(prompt)
    if overlay_text:
        final_img = add_text_overlay(base_img, str(overlay_text))
    else:
        # Resize to expected Pinterest 2:3 ratio
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
