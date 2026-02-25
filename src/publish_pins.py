import pandas as pd
import cloudinary.uploader
from config import DATA_DIR, PINTEREST_ACCESS_TOKEN, PINTEREST_API_BASE, PINTEREST_BOARD_ID, PUBLISH_DRY_RUN, AMAZON_ASSOCIATE_TAG
from pinterest_api import PinterestAPI, PinterestAPIException
from utils import now_ts

def get_amz_link(asin: str) -> str:
    asin = str(asin).strip()
    return f"https://www.amazon.fr/dp/{asin}?tag={AMAZON_ASSOCIATE_TAG}&linkCode=ogi"

def publish_single_pin(local_image_path: str, title: str, asin: str) -> bool:
    """
    1. Upload image to Cloudinary
    2. Build Amazon Link
    3. Publish to Pinterest
    Used primarily by the Autopilot functionality.
    """
    print(f"[{now_ts()}] Uploading to Cloudinary...")
    try:
        response = cloudinary.uploader.upload(
            local_image_path,
            folder="pinterest_affiliate"
        )
        image_url = response.get('secure_url')
    except Exception as e:
        print(f"[{now_ts()}] Cloudinary API Error: {e}")
        raise
        
    print(f"[{now_ts()}] Publishing to Pinterest Board {PINTEREST_BOARD_ID}...")
    api = PinterestAPI(access_token=PINTEREST_ACCESS_TOKEN, api_base=PINTEREST_API_BASE)
    
    affiliate_url = get_amz_link(asin)
    description = f"Magnifique idée déco hyper réaliste : {title}. Pensez à l'ajouter à vos tableaux d'aménagement intérieur ! [LIEN_AFFILIATE]".replace("[LIEN_AFFILIATE]", affiliate_url)
    
    if PUBLISH_DRY_RUN:
        print(f"DRY RUN: Would publish '{title}' -> {affiliate_url}")
        print(f"Image used: {image_url}")
        return True
    else:
        try:
            res = api.create_pin(
                board_id=PINTEREST_BOARD_ID,
                title=title,
                description=description,
                link=affiliate_url,
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
            print(f"[{now_ts()}] Skipping {row['slug']} (Status: {status})")
            continue
            
        title = row.get("title", "")
        desc = row.get("description", "")
        link = row.get("affiliate_url", "")
        image_url = row.get("image_public_url", "")
        
        if pd.isna(image_url) or not str(image_url).startswith("http"):
            print(f"[{now_ts()}] Missing or invalid image_public_url for {row['slug']}, skipping.")
            df.at[idx, "publish_status"] = "error: no public image"
            continue
            
        print(f"[{now_ts()}] Publishing {row['slug']}...")
        
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
