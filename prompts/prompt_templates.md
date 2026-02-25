# Prompts pour la génération de CSV (Affiliation Pinterest)

Ce fichier regroupe des structures de prompt efficaces à fournir à ChatGPT ou Claude pour générer les données structurées des épingles Pinterest.

## 1. Génération de lot (Batch)

**Prompt :**
```text
Agis comme un expert Pinterest et copywriter spécialisé dans la décoration intérieure.
Génère pour moi un tableau de 10 nouvelles idées d'épingles destinées à l'affiliation pour ma ligne éditoriale "décoration minimaliste à petit budget".
Pour chaque idée, remplis les colonnes suivantes au format CSV :

- slug : identifiant unique (ex: pin_deco_006)
- title : Titre accrocheur et optimisé SEO Pinterest (max 90 char)
- overlay_text : Texte très court et percutant qui sera inséré sur l'image elle-même (3 à 6 mots max)
- description : Description d'environ 300 caractères qui donne envie de cliquer, en terminant par l'appel à l'action "[LIEN_AFFILIATE]"
- affiliate_url : Laisse vide ou mets un placeholder (ex: "URL_A_CHANGER")
- niche : "décoration, minimalisme"
- keywords : 5 à 10 mots clés pertinents séparés par des virgules (ex: "salon minimaliste, déco pas chère, astuce rangement")

Le CSV doit utiliser la virgule (,) comme séparateur et des guillemets doubles pour entourer les textes longs comportant des virgules.
```

## 2. Déclinaisons (A/B Testing Visuel)

**Prompt :**
```text
Je veux décliner ce produit affilié en 3 épingles Pinterest différentes pour tester divers angles d'approche.
Produit : "Étagère murale en bois asymétrique"
URL : https://amazon.fr/dp/123456

Angle 1 : Pragmatique (Gain de place)
Angle 2 : Esthétique (Design moderne)
Angle 3 : Inspirant (Avant / Après imaginaire ou mise en situation de rêve)

Génère les 3 lignes au format CSV avec les mêmes colonnes que précédemment : 
slug, title, overlay_text, description, affiliate_url, niche, keywords.
```
