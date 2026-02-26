#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
#  infos.sh  —  Pinterest Autopilot Dashboard
#  Affiche : compte HF, crédits estimés, CSV pool, R2, coût par run
# ─────────────────────────────────────────────────────────────────────────────
set -euo pipefail

# Charge le .env si présent
if [ -f .env ]; then
  export $(grep -v '^#' .env | grep -v '^$' | xargs) 2>/dev/null || true
fi

HF_TOKEN="${HF_TOKEN:-}"
PINS_PER_DAY="${PINS_PER_DAY:-1}"

# Utilise le python du venv si dispo (pour avoir boto3, etc.)
if [ -f "venv/bin/python3" ]; then
  PYTHON3="venv/bin/python3"
elif [ -f "venv/bin/python" ]; then
  PYTHON3="venv/bin/python"
else
  PYTHON3="python3"
fi

BOLD='\033[1m'
CYAN='\033[0;36m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color
DIM='\033[2m'

hr() { printf "${DIM}%s${NC}\n" "────────────────────────────────────────────────"; }

echo ""
echo -e "${BOLD}${CYAN}╔══════════════════════════════════════════════╗${NC}"
echo -e "${BOLD}${CYAN}║   🎯  Pinterest Autopilot — Tableau de Bord  ║${NC}"
echo -e "${BOLD}${CYAN}╚══════════════════════════════════════════════╝${NC}"
echo ""

# ─── 1. COMPTE HUGGING FACE ──────────────────────────────────────────────────
hr
echo -e "${BOLD}🤖  Compte Hugging Face${NC}"
hr

if [ -z "$HF_TOKEN" ]; then
  echo -e "  ${RED}✗ HF_TOKEN non trouvé dans .env${NC}"
else
  HF_RESPONSE=$(curl -s \
    -H "Authorization: Bearer $HF_TOKEN" \
    -H "Accept: application/json" \
    https://huggingface.co/api/whoami-v2 2>/dev/null || echo '{"error":"curl failed"}')

  if echo "$HF_RESPONSE" | grep -q '"error"'; then
    # Retry with /whoami (older endpoint)
    HF_RESPONSE=$(curl -s \
      -H "Authorization: Bearer $HF_TOKEN" \
      https://huggingface.co/api/whoami 2>/dev/null || echo '{"error":"curl failed"}')
  fi

  if echo "$HF_RESPONSE" | grep -q '"error"'; then
    echo -e "  ${RED}✗ Token invalide ou expiré${NC}"
    echo -e "  ${DIM}Réponse: $HF_RESPONSE${NC}"
  else
    HF_USER=$(echo "$HF_RESPONSE"    | $PYTHON3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('name','?'))" 2>/dev/null || echo "?")
    HF_EMAIL=$(echo "$HF_RESPONSE"   | $PYTHON3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('email','(non exposé)'))" 2>/dev/null || echo "?")
    HF_PLAN=$(echo "$HF_RESPONSE"    | $PYTHON3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('type','?').capitalize())" 2>/dev/null || echo "?")
    HF_FOLLOW=$(echo "$HF_RESPONSE"  | $PYTHON3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('numFollowers',0))" 2>/dev/null || echo "?")

    echo -e "  👤  Utilisateur  : ${BOLD}$HF_USER${NC}"
    echo -e "  📧  Email        : ${DIM}$HF_EMAIL${NC}"
    echo -e "  💼  Plan         : ${BOLD}$HF_PLAN${NC}"
    echo -e "  👥  Followers    : $HF_FOLLOW"
  fi
fi
echo ""

# ─── 2. CRÉDITS & COÛT ESTIMÉ ────────────────────────────────────────────────
hr
echo -e "${BOLD}💰  Crédits Inference & Coût estimé${NC}"
hr

# HuggingFace n'expose pas les crédits restants via API publique.
# On affiche les plafonds connus par plan + estimation de coût.
echo -e "  ${YELLOW}ℹ${NC}  HF n'expose pas les crédits restants via API."
echo -e "  ${DIM}→ Pour le solde exact : https://huggingface.co/settings/billing${NC}"
echo ""
echo -e "  Crédits mensuels inclus par plan :"
echo -e "    Free  : ${BOLD}\$0.10${NC} / mois   |   PRO : ${BOLD}\$2.00${NC} / mois"
echo ""

# Estimation : FLUX.1-schnell ≈ $0.0003 / image (1000×1500 = 1.5M px)
# Source : https://huggingface.co/pricing (Inference Providers)
COST_PER_IMAGE=0.0003
COST_PER_RUN=$($PYTHON3 -c "print(f'{int(\"${PINS_PER_DAY}\") * ${COST_PER_IMAGE}:.4f}')" 2>/dev/null || echo "?")
COST_PER_MONTH=$($PYTHON3 -c "print(f'{int(\"${PINS_PER_DAY}\") * ${COST_PER_IMAGE} * 30:.4f}')" 2>/dev/null || echo "?")

echo -e "  📸  Coût FLUX.1-schnell (estimation) : ~\$${COST_PER_IMAGE}/image"
echo -e "  🔄  PINS_PER_DAY actuel              : ${BOLD}${PINS_PER_DAY}${NC} pins/run"
echo -e "  💸  Coût estimé / run                : ~\$${COST_PER_RUN}"
echo -e "  📅  Coût estimé / mois (1 run/j)     : ~\$${COST_PER_MONTH}"
echo ""

# ─── 3. POOL CSV ─────────────────────────────────────────────────────────────
hr
echo -e "${BOLD}📋  Pool de pins (CSV)${NC}"
hr

CSV_PATH="data/pins_ideas_to_fill.csv"
if [ -f "$CSV_PATH" ]; then
  TOTAL=$(PYTHON3_BIN="$PYTHON3" $PYTHON3 - <<'EOF'
import csv
with open('data/pins_ideas_to_fill.csv') as f:
    rows = list(csv.DictReader(f))
total = len(rows)
ready = sum(1 for r in rows if r.get('amazon_product_url','').strip() or r.get('search_link_amazon','').strip())
print(f'{total} {ready}')
EOF
  2>/dev/null || echo "? ?")
  TOTAL_ROWS=$(echo $TOTAL | awk '{print $1}')
  READY_ROWS=$(echo $TOTAL | awk '{print $2}')

  if [ "$READY_ROWS" -lt 10 ] 2>/dev/null; then
    STATUS="${RED}⚠️  CRITIQUE${NC}"
  elif [ "$READY_ROWS" -lt 50 ] 2>/dev/null; then
    STATUS="${YELLOW}⚠️  Bas${NC}"
  else
    STATUS="${GREEN}✅ OK${NC}"
  fi

  RUNS_LEFT=$($PYTHON3 -c "print($READY_ROWS // $PINS_PER_DAY)" 2>/dev/null || echo "?")

  echo -e "  📦  Idées totales      : ${BOLD}${TOTAL_ROWS}${NC}"
  echo -e "  ✅  Prêtes à publier   : ${BOLD}${READY_ROWS}${NC}  — Statut: $STATUS"
  echo -e "  📅  Runs restants      : ${BOLD}${RUNS_LEFT}${NC} runs (à ${PINS_PER_DAY} pins/run)"
else
  echo -e "  ${RED}✗ Fichier '$CSV_PATH' introuvable${NC}"
fi
echo ""

# ─── 4. STOCKAGE R2 ──────────────────────────────────────────────────────────
hr
echo -e "${BOLD}☁️   Cloudflare R2 (images publiées)${NC}"
hr

R2_ACCOUNT_ID="${R2_ACCOUNT_ID:-}"
R2_ACCESS_KEY_ID="${R2_ACCESS_KEY_ID:-}"
R2_SECRET_ACCESS_KEY="${R2_SECRET_ACCESS_KEY:-}"
R2_BUCKET_NAME="${R2_BUCKET_NAME:-}"

if [ -z "$R2_ACCOUNT_ID" ] || [ -z "$R2_ACCESS_KEY_ID" ] || [ -z "$R2_BUCKET_NAME" ]; then
  echo -e "  ${YELLOW}ℹ${NC}  Identifiants R2 non trouvés dans .env — skip"
else
  R2_STATS=$($PYTHON3 - <<'EOF'
import os, boto3
from botocore.config import Config

s3 = boto3.client('s3',
    endpoint_url=f"https://{os.environ['R2_ACCOUNT_ID']}.r2.cloudflarestorage.com",
    aws_access_key_id=os.environ['R2_ACCESS_KEY_ID'],
    aws_secret_access_key=os.environ['R2_SECRET_ACCESS_KEY'],
    config=Config(signature_version='s3v4'),
    region_name='auto'
)
paginator = s3.get_paginator('list_objects_v2')
count, total_bytes = 0, 0
for page in paginator.paginate(Bucket=os.environ['R2_BUCKET_NAME']):
    for obj in page.get('Contents', []):
        count += 1
        total_bytes += obj['Size']
print(f"{count} {total_bytes}")
EOF
  2>/dev/null || echo "ERR")

  if [ "$R2_STATS" = "ERR" ] || [ -z "$R2_STATS" ]; then
    echo -e "  ${RED}✗ Impossible de contacter R2${NC}"
  else
    R2_COUNT=$(echo $R2_STATS | awk '{print $1}')
    R2_BYTES=$(echo $R2_STATS | awk '{print $2}')
    R2_MB=$($PYTHON3 -c "print(f'{int(\"${R2_BYTES}\") / 1024 / 1024:.1f}')" 2>/dev/null || echo "?")
    echo -e "  🖼️   Fichiers stockés : ${BOLD}${R2_COUNT}${NC} images"
    echo -e "  💾  Taille totale    : ${BOLD}${R2_MB} Mo${NC}"
    echo -e "  ${DIM}(R2 Free = 10 Go inclus — vous êtes loin du limite)${NC}"
  fi
fi
echo ""

# ─── 5. GIT ──────────────────────────────────────────────────────────────────
hr
echo -e "${BOLD}🔀  Git — État du dépôt${NC}"
hr
BRANCH=$(git branch --show-current 2>/dev/null || echo "?")
LAST_COMMIT=$(git log -1 --format="%h — %s (%cr)" 2>/dev/null || echo "?")
MODIFIED=$(git status --short 2>/dev/null | wc -l | tr -d ' ')
echo -e "  🌿  Branche       : ${BOLD}${BRANCH}${NC}"
echo -e "  🕐  Dernier commit: ${DIM}${LAST_COMMIT}${NC}"
echo -e "  📝  Fichiers modifs locaux : ${BOLD}${MODIFIED}${NC}"
echo ""

hr
echo -e "${DIM}  Solde exact HF → https://huggingface.co/settings/billing${NC}"
echo -e "${DIM}  Tableau Pinterest → https://analytics.pinterest.com${NC}"
hr
echo ""
