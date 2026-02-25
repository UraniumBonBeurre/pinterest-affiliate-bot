import os
import random
import logging
import pandas as pd
from config import PINS_PER_DAY, IMAGES_DIR, DATA_DIR
from generate_images import generate_interior_image
from prompts import POSITIVE_PROMPT
from publish_pins import publish_single_pin

# Add GH Actions output format
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

def main():
    logging.info("Starting Pinterest Deco Autopilot")
    
    csv_path = DATA_DIR / "pins_ideas_to_fill.csv"
    if not csv_path.exists():
        logging.error(f"CSV database not found at {csv_path}. Exiting.")
        return
        
    try:
        df = pd.read_csv(csv_path)
    except Exception as e:
        logging.error(f"Failed to read CSV: {e}")
        return

    # Filter rows that actually have an ASIN filled by the user
    # NaN check or empty string check
    available_mask = df['asin'].notna() & (df['asin'].str.strip() != "")
    available_df = df[available_mask]
    
    available_count = len(available_df)
    total_count = len(df)
    
    logging.info(f"Loaded CSV: {total_count} total ideas, {available_count} with ASIN configured and ready.")
    
    # 1. Health check (Trigger GH issue if < 50 ASINs remaining)
    is_low = available_count < 50
    if is_low:
        if "GITHUB_OUTPUT" in os.environ:
            with open(os.environ["GITHUB_OUTPUT"], "a") as env_file:
                env_file.write("pool_low=true\n")
        logging.warning(f"⚠️ ASIN Pool is running low ({available_count} < 50)!")
    else:
        if "GITHUB_OUTPUT" in os.environ:
            with open(os.environ["GITHUB_OUTPUT"], "a") as env_file:
                env_file.write("pool_low=false\n")
                
    if available_count == 0:
        logging.error("No more ASINs available. Exiting.")
        return
        
    # 2. Pick N random products
    sample_size = min(PINS_PER_DAY, available_count)
    chosen_df = available_df.sample(n=sample_size)
    
    logging.info(f"Selected {sample_size} products for today's run.")
    
    generated_count = 0
    indexes_to_drop = []
    
    for idx, row in chosen_df.iterrows():
        asin = str(row.get("asin")).strip()
        title = str(row.get("title")).strip()
        logging.info(f"Processing ASIN: {asin} - {title[:30]}...")
        
        try:
            # 3. Generate Image
            image_path = str(IMAGES_DIR / f"autopilot_{asin}.jpg")
            prompt = POSITIVE_PROMPT.format(subject=title)
            generate_interior_image(prompt, image_path, None)
            
            # 4. Publish
            # Using the specific title and asin mapping to generate link internal to publish_single_pin
            publish_single_pin(image_path, title, asin)
            
            # 5. Mark for deletion
            indexes_to_drop.append(idx)
            generated_count += 1
            
        except Exception as e:
            logging.error(f"Failed to process ASIN {asin}: {e}")
            continue
            
    # 6. Delete processed rows and save
    if indexes_to_drop:
        df = df.drop(indexes_to_drop)
        df.to_csv(csv_path, index=False)
        logging.info(f"Deleted {len(indexes_to_drop)} successfully published products from CSV.")
        
    logging.info(f"Autopilot finished. Successfully generated and published {generated_count}/{sample_size} pins.")

if __name__ == "__main__":
    main()
