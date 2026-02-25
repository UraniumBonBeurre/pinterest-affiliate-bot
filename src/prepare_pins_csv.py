#!/usr/bin/env python3
import pandas as pd
from pathlib import Path
from config import DATA_DIR
from utils import now_ts

def prepare_csv():
    input_path = DATA_DIR / "pins_ready.csv"
    
    if not input_path.exists():
        print(f"Error: {input_path} not found. Run generate_images_hf.py first.")
        return
        
    df = pd.read_csv(input_path)
    print(f"[{now_ts()}] Loaded {len(df)} rows from pins_ready.csv")
    
    required_cols = ["slug", "title", "description", "affiliate_url", "image_path"]
    for col in required_cols:
        if col not in df.columns:
            print(f"[{now_ts()}] Error: Missing required column: {col}")
            return
            
    # Cleaning
    # 1. Ensure "(Lien affilié)" transparency
    def append_transparency(desc, url):
        if pd.isna(desc):
            desc = ""
        desc = str(desc).strip()
        if "lien affilié" not in desc.lower() and pd.notna(url) and str(url).strip():
            desc = f"{desc}\n\n(Lien affilié)"
        return desc
    
    df["description"] = df.apply(lambda row: append_transparency(row["description"], row["affiliate_url"]), axis=1)
    
    # 2. Init publish_status if missing
    if "publish_status" not in df.columns:
        df["publish_status"] = "pending"
        
    # Clean titles (max 100 char limit enforced later, but let's warn or trim)
    df["title"] = df["title"].fillna("").astype(str)
    df["title"] = df["title"].apply(lambda t: t[:100].strip())
    
    # Validating
    for idx, row in df.iterrows():
        if row["status"].startswith("error"):
            print(f"[{now_ts()}] Skipping valid status for {row['slug']} due to generation error")
            df.at[idx, "publish_status"] = "error"
            
    df.to_csv(input_path, index=False)
    print(f"[{now_ts()}] Prepared data saved back to {input_path}")

if __name__ == "__main__":
    prepare_csv()
