import os
from google import genai
from config import GEMINI_API_KEY

if not GEMINI_API_KEY:
    print("NO API KEY")
else:
    client = genai.Client(api_key=GEMINI_API_KEY)
    found = False
    for m in client.models.list():
        if "imagen" in m.name.lower() or "image" in m.name.lower():
            print(m.name, getattr(m, 'supported_generation_methods', ''))
            found = True
    if not found:
        print("No imagen models found.")
