# Pinterest Affiliate Automation

Un pipeline en Python pour générer et publier automatiquement des épingles Pinterest (Pins) pour des stratégies d'affiliation.

## Fonctionnalités
- Génération d'images via l'API Gemini (Imagen)
- Ajout de texte (overlay) sur l'image
- Hébergement Cloudinary pour accès public de l'image (requis par l'API Pinterest)
- Publication automatique sur un compte Pinterest via l'API v5

## Installation

```bash
# 1. Cloner le dépôt et se placer dedans
cd pinterest-affiliate-bot

# 2. Créer un environnement virtuel
python -m venv venv
source venv/bin/activate  # Sous Windows : venv\Scripts\activate

# 3. Installer les dépendances
pip install -r requirements.txt
```

## Configuration

1. Copiez le fichier d'exemple :
```bash
cp .env.example .env
```
2. Remplissez les clés d'API (Gemini, Pinterest, Cloudinary) dans `.env`.

## Comment utiliser ?

### Etape 1 : Préparer les données
Remplissez le fichier `data/pins_input.csv` avec vos projets de pins (titre, mots-clés, description, URL affiliée, etc.).

### Etape 2 : Générer les visuels
```bash
python src/generate_images.py
```
*Cela génère les images et crée `data/pins_ready.csv`.*

### Etape 3 : Nettoyer/valider le CSV
```bash
python src/prepare_pins_csv.py
```

### Etape 4 : Héberger les images (Recommandé)
```bash
python src/upload_images_cloudinary.py
```
*Upload les images et ajoute l'URL publique `image_public_url` au CSV.*

### Etape 5 : Récupérer son Board ID
```bash
python src/list_boards.py
```
*Copiez l'ID du board choisi et mettez à jour `PINTEREST_BOARD_ID` dans `.env`.*

### Etape 6 : Publication
Test en mode Dry Run (recommandé avant la première vraie publication) :
Vérifiez que `PUBLISH_DRY_RUN=true` est dans `.env`.
```bash
python src/publish_pins.py
```

Publication Réelle :
Passez `PUBLISH_DRY_RUN=false` et relancez le script.

## Notes sur l'affiliation
Assurez-vous de respecter les TOS de Pinterest en mentionnant clariement "(Lien affilié)" dans vos épingles et d'utiliser une redirection claire ou un lien direct approprié.

---

## 🚀 Le Workflow "Autopilot" (Générateur Automatique Quotidien)

Ce repository est configuré pour tourner sous **GitHub Actions** 100% en autonomie pour la Niche de Décoration d'intérieur.

**Fonctionnement :**
- Tous les jours, un cron (avec un délai aléatoire pour simuler un humain) exécute `src/autopilot.py`.
- Le script pioche `PINS_PER_DAY` (ex: 5) ASINs prêts à l'emploi (ayant un ASIN valide) dans le fichier `data/pins_ideas_to_fill.csv`.
- Il génère des images hyper réalistes avec **Together AI (FLUX.1-schnell)**.
- Il publie l'épingle via l'API Pinterest avec votre lien affilié (via Cloudinary).
- Il met à jour le fichier CSV en **supprimant** les lignes venant d'être publiées.
- Si le nombre de produits restants dans le CSV tombe sous 50, une **Issue GitHub** est créée pour vous alerter.

**Configuration GitHub Requise :**
Ajoutez ces variables dans les **Settings > Secrets & Variables > Actions** de votre dépôt GitHub :
- `TOGETHER_API_KEY` (Clé Together AI)
- `R2_ACCOUNT_ID`, `R2_ACCESS_KEY_ID`, `R2_SECRET_ACCESS_KEY`, `R2_BUCKET_NAME`, `R2_PUBLIC_HASH` (Pour Cloudflare R2)
- `PINTEREST_ACCESS_TOKEN`, `PINTEREST_BOARD_ID`
- `AMAZON_ASSOCIATE_TAG` (ex: `afprod-21`)

**Faire le plein d'ASIN (Ravitaillement Régulier) :**
Lorsque l'Action GitHub vous prévient que la réserve est presque vide :
1. Sur votre ordinateur (en local), lancez `python src/01_generate_ideas.py`.
2. L'IA va générer de nouvelles idées dans le fichier `data/pins_ideas_to_fill.csv`.
3. Ouvrez ce fichier, cliquez sur la colonne `search_link_amazon` pour trouver les produits.
4. Coupez/Collez les ASIN 10-caractères dans la colonne `asin` correspondante.
5. Une fois que vous en avez rempli suffisamment, lancez :
   ```bash
   python src/push_ideas_to_git.py
   ```
   Ce script se charge de pousser automatiquement les nouvelles idées au robot sur GitHub ! L'autopilot utilisera ces nouvelles entrées lors de son exécution le lendemain.
