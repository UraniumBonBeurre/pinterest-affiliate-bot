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
        self.root.geometry("1100x800")
        self.exit_code = 1
        self.root.protocol("WM_DELETE_WINDOW", lambda: self.close_app(1))
        
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
        sub.pack(anchor="w", pady=(0, 6))

        # Légende des émojis
        legend = tk.Label(
            self.main_frame,
            text="  🏷️ Titre du pin (EN)    🇫🇷 Traduction française (produit)    📂 Catégorie    ⏳ Statut    ",
            font=("Arial", 11), fg="#94a3b8", anchor="w", justify="left"
        )
        legend.pack(anchor="w", pady=(0, 14))
        
        # Bottom Frame for global actions (Packed FIRST at the bottom)
        self.bottom_frame = ttk.Frame(self.main_frame)
        self.bottom_frame.pack(side=tk.BOTTOM, fill=tk.X, pady=(20, 0))
        
        btn_cancel = tk.Button(
            self.bottom_frame, text="🛑 INTERROMPRE (Ne pas pousser)", 
            fg="#dc2626", font=("Arial", 14, "bold"), 
            command=lambda: self.close_app(1)
        )
        btn_cancel.pack(side="left", padx=10, pady=10)
        
        btn_validate = tk.Button(
            self.bottom_frame, text="✅ VALIDER ET POUSSER SUR GIT", 
            fg="#16a34a", font=("Arial", 14, "bold"), 
            command=lambda: self.close_app(0)
        )
        btn_validate.pack(side="right", padx=10, pady=10)

        # Middle Frame for Canvas and Scrollbar
        self.middle_frame = ttk.Frame(self.main_frame)
        self.middle_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        self.canvas = tk.Canvas(self.middle_frame, highlightthickness=0)
        self.scrollbar = ttk.Scrollbar(self.middle_frame, orient="vertical", command=self.canvas.yview)
        self.scrollable_frame = ttk.Frame(self.canvas)

        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )
        self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=self.scrollbar.set)

        # ── Mouse wheel ───────────────────────────────────────────
        def _on_mousewheel(event):
            if event.num == 4:    self.canvas.yview_scroll(-1, "units")
            elif event.num == 5:  self.canvas.yview_scroll( 1, "units")
            else: self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

        def _bind_wheel(widget):
            """Recursively bind wheel to widget and all its children."""
            widget.bind("<MouseWheel>", _on_mousewheel, add="+")
            widget.bind("<Button-4>",   _on_mousewheel, add="+")
            widget.bind("<Button-5>",   _on_mousewheel, add="+")
            for child in widget.winfo_children():
                _bind_wheel(child)

        # Bind on root + canvas now; also store the binder to run on new rows
        self._bind_wheel = _bind_wheel
        _bind_wheel(self.root)

        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")

        self.row_widgets = {}

    def close_app(self, code):
        self.exit_code = code
        self.root.destroy()

    def delete_row(self, idx):
        """Remove a row from the DataFrame and CSV immediately."""
        if messagebox.askyesno("❌ Supprimer ?", "Supprimer cette ligne du CSV ? (irréversible)"):
            self.df = self.df.drop(index=idx)
            try:
                self.df.to_csv(CSV_PATH, index=False, quoting=csv.QUOTE_ALL)
            except Exception as e:
                messagebox.showerror("Erreur", str(e))
                return
            # Remove the frame from view
            if idx in self.row_widgets:
                self.row_widgets[idx]['frame'].destroy()
                del self.row_widgets[idx]
            # Update scroll region
            self.scrollable_frame.update_idletasks()
            self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    # French niche labels for quick reading
    NICHE_FR = {
        "living_room_storage"    : "Salon — rangement",
        "bedroom_essentials"     : "Chambre — essentiels",
        "desk_organization"      : "Bureau — organisation",
        "cable_management"       : "Gestion des câbles",
        "small_space_solutions"  : "Petits espaces",
        "kitchen_organization"   : "Cuisine — organisation",
        "bathroom_storage"       : "Salle de bain — rangement",
        "entryway_decor"         : "Entrée — décoration",
        "outdoor_living"         : "Extérieur — vie outdoor",
        "bricolage"              : "Bricolage / DIY",
    }

    def populate_rows(self):
        # Clear existing
        for widget in self.scrollable_frame.winfo_children():
            widget.destroy()
            
        pending_count = 0
        for idx, row in self.df.iterrows():
            amz_url = str(row.get('amazon_product_url', '')).strip()
            title   = str(row.get('title', '')).strip()
            overlay   = str(row.get('overlay_text', '')).strip()
            hint      = str(row.get('french_hint', '')).strip()  # traduction FR LLM
            fr_text   = hint if (hint and hint.lower() != 'nan') else overlay  # fallback
            niche     = str(row.get('niche', '')).strip()
            niche_fr  = self.NICHE_FR.get(niche, niche.replace('_', ' ').title())
            
            # Skip if already filled, or empty row
            if (amz_url and amz_url.lower() != 'nan') or not title:
                continue
                
            pending_count += 1
            frame = ttk.Frame(self.scrollable_frame, borderwidth=1, relief="solid")
            frame.pack(fill="x", pady=7, padx=5, expand=True)

            # ── Left: text block ──────────────────────────────────────────
            text_block = tk.Frame(frame)
            text_block.pack(side="left", padx=15, pady=12, fill="x", expand=True)

            # English title (truncated)
            title_short = title[:75] + ("…" if len(title) > 75 else "")
            tk.Label(
                text_block, text=f"🏷️ {title_short}",
                font=("Arial", 14, "bold"), anchor="w", justify="left", wraplength=500
            ).pack(anchor="w")

            # Traduction FR : french_hint LLM (ou overlay fallback)
            if fr_text and fr_text.lower() != 'nan':
                tk.Label(
                    text_block, text=f"🇫🇷 {fr_text}",
                    font=("Arial", 13), fg="#d97706", anchor="w"
                ).pack(anchor="w", pady=(2, 0))

            tk.Label(
                text_block, text=f"📂 {niche_fr}",
                font=("Arial", 11, "italic"), fg="#6b7280", anchor="w"
            ).pack(anchor="w")
            
            # ── Right: delete ✕ + status + open button ──────────────────────────────
            status_lbl = tk.Label(frame, text="⏳ En attente", font=("Arial", 13, "bold"), fg="#d97706", width=22, anchor="w")
            status_lbl.pack(side="left", padx=10)

            search_url = str(row.get('search_link_amazon', ''))
            btn = ttk.Button(frame, text="🔍 Ouvrir & Chercher", command=lambda i=idx, s=search_url: self.open_browser(i, s))
            btn.pack(side="right", padx=8, pady=15)

            # ✕ Delete button
            del_btn = tk.Button(
                frame, text="✕", font=("Arial", 14, "bold"), fg="#ef4444", bg="#1a1a2e",
                activeforeground="white", activebackground="#dc2626",
                relief="flat", cursor="hand2", bd=0,
                command=lambda i=idx: self.delete_row(i)
            )
            del_btn.pack(side="right", padx=4, pady=15)

            self.row_widgets[idx] = {'status': status_lbl, 'btn': btn, 'frame': frame}
            self._bind_wheel(frame)  # scroll works on all new row widgets
        if pending_count == 0:
            tk.Label(self.scrollable_frame, text="🎉 Bravo ! Tous les produits sont enrichis.", font=("Arial", 20), fg="green").pack(pady=80)

    def open_browser(self, idx, search_url):
        if not search_url or search_url.lower() == 'nan':
            messagebox.showerror("Erreur", "Pas de lien de recherche Amazon pour cette ligne.")
            return
            
        import urllib.parse
        # Automatically shorten overly long search queries (for older rows)
        if "amazon.fr/s?k=" in search_url:
            try:
                parsed = urllib.parse.urlparse(search_url)
                query_dict = urllib.parse.parse_qs(parsed.query)
                if 'k' in query_dict:
                    words = query_dict['k'][0].split()
                    if len(words) > 4:
                        short_query = " ".join(words[:4])
                        search_url = f"https://www.amazon.fr/s?k={urllib.parse.quote_plus(short_query)}"
            except Exception:
                pass
                
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
                        # IMPORTANT: Don't use time.sleep(0.5) because it blocks the Playwright execution thread
                        try:
                            page.wait_for_timeout(500)
                        except Exception:
                            # If page was closed manually by user
                            pass
                            
                        try:
                            pages = context.pages
                            if not pages:
                                break
                                
                            for p_page in pages:
                                try:
                                    url = p_page.url
                                    if "/dp/" in url or "/gp/" in url:
                                        final_url = url
                                        break
                                except Exception:
                                    pass
                            
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
    sys.exit(app.exit_code)
