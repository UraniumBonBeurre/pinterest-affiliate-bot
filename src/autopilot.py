import os
import re
import hashlib
import random
import logging
import pandas as pd
from config import PINS_PER_DAY, IMAGES_DIR, DATA_DIR, AMAZON_ASSOCIATE_TAG
from generate_images import generate_interior_image
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

    # Only publish rows where the user has filled in an amazon_product_url.
    # Rows without amazon_product_url are kept in CSV for later manual enrichment.
    # A row is publishable if it has a product URL OR a search link.
    # We cast to str to avoid .str accessor crashes on NaN/float columns.
    has_product_url = (df['amazon_product_url'].astype(str).str.strip()
                       .replace({'nan': '', 'None': ''}).ne(''))
    has_search_link = (df['search_link_amazon'].astype(str).str.strip()
                       .replace({'nan': '', 'None': ''}).ne(''))
    
    available_mask = has_product_url | has_search_link
    available_df = df[available_mask]
    
    available_count = len(available_df)
    total_count = len(df)
    
    logging.info(f"Loaded CSV: {total_count} total ideas, {available_count} ready to publish.")
    
    # 1. Health check (Trigger GH issue if < 50 URLs remaining)
    is_low = available_count < 50
    if is_low:
        if "GITHUB_OUTPUT" in os.environ:
            with open(os.environ["GITHUB_OUTPUT"], "a") as env_file:
                env_file.write("pool_low=true\n")
        logging.warning(f"⚠️ URL Pool is running low ({available_count} < 50)!")
    else:
        if "GITHUB_OUTPUT" in os.environ:
            with open(os.environ["GITHUB_OUTPUT"], "a") as env_file:
                env_file.write("pool_low=false\n")
                
    if available_count == 0:
        logging.error("No more URLs available. Exiting.")
        return
        
    # 2. Pick N random products
    sample_size = min(PINS_PER_DAY, available_count)
    chosen_df = available_df.sample(n=sample_size)
    
    logging.info(f"Selected {sample_size} products for today's run.")
    
    generated_count = 0
    indexes_to_drop = []
    
    for idx, row in chosen_df.iterrows():
        product_url  = str(row.get("amazon_product_url", "")).strip()
        search_url   = str(row.get("search_link_amazon", "")).strip()
        title        = str(row.get("title", "")).strip()
        overlay_text = str(row.get("overlay_text", "")).strip()
        description  = str(row.get("description", "")).strip()

        # ── Build affiliate link ──────────────────────────────────────────────
        # Priority: amazon_product_url (real product) > search_link_amazon (fallback)
        # If product_url looks like a real product page (contains /dp/), use it directly.
        # Otherwise, try to extract an ASIN and build a clean affiliate URL.
        # If none of that works, use the search URL as the destination.
        asin_match = re.search(r"/([A-Z0-9]{10})(?:[/?]|$)", product_url)
        if asin_match:
            asin = asin_match.group(1)
            affiliate_link = f"https://www.amazon.fr/dp/{asin}?tag={AMAZON_ASSOCIATE_TAG}&linkCode=ogi"
        elif product_url and product_url != "nan":
            # URL present but no clean ASIN — append tag param
            sep = "&" if "?" in product_url else "?"
            affiliate_link = f"{product_url}{sep}tag={AMAZON_ASSOCIATE_TAG}"
        elif search_url and search_url != "nan":
            # Fallback: use the search link
            sep = "&" if "?" in search_url else "?"
            affiliate_link = f"{search_url}{sep}tag={AMAZON_ASSOCIATE_TAG}"
        else:
            logging.error(f"Row {idx} has neither amazon_product_url nor search_link_amazon — skipping.")
            continue

        # ── Unique image ID based on row index (no ASIN needed) ───────────────
        pin_uid = f"{idx:06d}"  # stable, unique per CSV row
        logging.info(f"Processing pin #{pin_uid} - {title[:40]}...")

        try:
            # 3. Generate Image
            image_path = str(IMAGES_DIR / f"autopilot_{pin_uid}.jpg")

            if not overlay_text or overlay_text == "nan":
                overlay_text = title

            generate_interior_image(title, image_path, overlay_text)

            # 4. Publish (pass description + link directly)
            publish_single_pin(
                local_image_path=image_path,
                title=title,
                affiliate_link=affiliate_link,
                description=description if description and description != "nan" else None,
            )

            # 5. Mark for deletion
            indexes_to_drop.append(idx)
            generated_count += 1

        except Exception as e:
            import tenacity
            if isinstance(e, tenacity.RetryError):
                e = e.last_attempt.exception()
            logging.error(f"Failed to process pin #{pin_uid}: {e}")
            continue
            
    # 6. Delete ONLY successfully published rows; keep empty-URL rows for later
    if indexes_to_drop:
        df = df.drop(indexes_to_drop)
        df.to_csv(csv_path, index=False, quoting=__import__('csv').QUOTE_ALL)
        logging.info(f"Deleted {len(indexes_to_drop)} published products from CSV. Empty-URL rows preserved.")
        
    logging.info(f"Autopilot finished. Successfully generated and published {generated_count}/{sample_size} pins.")

if __name__ == "__main__":
    main()
