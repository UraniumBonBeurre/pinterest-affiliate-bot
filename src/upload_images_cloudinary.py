#!/usr/bin/env python3
import os
import pandas as pd
import cloudinary
import cloudinary.uploader
from config import CLOUDINARY_CLOUD_NAME, CLOUDINARY_API_KEY, CLOUDINARY_API_SECRET, CLOUDINARY_FOLDER, DATA_DIR
from utils import now_ts

def upload_images():
    input_path = DATA_DIR / "pins_ready.csv"
    
    if not input_path.exists():
        print(f"Error: {input_path} not found.")
        return
        
    if not all([CLOUDINARY_CLOUD_NAME, CLOUDINARY_API_KEY, CLOUDINARY_API_SECRET]):
        print("Error: Cloudinary credentials missing in .env")
        return
        
    cloudinary.config(
        cloud_name=CLOUDINARY_CLOUD_NAME,
        api_key=CLOUDINARY_API_KEY,
        api_secret=CLOUDINARY_API_SECRET,
        secure=True
    )
    
    df = pd.read_csv(input_path)
    
    if "image_public_url" not in df.columns:
        df["image_public_url"] = ""
        
    for idx, row in df.iterrows():
        # Only upload if path exists locally and hasn't been uploaded yet
        local_path = row.get("image_path")
        public_url = row.get("image_public_url")
        
        if pd.isna(public_url) or not str(public_url).startswith("http"):
            if pd.notna(local_path) and os.path.exists(local_path):
                print(f"[{now_ts()}] Uploading {local_path} to Cloudinary...")
                try:
                    response = cloudinary.uploader.upload(
                        local_path,
                        folder=CLOUDINARY_FOLDER,
                        public_id=f"pin_{row['slug']}",
                        overwrite=True
                    )
                    url = response.get("secure_url")
                    df.at[idx, "image_public_url"] = url
                    print(f"[{now_ts()}] -> Success: {url}")
                except Exception as e:
                    print(f"[{now_ts()}] -> Failed to upload {row['slug']}: {e}")
            else:
                print(f"[{now_ts()}] Local image not found for {row['slug']}, skipping...")
        else:
            print(f"[{now_ts()}] {row['slug']} already uploaded ({public_url})")
            
    df.to_csv(input_path, index=False)
    print(f"[{now_ts()}] All uploads processed. Saved to {input_path}")

if __name__ == "__main__":
    upload_images()
