import requests
from tenacity import retry, wait_fixed, stop_after_attempt, retry_if_exception_type

class PinterestAPIException(Exception):
    pass

class PinterestAPI:
    """
    A simple client for the Pinterest API v5.
    """
    def __init__(self, access_token: str, api_base: str):
        if not access_token:
            raise ValueError("PINTEREST_ACCESS_TOKEN is missing")
        self.access_token = access_token
        self.api_base = api_base
        self.headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
            "Accept": "application/json"
        }

    @retry(stop=stop_after_attempt(3), wait=wait_fixed(2), retry=retry_if_exception_type(PinterestAPIException))
    def list_boards(self) -> dict:
        """
        List all boards owned by the authenticated user.
        """
        url = f"{self.api_base}/boards"
        response = requests.get(url, headers=self.headers, timeout=15)
        
        if not response.ok:
            raise PinterestAPIException(f"Failed to list boards: {response.status_code} - {response.text}")
        
        return response.json()

    @retry(stop=stop_after_attempt(3), wait=wait_fixed(2), retry=retry_if_exception_type(PinterestAPIException))
    def create_pin(self, board_id: str, title: str, description: str, link: str, image_public_url: str) -> dict:
        """
        Create a Pin on a specific board using a public image URL.
        """
        url = f"{self.api_base}/pins"
        
        payload = {
            "board_id": board_id,
            "title": title[:100],  # Title max length is 100
            "description": description[:500], # Description max length is ~500
            "link": link,
            "media_source": {
                "source_type": "image_url",
                "url": image_public_url
            }
        }
        
        response = requests.post(url, headers=self.headers, json=payload, timeout=20)
        
        if not response.ok:
            raise PinterestAPIException(f"Failed to create pin: {response.status_code} - {response.text}")
            
        return response.json()
