#!/usr/bin/env python3
import warnings
warnings.filterwarnings("ignore", category=UserWarning, module="PIL")

import os
import base64
import pandas as pd
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import requests
import time
from pathlib import Path
from tenacity import retry, wait_fixed, stop_after_attempt, retry_if_exception_type
from config import HF_TOKEN, DATA_DIR, IMAGES_DIR, BASE_DIR

class GenerationError(Exception):
    pass

# ---------------------------------------------------------------------------
# FONT MANAGEMENT — auto-download Caveat if missing
# ---------------------------------------------------------------------------

FONTS_DIR = BASE_DIR / "assets" / "fonts"

# Plusieurs URLs de fallback par police (GitHub rate-limite parfois et renvoie du HTML)
CAVEAT_URLS = {
    "Caveat-Bold.ttf": [
        # GitHub — raw direct avec Accept header
        "https://github.com/googlefonts/caveat/raw/refs/heads/main/fonts/ttf/Caveat-Bold.ttf",
        # jsDelivr CDN (miroir fiable de GitHub, pas de redirect HTML)
        "https://cdn.jsdelivr.net/gh/googlefonts/caveat@main/fonts/ttf/Caveat-Bold.ttf",
        # Google Fonts API static (woff2 → non utilisable, mais TTF dispo ici)
        "https://fonts.gstatic.com/s/caveat/v18/WnznHAc5bAfYB2QRah7pcpNvOx-pjcJ9eIWpZA.ttf",
    ],
    "Caveat-Regular.ttf": [
        "https://github.com/googlefonts/caveat/raw/refs/heads/main/fonts/ttf/Caveat-Regular.ttf",
        "https://cdn.jsdelivr.net/gh/googlefonts/caveat@main/fonts/ttf/Caveat-Regular.ttf",
        "https://fonts.gstatic.com/s/caveat/v18/WnznHAc5bAfYB2QRah7pcpNvOx-pjfJ9eIWpZA.ttf",
    ],
}

# Magic bytes qui identifient un vrai fichier TTF/OTF
_TTF_MAGIC = (
    b"\x00\x01\x00\x00",  # TrueType
    b"\x74\x72\x75\x65",  # "true"
    b"\x4F\x54\x54\x4F",  # "OTTO" (OpenType/CFF)
    b"\x74\x79\x70\x31",  # "typ1"
)

def _is_valid_ttf(data: bytes) -> bool:
    """Vérifie que les données sont bien un fichier TTF/OTF valide."""
    return len(data) > 4 and data[:4] in _TTF_MAGIC

def _download_font(font_file: str, urls: list, dest: Path) -> bool:
    """
    Essaie chaque URL dans l'ordre jusqu'à obtenir un TTF valide.
    Retourne True si succès, False sinon.
    """
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Accept": "application/octet-stream, */*",
    }
    for url in urls:
        try:
            print(f"[FONTS]   ↓ Tentative : {url}")
            r = requests.get(url, headers=headers, timeout=30, allow_redirects=True)
            r.raise_for_status()
            data = r.content
            if not _is_valid_ttf(data):
                print(f"[FONTS]   ✗ Fichier invalide reçu ({len(data)} octets, probablement du HTML) — essai URL suivante…")
                continue
            dest.write_bytes(data)
            print(f"[FONTS] ✓ {font_file} téléchargée avec succès ({len(data) // 1024} Ko).")
            return True
        except Exception as e:
            print(f"[FONTS]   ✗ Erreur réseau : {e} — essai URL suivante…")
    return False

def ensure_fonts() -> dict:
    """
    Vérifie que les polices Caveat sont présentes et valides.
    - Si un fichier existe mais est corrompu, il est supprimé et re-téléchargé.
    - Essaie plusieurs URLs de fallback.
    Retourne un dict {nom_fichier: chemin_absolu | None}.
    """
    FONTS_DIR.mkdir(parents=True, exist_ok=True)
    paths = {}

    for font_file, urls in CAVEAT_URLS.items():
        font_path = FONTS_DIR / font_file

        # Vérifier si le fichier existe ET est valide
        if font_path.exists():
            data = font_path.read_bytes()
            if _is_valid_ttf(data):
                print(f"[FONTS] ✓ {font_file} présente et valide.")
                paths[font_file] = font_path
                continue
            else:
                print(f"[FONTS] ⚠ {font_file} corrompue (format invalide) — suppression et re-téléchargement…")
                font_path.unlink()

        # Téléchargement
        print(f"[FONTS] ✗ {font_file} absente — téléchargement en cours…")
        success = _download_font(font_file, urls, font_path)
        paths[font_file] = font_path if success else None

        if not success:
            print(f"[FONTS] ✗ Impossible de télécharger {font_file} depuis toutes les sources. Fallback système actif.")

    return paths

def load_font(font_name: str, font_size: int, font_paths: dict) -> ImageFont.FreeTypeFont:
    """
    Charge la police demandée. Si elle n'est pas disponible,
    tente des polices système, puis load_default() en dernier recours.
    """
    # 1. Tentative avec la police Caveat (téléchargée ou déjà présente)
    path = font_paths.get(font_name)
    if path and Path(path).exists():
        try:
            return ImageFont.truetype(str(path), font_size)
        except Exception as e:
            print(f"[FONTS] Erreur chargement {font_name} : {e}")

    # 2. Fallback polices système
    system_fonts = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf",
        "/System/Library/Fonts/Helvetica.ttc",   # macOS
        "C:/Windows/Fonts/arialbd.ttf",           # Windows
        "C:/Windows/Fonts/arial.ttf",
    ]
    for sf in system_fonts:
        try:
            font = ImageFont.truetype(sf, font_size)
            print(f"[FONTS] Fallback système utilisé : {sf}")
            return font
        except Exception:
            continue

    # 3. Dernier recours : load_default avec taille (Pillow >= 10.1)
    try:
        font = ImageFont.load_default(size=font_size)
        print(f"[FONTS] load_default(size={font_size}) utilisé — installez Caveat pour un meilleur rendu.")
        return font
    except TypeError:
        font = ImageFont.load_default()
        print("[FONTS] load_default() sans taille utilisé — mettez à jour Pillow (>=10.1).")
        return font


# Pré-chargement des polices au démarrage du module
_FONT_PATHS = ensure_fonts()

# ---------------------------------------------------------------------------
# IMAGE GENERATION — HuggingFace API
# ---------------------------------------------------------------------------

@retry(stop=stop_after_attempt(5), wait=wait_fixed(15), retry=retry_if_exception_type(GenerationError))
def generate_image_hf(prompt: str) -> Image.Image:
    """
    Génère une image via l'API Hugging Face (Flux.1-schnell).
    """
    if not HF_TOKEN:
        raise GenerationError("HF_TOKEN n'est pas défini dans .env")

    API_URL = "https://router.huggingface.co/hf-inference/models/black-forest-labs/FLUX.1-schnell"
    headers = {"Authorization": f"Bearer {HF_TOKEN}"}

    payload = {
        "inputs": prompt,
        "parameters": {
            "negative_prompt": (
                "cartoon, anime, illustration, painting, blurry, low quality, "
                "deformed, ugly, extra objects, text, watermark, people, faces, "
                "animals, fantasy, overexposed, underexposed"
            ),
            "width": 1000,
            "height": 1500,
        },
    }

    try:
        response = requests.post(API_URL, headers=headers, json=payload, timeout=60)

        if response.status_code == 503:
            print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] HF API 503 : modèle en chargement. {response.text}")
            raise GenerationError(f"Modèle en chargement, retry… {response.json()}")

        if response.status_code != 200:
            print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] HF API Erreur {response.status_code} : {response.text}")
            raise GenerationError(f"HF API Erreur {response.status_code} : {response.text}")

        image = Image.open(BytesIO(response.content))
        return image.convert("RGB")

    except Exception as e:
        if isinstance(e, GenerationError):
            raise
        raise GenerationError(f"HF Request Error : {e}")

# ---------------------------------------------------------------------------
# TEXT OVERLAY — Pinterest Style + Highlight per ligne
# ---------------------------------------------------------------------------

def _tw(font: ImageFont.FreeTypeFont, text: str) -> float:
    """Mesure la largeur pixel d'un texte."""
    dummy = ImageDraw.Draw(Image.new("RGB", (1, 1)))
    return dummy.textlength(text, font=font)


def _wrap(text: str, font: ImageFont.FreeTypeFont, max_w: int) -> list[str]:
    """
    Word-wrap propre : jamais de coupure à l'intérieur d'un mot.
    La police doit avoir été choisie pour que le mot le plus long tienne dans max_w.
    """
    words = text.upper().split()
    lines, cur = [], []
    for word in words:
        candidate = " ".join(cur + [word])
        if _tw(font, candidate) > max_w and cur:
            lines.append(" ".join(cur))
            cur = [word]
        else:
            cur.append(word)
    if cur:
        lines.append(" ".join(cur))
    return lines or [text.upper()]


def _autofit(
    text: str,
    font_name: str,
    font_paths: dict,
    max_w: int,
    max_h: int,
    start: int = 190,
    minimum: int = 50,
    spacing: float = 1.20,
) -> tuple:
    """
    Cherche la plus grande taille de police telle que :
      - Le mot le plus long tient dans max_w (jamais de coupure)
      - Le bloc total tient dans max_h
    Retourne (font, lines, line_h, size).
    """
    words_upper = text.upper().split()
    for size in range(start, minimum - 1, -2):
        font = load_font(font_name, size, font_paths)
        longest_w = max(_tw(font, w) for w in words_upper)
        if longest_w > max_w:
            continue
        lines  = _wrap(text, font, max_w)
        line_h = int(size * spacing)
        if len(lines) * line_h <= max_h:
            return font, lines, line_h, size
    font   = load_font(font_name, minimum, font_paths)
    lines  = _wrap(text, font, max_w)
    line_h = int(minimum * spacing)
    return font, lines, line_h, minimum


def _rounded_rect_rgba(
    layer: Image.Image,
    x0: int, y0: int, x1: int, y1: int,
    radius: int,
    fill: tuple,
) -> None:
    """
    Dessine un rectangle aux coins arrondis sur une couche RGBA.
    Compatible Pillow >= 8.2 (rounded_rectangle natif) et versions antérieures.
    """
    draw = ImageDraw.Draw(layer)
    try:
        draw.rounded_rectangle([x0, y0, x1, y1], radius=radius, fill=fill)
    except AttributeError:
        # Fallback : composition manuelle
        draw.rectangle([x0 + radius, y0, x1 - radius, y1], fill=fill)
        draw.rectangle([x0, y0 + radius, x1, y1 - radius], fill=fill)
        for cx, cy in [
            (x0 + radius, y0 + radius),
            (x1 - radius, y0 + radius),
            (x0 + radius, y1 - radius),
            (x1 - radius, y1 - radius),
        ]:
            draw.ellipse([cx - radius, cy - radius, cx + radius, cy + radius], fill=fill)


def add_text_overlay(image_path: str, texte: str, output_path: str = None) -> str:
    """
    Overlay Pinterest avec surlignage noir arrondi par ligne :

    ┌──────────────────────────────┐
    │  ░░░░░ gradient sombre ░░░░░ │  ← 42% de l'image
    │                              │
    │   ╭───────────────────╮      │
    │   │  TITRE EN CAVEAT  │      │  ← highlight noir 90% + texte blanc
    │   ╰───────────────────╯      │
    │   ╭──────────────────────╮   │
    │   │  DEUXIÈME LIGNE ICI  │   │  ← chaque ligne a son propre highlight
    │   ╰──────────────────────╯   │
    │            ─────             │  ← tiret décoratif
    │                              │
    ├──────────────────────────────┤
    │     [photo intacte]          │  ← 58% bas visible
    └──────────────────────────────┘

    Caractéristiques :
    • Highlight noir (0,0,0) opacité 90% par ligne, coins arrondis
    • Padding horizontal et vertical proportionnel à la taille de police
    • Centrage horizontal exact par ligne
    • Centrage vertical du bloc dans la zone gradient
    • Ombre portée gaussienne pour profondeur
    • Contour sombre fin sur le texte blanc
    • Jamais de coupure de mot — autofit réduit la police si besoin
    • Tiret décoratif centré sous le dernier highlight
    """
    if output_path is None:
        ext = ".png" if image_path.endswith(".png") else ".jpg"
        output_path = image_path.replace(ext, f"_final{ext}")

    img = Image.open(image_path).convert("RGBA")
    W, H = img.size

    # ══════════════════════════════════════════════════════════════════════════
    # 1. GRADIENT SOMBRE en haut
    # ══════════════════════════════════════════════════════════════════════════
    BAND_RATIO = 0.48
    BAND_H     = int(H * BAND_RATIO)

    grad_pixels = []
    for row in range(BAND_H):
        t     = row / BAND_H
        alpha = int(160 * (1.0 - t ** 0.55))   # doux, max 160 (assez subtil)
        grad_pixels.append((8, 6, 5, alpha))

    grad_col = Image.new("RGBA", (1, BAND_H))
    grad_col.putdata(grad_pixels)
    gradient = grad_col.resize((W, BAND_H), Image.Resampling.NEAREST)
    band     = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    band.paste(gradient, (0, 0))
    img = Image.alpha_composite(img, band)

    # ══════════════════════════════════════════════════════════════════════════
    # 2. AUTOFIT + calcul des zones
    # ══════════════════════════════════════════════════════════════════════════
    MARGIN_X  = int(W * 0.07)
    PAD_TOP   = int(H * 0.04)
    PAD_BOT   = int(H * 0.04)
    MAX_TXT_W = W - 2 * MARGIN_X
    MAX_TXT_H = BAND_H - PAD_TOP - PAD_BOT

    font, lines, line_h, fsize = _autofit(
        texte, "Caveat-Bold.ttf", _FONT_PATHS,
        max_w=MAX_TXT_W, max_h=MAX_TXT_H,
        start=190, minimum=50, spacing=1.20,
    )
    total_txt_h = len(lines) * line_h

    # Centrage vertical dans la zone gradient
    usable  = BAND_H - PAD_TOP - PAD_BOT
    start_y = PAD_TOP + max(0, (usable - total_txt_h) // 2)

    # ══════════════════════════════════════════════════════════════════════════
    # 3. HIGHLIGHTS ARRONDIS — un rectangle par ligne, centré sur la ligne
    # ══════════════════════════════════════════════════════════════════════════
    # Padding intérieur du highlight autour du texte
    HL_PAD_X = int(fsize * 0.28)   # padding gauche/droite (proportionnel)
    HL_PAD_Y = int(fsize * 0.10)   # padding haut/bas
    HL_RADIUS = max(8, int(fsize * 0.18))  # rayon des coins arrondis
    HL_COLOR  = (0, 0, 0, 230)     # noir 90% d'opacité

    highlight_layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))

    y = start_y
    for line in lines:
        lw     = int(_tw(font, line))
        # Coordonnées du texte (centré horizontalement)
        txt_x  = (W - lw) // 2
        txt_y  = y
        # Rectangle autour de ce texte + padding
        hl_x0  = txt_x - HL_PAD_X
        hl_y0  = txt_y - HL_PAD_Y
        hl_x1  = txt_x + lw + HL_PAD_X
        hl_y1  = txt_y + fsize + HL_PAD_Y   # fsize = hauteur réelle du glyphe
        _rounded_rect_rgba(
            highlight_layer,
            hl_x0, hl_y0, hl_x1, hl_y1,
            radius=HL_RADIUS,
            fill=HL_COLOR,
        )
        y += line_h

    img = Image.alpha_composite(img, highlight_layer)

    # ══════════════════════════════════════════════════════════════════════════
    # 4. OMBRE PORTÉE (couche séparée + blur) — sous le texte, sur les highlights
    # ══════════════════════════════════════════════════════════════════════════
    sh_layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    sh_draw  = ImageDraw.Draw(sh_layer)
    sh_off   = max(3, fsize // 32)
    sh_blur  = max(4, fsize // 20)

    y = start_y
    for line in lines:
        lw = _tw(font, line)
        x  = (W - int(lw)) // 2
        sh_draw.text((x + sh_off, y + sh_off), line, font=font,
                     fill=(0, 0, 0, 180))
        y += line_h

    sh_layer = sh_layer.filter(ImageFilter.GaussianBlur(radius=sh_blur))
    img      = Image.alpha_composite(img, sh_layer)

    # ══════════════════════════════════════════════════════════════════════════
    # 5. TEXTE PRINCIPAL — blanc pur, contour sombre fin
    # ══════════════════════════════════════════════════════════════════════════
    draw     = ImageDraw.Draw(img)
    stroke_w = max(2, fsize // 55)

    y = start_y
    for line in lines:
        lw = _tw(font, line)
        x  = (W - int(lw)) // 2
        draw.text(
            (x, y), line, font=font,
            fill=(255, 255, 255, 255),
            stroke_width=stroke_w,
            stroke_fill=(20, 15, 10, 255),
        )
        y += line_h

    # ══════════════════════════════════════════════════════════════════════════
    # 6. TIRET DÉCORATIF centré, juste sous le dernier highlight
    # ══════════════════════════════════════════════════════════════════════════
    last_hl_bottom = start_y + total_txt_h + HL_PAD_Y
    dash_y   = last_hl_bottom + int(fsize * 0.25)
    dash_hw  = int(W * 0.055)
    dash_cx  = W // 2
    dash_th  = max(2, fsize // 60)

    draw.line(
        [(dash_cx - dash_hw, dash_y), (dash_cx + dash_hw, dash_y)],
        fill=(255, 255, 255, 190),
        width=dash_th,
    )
    # Micro-points aux extrémités
    dot_r = dash_th + 1
    for dx in [dash_cx - dash_hw, dash_cx + dash_hw]:
        draw.ellipse(
            [dx - dot_r, dash_y - dot_r, dx + dot_r, dash_y + dot_r],
            fill=(255, 255, 255, 170),
        )

    # ══════════════════════════════════════════════════════════════════════════
    # 7. SAUVEGARDE
    # ══════════════════════════════════════════════════════════════════════════
    img = img.convert("RGB")
    img.save(output_path, "JPEG", quality=98, optimize=True)
    return output_path

# ---------------------------------------------------------------------------
# SINGLE IMAGE GENERATION (workflow autopilot)
# ---------------------------------------------------------------------------

def generate_interior_image(image_description: str, image_path: str, overlay_text: str = None) -> str:
    """
    Génère une image via HF et y ajoute l'overlay texte PIL.
    Utilisé par le workflow autopilot.
    """
    base_img = generate_image_hf(image_description)
    final_img = base_img.resize((1000, 1500), Image.Resampling.LANCZOS)
    final_img.save(image_path, "JPEG", quality=90)

    if overlay_text and overlay_text.strip() and str(overlay_text).lower() != "nan":
        add_text_overlay(image_path, overlay_text, image_path)

    return image_path

# ---------------------------------------------------------------------------
# BATCH PROCESSING
# ---------------------------------------------------------------------------

def now_ts() -> str:
    return time.strftime("%Y-%m-%d %H:%M:%S")

def process_batch():
    input_path = DATA_DIR / "pins_input.csv"
    output_csv = DATA_DIR / "pins_ready.csv"

    if not input_path.exists():
        print(f"Erreur : {input_path} introuvable.")
        return

    df = pd.read_csv(input_path)
    results = []

    for idx, row in df.iterrows():
        slug             = row.get("slug")
        title            = row.get("title")
        overlay_text     = row.get("overlay_text", "")
        description      = row.get("description", "")
        affiliate_url    = row.get("affiliate_url", "")
        keywords         = row.get("keywords", "")
        image_description = row.get("image_description_for_llm", title)

        print(f"[{now_ts()}] Traitement de {slug}…")

        image_path = IMAGES_DIR / f"{slug}.jpg"
        status = "success"

        if not image_path.exists():
            try:
                if pd.isna(image_description) or not str(image_description).strip():
                    image_description = (
                        f"Pinterest style aesthetic product photo, vertical orientation, "
                        f"brightly lit, high quality professional photography, highly realistic, "
                        f"8k resolution. Subject: {title}"
                    )

                generate_interior_image(
                    str(image_description),
                    str(image_path),
                    str(overlay_text) if pd.notna(overlay_text) else title,
                )
                print(f"[{now_ts()}] -> Sauvegardé avec succès")
            except Exception as e:
                import tenacity
                if isinstance(e, tenacity.RetryError):
                    e = e.last_attempt.exception()
                print(f"[{now_ts()}] -> Erreur : {e}")
                status = f"error: {str(e)}"
        else:
            print(f"[{now_ts()}] -> Image déjà existante, ignorée")

        results.append({
            "slug":         slug,
            "title":        title,
            "description":  str(description).replace("[LIEN_AFFILIATE]", str(affiliate_url)) if pd.notna(description) else "",
            "affiliate_url": affiliate_url,
            "image_path":   str(image_path),
            "keywords":     keywords,
            "status":       status,
        })

    df_ready = pd.DataFrame(results)
    df_ready.to_csv(output_csv, index=False)
    print(f"\nTraitement batch terminé. Fichier écrit : {output_csv}")

if __name__ == "__main__":
    process_batch()
