#!/usr/bin/env python3
import sys
from config import PINTEREST_ACCESS_TOKEN, PINTEREST_API_BASE, DATA_DIR
from pinterest_api import PinterestAPI, PinterestAPIException
from utils import save_json

def list_and_save_boards():
    """
    Fetch Pinterest boards and save them to a local JSON cache.
    """
    print("Fetching Pinterest boards...")
    
    try:
        api = PinterestAPI(access_token=PINTEREST_ACCESS_TOKEN, api_base=PINTEREST_API_BASE)
        data = api.list_boards()
        
        boards = data.get('items', [])
        
        if not boards:
            print("No boards found. Please check your account or token permissions.")
            return

        print("\n--- Available Boards ---")
        for board in boards:
            print(f"Name: '{board.get('name')}' | ID: {board.get('id')}")
            
        # Save to cache
        cache_path = DATA_DIR / "boards_cache.json"
        save_json(cache_path, data)
        print(f"\nBoards saved to {cache_path}")
        print("-> Copy the desired Board ID and paste it into your .env under PINTEREST_BOARD_ID")
        
    except PinterestAPIException as e:
        print(f"API Error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    list_and_save_boards()
