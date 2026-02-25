#!/usr/bin/env python3
import subprocess
from config import BASE_DIR
from utils import now_ts

def push_ideas_to_git():
    print("==================================================")
    print("🚀 PUBLICATION DE VOS IDÉES SUR GITHUB")
    print("==================================================\n")
    
    csv_file = BASE_DIR / "data" / "pins_ideas_to_fill.csv"
    
    if not csv_file.exists():
        print(f"❌ Erreur: Le fichier {csv_file} n'existe pas.")
        return
        
    print(f"[{now_ts()}] Ajout du fichier {csv_file} à l'index Git...")
    
    try:
        # cd to BASE_DIR just to be sure
        subprocess.run(["git", "add", "data/pins_ideas_to_fill.csv"], cwd=BASE_DIR, check=True)
        
        # Check if there are changes to commit
        status_res = subprocess.run(["git", "status", "--porcelain"], cwd=BASE_DIR, capture_output=True, text=True)
        
        if "data/pins_ideas_to_fill.csv" not in status_res.stdout:
            print("ℹ️ Aucune modification détectée dans le fichier CSV. Avez-vous sauvegardé vos ASINs ?")
            return
            
        print(f"[{now_ts()}] Création du commit...")
        subprocess.run(["git", "commit", "-m", "feat: refilled ASIN ideas pool"], cwd=BASE_DIR, check=True)
        
        print(f"[{now_ts()}] Envoi vers GitHub (push)...")
        subprocess.run(["git", "push"], cwd=BASE_DIR, check=True)
        
        print("\n✅ OPÉRATION RÉUSSIE ! 🎉")
        print("L'autopilot utilisera ces nouveaux ASINs lors de ses prochaines exécutions automatisées.")
        
    except subprocess.CalledProcessError as e:
        print(f"\n❌ Erreur lors de l'exécution de la commande Git : {e}")
    except Exception as e:
        print(f"\n❌ Une erreur inattendue est survenue : {e}")

if __name__ == "__main__":
    push_ideas_to_git()
