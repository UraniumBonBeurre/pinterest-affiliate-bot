# test_pinterest_post.py
import requests
import json

# Remplace par ton vrai token (celui généré sur developers.pinterest.com)
ACCESS_TOKEN = "pina_AMAXPIQXABZKCAIAGCAIIDX5DGHZVHABACGSP7YL6PYDRFYV2FI46QWOIOK26H5E7CZZGAWZ7YYBN44VVBIORIFBOHP2LPIA"

# Remplace par l'ID de ton board (trouve-le via l'API ou en inspectant l'URL de ton board)
BOARD_ID = "1046101888385957582"   # ← CHANGE ÇA

# Image publique de test (tu peux mettre une URL à toi plus tard)
IMAGE_URL = "https://picsum.photos/1000/1500"  # Image aléatoire 1000x1500

payload = {
    "board_id": BOARD_ID,
    "note": "Pin de test automatique - Grok 2026",
    "link": "https://example.com",  # Lien de destination (peut être ton lien Amazon)
    "alt_text": "Image de test Pinterest",
    "media_source": {
        "source_type": "image_url",
        "url": IMAGE_URL
    }
}

headers = {
    "Authorization": f"Bearer {ACCESS_TOKEN}",
    "Content-Type": "application/json"
}

url = "https://api-sandbox.pinterest.com/v5/pins"

try:
    response = requests.post(url, headers=headers, json=payload)
    
    if response.status_code in (200, 201):
        print("🎉 SUCCÈS ! Le Pin a été publié.")
        print("Réponse :", json.dumps(response.json(), indent=2))
    else:
        print("❌ Échec.")
        print(f"Statut : {response.status_code}")
        print("Réponse :", response.text)
        
except Exception as e:
    print("Erreur réseau ou autre :", str(e))