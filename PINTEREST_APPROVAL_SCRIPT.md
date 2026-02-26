# 🎥 Script Vidéo — Accès Standard Pinterest API

Pinterest exige une courte vidéo screencast en anglais montrant comment ton app utilise leur API.

---

## 🎬 1. Préparation

1. Ouvre VSCode/Cursor avec `src/publish_pins.py` (surligne `create_pin` vers ligne 73).
2. Ouvre un terminal à la racine du projet.
3. Ouvre ton compte Pinterest dans un navigateur (tableau "house" visible).
4. Assure-toi que `.env` pointe sur `PINTEREST_API_BASE=https://api.pinterest.com/v5` (prod).

---

## 🗣️ 2. Script (en anglais)

**[1 — Intro]**
> *"Hi Pinterest team! My name is Nicolas and I'm applying for Standard API Access for [Nom exact de l'App]."*
> *"This is a private internal CLI tool I built as a content creator and Amazon affiliate. It helps me showcase curated home decor products to my audience."*
> *"The app automatically generates photorealistic contextual product images — all original content — and publishes them to my boards using your API."*

**[2 — Auth (pas d'UI OAuth)]**
> *"This is a server-to-server script — I am the only user. I generate my access token directly from the Pinterest Developer portal and inject it as a secure environment variable. No public login flow is needed."*

**[3 — Montrer le code — endpoint POST /v5/pins]**
*(Surligne `create_pin` dans `publish_pins.py`)*
> *"Here is the core logic. I use the `POST /v5/pins` endpoint. Each pin gets an original AI-generated image, a descriptive title, and a direct Amazon affiliate link giving users a seamless path to purchase."*

**[4 — Démo live]**
*(Lance le script via ton terminal ou GitHub Actions > Run workflow)*
> *"I'll now trigger a live run to demonstrate pin creation."*
*(Montre le log avec `✅ Pinterest Publish Success! Pin ID:...`)*
> *"The API returned 201 Created — the pin was published successfully."*

**[5 — Preuve visuelle]**
*(Rafraîchis ton tableau Pinterest dans le navigateur)*
> *"Here is my live Pinterest board with the freshly published pin — image, title, and affiliate destination link, all correct."*

**[6 — Conclusion]**
> *"This workflow fully complies with Pinterest's Community Guidelines on original content and affiliate links. This tool is essential for maintaining my publishing consistency and bringing curated value to the Pinterest community. Thank you for reviewing my Standard Access request."*

---

## 📋 3. Formulaire Pinterest

- **App description** : *"Private internal CLI script hosted on GitHub Actions. Automates original home decor pin creation and publishing to my personal boards via POST /v5/pins."*
- **Does your app require users to log in?** : **Non** — server-to-server with a static personal access token.
