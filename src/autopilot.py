import os
import random
import logging
from config import PINS_PER_DAY, IMAGES_DIR
from manage_asin_pool import get_available_asins, mark_as_used, check_pool_health
from generate_images import generate_interior_image
from prompts import POSITIVE_PROMPT
from publish_pins import publish_single_pin

# Add GH Actions output format
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

def main():
    logging.info("Starting Pinterest Deco Autopilot")
    
    # 1. Health check
    is_low = check_pool_health()
    if is_low:
        # We write this to a GitHub Actions output var so the YAML can catch it and create an issue.
        if "GITHUB_OUTPUT" in os.environ:
            with open(os.environ["GITHUB_OUTPUT"], "a") as env_file:
                env_file.write("pool_low=true\n")
        logging.warning("⚠️ ASIN Pool is running low (< 50)!")
    else:
        if "GITHUB_OUTPUT" in os.environ:
            with open(os.environ["GITHUB_OUTPUT"], "a") as env_file:
                env_file.write("pool_low=false\n")
                
    # 2. Get available ASINs
    available = get_available_asins()
    if not available:
        logging.error("No more ASINs available in the pool! Exiting.")
        return
        
    # 3. Pick N random products
    chosen_items = random.sample(available, min(PINS_PER_DAY, len(available)))
    logging.info(f"Selected {len(chosen_items)} products for today's run.")
    
    generated_count = 0
    for item in chosen_items:
        asin = item.get("asin")
        title = item.get("title")
        logging.info(f"Processing ASIN: {asin} - {title[:30]}...")
        
        try:
            # 4. Generate Image
            image_path = str(IMAGES_DIR / f"autopilot_{asin}.jpg")
            prompt = POSITIVE_PROMPT.format(subject=title)
            generate_interior_image(prompt, image_path, None)
            
            # 5. Publish
            publish_single_pin(image_path, title, asin)
            
            # 7. Mark as Used
            mark_as_used(asin)
            generated_count += 1
            
        except Exception as e:
            logging.error(f"Failed to process ASIN {asin}: {e}")
            continue
            
    logging.info(f"Autopilot finished. Successfully generated and published {generated_count}/{len(chosen_items)} pins.")

if __name__ == "__main__":
    main()
