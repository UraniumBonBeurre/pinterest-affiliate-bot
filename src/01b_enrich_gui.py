import tkinter as tk
from tkinter import ttk, messagebox
import pandas as pd
from pathlib import Path
import threading
import time
import sys
import csv
from playwright.sync_api import sync_playwright

BASE_DIR = Path(__file__).resolve().parent.parent
CSV_PATH = BASE_DIR / "data" / "pins_ideas_to_fill.csv"
PROFILE_DIR = BASE_DIR / "chrome_profile"

class App:
    def __init__(self, root):
        self.root = root
        self.root.title("🪄 Enrichissement ASIN Amazon | Pinterest Autopilot")
        self.root.geometry("1100x700")
        
        # Load Data
        if not CSV_PATH.exists():
            messagebox.showerror("Erreur", f"Le fichier CSV est introuvable:\n{CSV_PATH}")
            sys.exit(1)
            
        self.df = pd.read_csv(CSV_PATH)
        if 'amazon_product_url' not in self.df.columns:
            self.df['amazon_product_url'] = ""
        else:
            self.df['amazon_product_url'] = self.df['amazon_product_url'].fillna('')
        
        self.build_ui()
        self.populate_rows()
        
    def build_ui(self):
        style = ttk.Style()
        style.configure("TButton", font=("Arial", 13))
        
        self.main_frame = ttk.Frame(self.root)
        self.main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        header = tk.Label(
            self.main_frame, 
            text="✅ Lignes en attente de lien Amazon", 
            font=("Arial", 22, "bold")
        )
        header.pack(anchor="w", pady=(0, 5))
        
        sub = tk.Label(
            self.main_frame, 
            text="💡 Cliquez sur 'Ouvrir', naviguez sur Amazon, et cliquez sur un produit. La fenêtre se fermera toute seule !", 
            font=("Arial", 13), fg="#475569"
        )
        sub.pack(anchor="w", pady=(0, 20))
        
        # Canvas and Scrollbar
        self.canvas = tk.Canvas(self.main_frame, highlightthickness=0)
        self.scrollbar = ttk.Scrollbar(self.main_frame, orient="vertical", command=self.canvas.yview)
        self.scrollable_frame = ttk.Frame(self.canvas)
        
        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )
        self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        
        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")
        
        self.row_widgets = {}

    def populate_rows(self):
        # Clear existing
        for widget in self.scrollable_frame.winfo_children():
            widget.destroy()
            
        pending_count = 0
        for idx, row in self.df.iterrows():
            amz_url = str(row.get('amazon_product_url', '')).strip()
            title = str(row.get('title', '')).strip()
            
            # Skip if already filled, or empty row
            if (amz_url and amz_url.lower() != 'nan') or not title:
                continue
                
            pending_count += 1
            frame = ttk.Frame(self.scrollable_frame, borderwidth=1, relief="solid")
            frame.pack(fill="x", pady=7, padx=5, expand=True)
            
            # Title Label
            title_text = f"🏷️ {title[:70]}" + ("..." if len(title)>70 else "")
            title_lbl = tk.Label(frame, text=title_text, font=("Arial", 15), width=50, anchor="w", justify="left")
            title_lbl.pack(side="left", padx=15, pady=20)
            
            # Status Label
            status_lbl = tk.Label(frame, text="⏳ En attente", font=("Arial", 13, "bold"), fg="#d97706", width=25, anchor="w")
            status_lbl.pack(side="left", padx=10)
            
            # Open Button
            search_url = str(row.get('search_link_amazon', ''))
            btn = ttk.Button(frame, text="🔍 Ouvrir & Chercher", command=lambda i=idx, s=search_url: self.open_browser(i, s))
            btn.pack(side="right", padx=15, pady=15)
            
            self.row_widgets[idx] = {'status': status_lbl, 'btn': btn, 'frame': frame}
            
        if pending_count == 0:
            tk.Label(self.scrollable_frame, text="🎉 Bravo ! Tous les produits sont enrichis.", font=("Arial", 20), fg="green").pack(pady=80)

    def open_browser(self, idx, search_url):
        if not search_url or search_url.lower() == 'nan':
            messagebox.showerror("Erreur", "Pas de lien de recherche Amazon pour cette ligne.")
            return
            
        self.row_widgets[idx]['btn'].config(state=tk.DISABLED)
        self.row_widgets[idx]['status'].config(text="🌐 Navigation en cours...", fg="#2563eb")
        
        def _task():
            final_url = None
            try:
                from playwright_stealth import Stealth
                with sync_playwright() as p:
                    # Use a persistent context so the user doesn't have to log in or see pure cold start captchas
                    context = p.chromium.launch_persistent_context(
                        user_data_dir=str(PROFILE_DIR),
                        headless=False,
                        viewport={"width": 1280, "height": 800},
                        args=[
                            "--disable-blink-features=AutomationControlled",
                            "--disable-infobars"
                        ],
                        ignore_default_args=["--enable-automation"]
                    )
                    page = context.pages[0] if context.pages else context.new_page()
                    Stealth().apply_stealth_sync(page)
                    
                    page.goto(search_url)
                    
                    while True:
                        time.sleep(0.5)
                        try:
                            pages = context.pages
                            if not pages:
                                break
                                
                            for p_page in pages:
                                url = p_page.url
                                # Product pages in Amazon usually carry /dp/ or /gp/product/
                                if "/dp/" in url or "/gp/product/" in url:
                                    final_url = url
                                    break
                            
                            if final_url:
                                break
                        except Exception as e:
                            print(f"Exception observing URL: {e}")
                            break
                            
                    context.close()
            except Exception as e:
                print(f"Playwright error: {e}")
                
            if final_url:
                self.root.after(0, self.on_success, idx, final_url)
            else:
                self.root.after(0, self.on_cancel, idx)
                
        threading.Thread(target=_task, daemon=True).start()
        
    def on_success(self, idx, final_url):
        # Update DF and save immediately
        self.df.at[idx, 'amazon_product_url'] = final_url
        try:
            self.df.to_csv(CSV_PATH, index=False, quoting=csv.QUOTE_ALL)
            self.row_widgets[idx]['status'].config(text="✅ URL Capturée", fg="#16a34a")
            self.row_widgets[idx]['btn'].config(text="Refaire", state=tk.NORMAL)
        except Exception as e:
            self.row_widgets[idx]['status'].config(text="❌ Erreur de sauvegarde", fg="red")
            self.row_widgets[idx]['btn'].config(state=tk.NORMAL)
            messagebox.showerror("Save Error", str(e))
            
    def on_cancel(self, idx):
        self.row_widgets[idx]['status'].config(text="⚠️ Annulé / Fermé", fg="#dc2626")
        self.row_widgets[idx]['btn'].config(text="Ressayer", state=tk.NORMAL)

if __name__ == "__main__":
    root = tk.Tk()
    import platform
    import os
    if platform.system() == 'Darwin':
        # Force the python window to pop upfront on MacOS
        os.system('''/usr/bin/osascript -e 'tell app "Finder" to set frontmost of process "Python" to true' ''')
        
    app = App(root)
    root.mainloop()
