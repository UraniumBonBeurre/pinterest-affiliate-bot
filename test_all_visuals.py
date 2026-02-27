import os
import sys
import pandas as pd
from pathlib import Path

# Permet d'importer le code du dossier src
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), 'src')))

from generate_images import add_text_overlay, generate_image_hf
from config import DATA_DIR, BASE_DIR
import shutil

def main():
    csv_path = DATA_DIR / "pins_ideas_to_fill.csv"
    output_dir = BASE_DIR / "output" / "test_visuals"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    if not csv_path.exists():
        print(f"❌ Erreur: Le fichier {csv_path} introuvable.")
        return
        
    df = pd.read_csv(csv_path)
    
    print(f"🔄 Début du test de génération sur {len(df)} idées de : {csv_path.name}")
    print(f"📁 Dossier de sortie : {output_dir}")
    print("-" * 60)
    
    base_image_path = output_dir / "00_base_test_image.jpg"
    if not base_image_path.exists():
        print("🖼️  Génération de l'image de base (une seule fois pour économiser l'API)...")
        prompt = "Photorealistic vertical Pinterest image 1000x1500, empty modern minimalist home interior 2026, soft natural daylight from large window, realistic textures wood linen concrete plants, cozy neutral colors beige white sage green warm wood tones, clean aesthetic composition, highly detailed 8K, professional interior photography style, no people, no text, no watermark, no artifacts, sharp focus, highly pinnable"
        try:
            from PIL import Image
            img = generate_image_hf(prompt)
            img = img.resize((1000, 1500), Image.Resampling.LANCZOS)
            img.save(base_image_path, "JPEG", quality=90)
            print("✅ Image de base générée.")
        except Exception as e:
            print(f"❌ Erreur génération image de base : {e}")
            return
            
    for idx, row in df.iterrows():
        title = str(row.get("title", "")).strip()
        overlay = str(row.get("overlay_text", "")).strip()
        
        # Ignorer les lignes vides
        if not title or title.lower() == "nan":
            continue
            
        print(f"[{idx+1}/{len(df)}] Overlay pour : {title[:40]}...")
        # Nom de fichier garanti unique basé sur l'index
        output_filename = f"pin_test_{idx:03d}.jpg"
        output_path = str(output_dir / output_filename)
        

            
        try:
            # On copie l'image de base pour travailler dessus
            temp_copy = str(output_dir / f"temp_{output_filename}")
            shutil.copy2(base_image_path, temp_copy)
            
            # On ajoute le texte
            add_text_overlay(temp_copy, overlay, output_path)
            
            # On supprime la copie temporaire
            if os.path.exists(temp_copy):
                os.remove(temp_copy)
                
            print(f"  -> ✅ Succès (Overlay généré) !")
        except Exception as e:
            print(f"  -> ❌ Erreur Overlay : {e}")

if __name__ == "__main__":
    main()
