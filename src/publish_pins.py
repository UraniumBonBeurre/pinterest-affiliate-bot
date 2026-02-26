import os
import boto3
import pandas as pd
from config import DATA_DIR, PINTEREST_ACCESS_TOKEN, PINTEREST_API_BASE, PINTEREST_BOARD_ID, PUBLISH_DRY_RUN, AMAZON_ASSOCIATE_TAG, R2_ACCOUNT_ID, R2_ACCESS_KEY_ID, R2_SECRET_ACCESS_KEY, R2_BUCKET_NAME, R2_PUBLIC_HASH
from pinterest_api import PinterestAPI, PinterestAPIException
from utils import now_ts

def get_amz_link(asin: str) -> str:
    asin = str(asin).strip()
    return f"https://www.amazon.fr/dp/{asin}?tag={AMAZON_ASSOCIATE_TAG}&linkCode=ogi"

def upload_to_r2(local_image_path: str) -> str:
    """Upload image to Cloudflare R2 and return the public URL"""
    if not all([R2_ACCOUNT_ID, R2_ACCESS_KEY_ID, R2_SECRET_ACCESS_KEY, R2_BUCKET_NAME, R2_PUBLIC_HASH]):
        raise Exception("Missing R2 credentials in environment variables.")
        
    endpoint_url = f"https://{R2_ACCOUNT_ID}.r2.cloudflarestorage.com"
    
    from botocore.config import Config
    s3 = boto3.client('s3',
        endpoint_url=endpoint_url,
        aws_access_key_id=R2_ACCESS_KEY_ID,
        aws_secret_access_key=R2_SECRET_ACCESS_KEY,
        config=Config(signature_version='s3v4'),
        region_name="auto"
    )
    
    file_name = os.path.basename(local_image_path)
    
    # Upload the file
    s3.upload_file(local_image_path, R2_BUCKET_NAME, file_name, ExtraArgs={"ContentType": "image/jpeg"})
    
    # Construct the public URL using the dev hash
    # Example format: https://pub-[hash].r2.dev/[file_name]
    public_url = f"https://pub-{R2_PUBLIC_HASH}.r2.dev/{file_name}"
    
    return public_url

def publish_single_pin(local_image_path: str, title: str, affiliate_link: str, description: str = None) -> bool:
    """
    1. Upload image to Cloudflare R2
    2. Delete local image to save space
    3. Publish to Pinterest with the provided affiliate_link
    Used primarily by the Autopilot functionality.
    """
    print(f"[{now_ts()}] Uploading to Cloudflare R2...")
    try:
        image_url = upload_to_r2(local_image_path)
        print(f"[{now_ts()}] -> Image uploaded successfully: {image_url}")
        
        # Delete local image to save runner space
        if os.path.exists(local_image_path):
            os.remove(local_image_path)
            print(f"[{now_ts()}] -> Local image deleted.")
            
    except Exception as e:
        print(f"[{now_ts()}] R2 API Error: {e}")
        raise
        
    print(f"[{now_ts()}] Publishing to Pinterest Board {PINTEREST_BOARD_ID}...")
    api = PinterestAPI(access_token=PINTEREST_ACCESS_TOKEN, api_base=PINTEREST_API_BASE)

    # Build final description: replace [LIEN_AFFILIATE] placeholder if present
    if description and description not in ("", "nan"):
        final_description = description.replace("[LIEN_AFFILIATE]", affiliate_link)
    else:
        # Fallback generic description
        final_description = f"Découvrez cette idée déco premium : {title}. 🛒 Voir sur Amazon → {affiliate_link}"
    
    if PUBLISH_DRY_RUN:
        print(f"DRY RUN: Would publish '{title}' -> {affiliate_link}")
        print(f"Image used: {image_url}")
        print(f"Description (first 120 chars): {final_description[:120]}")
        return True
    else:
        try:
            res = api.create_pin(
                board_id=PINTEREST_BOARD_ID,
                title=title,
                description=final_description,
                link=affiliate_link,
                image_public_url=image_url
            )
            pin_id = res.get("id")
            print(f"[{now_ts()}] ✅ Pinterest Publish Success! Pin ID: {pin_id}")
            return True
        except PinterestAPIException as e:
            print(f"[{now_ts()}] Pinterest API Error: {e}")
            raise

            
def publish_batch():
    input_path = DATA_DIR / "pins_ready.csv"
    
    if not input_path.exists():
        print(f"Error: {input_path} not found.")
        return
        
    if not PINTEREST_ACCESS_TOKEN or not PINTEREST_BOARD_ID:
        print("Error: Pinterest Credentials or Board ID missing in .env")
        return
        
    print(f"[{now_ts()}] Starting publisher (DRY_RUN={PUBLISH_DRY_RUN}) targeting Board={PINTEREST_BOARD_ID}")
    
    df = pd.read_csv(input_path)
    api = PinterestAPI(access_token=PINTEREST_ACCESS_TOKEN, api_base=PINTEREST_API_BASE)
    
    if "publish_status" not in df.columns:
        df["publish_status"] = "pending"
    if "pinterest_pin_id" not in df.columns:
        df["pinterest_pin_id"] = ""
        
    for idx, row in df.iterrows():
        status = row.get("publish_status")
        
        if status in ["published", "dry_run_ok"]:
            print(f"[{now_ts()}] Skipping '{row.get('title', f'Row {idx}')}' (Status: {status})")
            continue
            
        title = row.get("title", "")
        desc = row.get("description", "")
        link = row.get("affiliate_url", "")
        image_url = row.get("image_public_url", "")
        
        if pd.isna(image_url) or not str(image_url).startswith("http"):
            print(f"[{now_ts()}] Missing or invalid image_public_url for '{title}', skipping.")
            df.at[idx, "publish_status"] = "error: no public image"
            continue
            
        print(f"[{now_ts()}] Publishing '{title}'...")
        
        try:
            if PUBLISH_DRY_RUN:
                print(f"DRY RUN: Would publish '{title}' to {PINTEREST_BOARD_ID}")
                print(f"Image: {image_url}")
                print(f"Link: {link}")
                df.at[idx, "publish_status"] = "dry_run_ok"
            else:
                response = api.create_pin(
                    board_id=PINTEREST_BOARD_ID,
                    title=title,
                    description=desc,
                    link=link,
                    image_public_url=image_url
                )
                pin_id = response.get("id")
                print(f"[{now_ts()}] -> Success! Pin ID: {pin_id}")
                df.at[idx, "publish_status"] = "published"
                df.at[idx, "pinterest_pin_id"] = pin_id
                
            # Incremental save to not lose progress on failure
            df.to_csv(input_path, index=False)
            
        except PinterestAPIException as e:
            print(f"[{now_ts()}] -> Error API: {e}")
            df.at[idx, "publish_status"] = f"error: {str(e)[:50]}"
            df.to_csv(input_path, index=False)
            
    print(f"[{now_ts()}] Publication process complete.")

if __name__ == "__main__":
    publish_batch()
