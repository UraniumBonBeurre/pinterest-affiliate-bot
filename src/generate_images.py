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
    Generates a single image via HF, optionally relying on FLUX text generation, and saves it.
    Used by the autopilot workflow.
    """
    if overlay_text and overlay_text.strip() and str(overlay_text).lower() != "nan":
        text_instruction = f'big bold text overlay in the upper third in modern sans-serif font (white with subtle black shadow, very readable, large size):\\n"{overlay_text}",'
    else:
        text_instruction = "no text, no watermark,"

    prompt = f"""
    Photorealistic vertical Pinterest image 1000x1500, modern minimalist home interior 2026, soft natural daylight, realistic textures wood linen plants, cozy neutral palette beige white sage, clean aesthetic, subject: {subject},
    {text_instruction}
    professional interior photography, highly detailed 8K, no people, sharp focus, aesthetic highly pinnable
    """
    
    base_img = generate_image_hf(prompt)
    # Resize to expected Pinterest 2:3 ratio (If HF couldn't honor it exactly)
    final_img = base_img.resize((1000, 1500), Image.Resampling.LANCZOS)
        
    final_img.save(image_path, "JPEG", quality=90)
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
