#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
#  infos.sh — Calcul du coût mensuel Pinterest Autopilot
# ─────────────────────────────────────────────────────────────────────────────

BOLD='\033[1m'
CYAN='\033[0;36m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
DIM='\033[2m'
NC='\033[0m'

echo ""
echo -e "${BOLD}${CYAN}╔══════════════════════════════════════════════╗${NC}"
echo -e "${BOLD}${CYAN}║   💰  Calculateur de coût — Autopilot        ║${NC}"
echo -e "${BOLD}${CYAN}╚══════════════════════════════════════════════╝${NC}"
echo ""

# ── Saisie ────────────────────────────────────────────────────────────────────
read -rp "$(echo -e "  ${BOLD}Combien de pins veux-tu publier par jour ?${NC} > ")" PINS_PER_DAY

# Validation
if ! [[ "$PINS_PER_DAY" =~ ^[0-9]+$ ]] || [ "$PINS_PER_DAY" -lt 1 ]; then
  echo -e "  ❌ Nombre invalide. Utilise un entier ≥ 1."
  exit 1
fi

# ── Tarifs (sources officielles) ──────────────────────────────────────────────
# FLUX.1-schnell via HF Serverless Inference :
#   → $0.0003 / image (1000×1500 px = 1.5 Mpx) — hf.co/pricing
# LLM DeepSeek-V3 via HF Serverless Inference :
#   → Gratuit en Free tier (quota mensuel ~$0.10)
#   → Les idées sont générées en batch : 1 appel LLM ≈ 10 idées
#   → Estimation : ~500 tokens/in + ~2000 tokens/out par batch
#   → DeepSeek-V3 pricing (HF) ≈ $0.00014/1K tokens in + $0.00028/1K tokens out
#   → Coût par batch ≈ $0.000070 + $0.000560 ≈ $0.00063 / 10 idées → $0.000063 / pin

python3 - <<EOF
pins_per_day   = $PINS_PER_DAY
days_per_month = 30

# ── Image generation (FLUX.1-schnell) ──
cost_image        = 0.000300  # \$/image — HF router pricing
total_images      = pins_per_day * days_per_month
cost_images_total = total_images * cost_image

# ── LLM (DeepSeek-V3 — idées générées en amont, 1 batch = 10 idées) ──
# On suppose 1 session generate_ideas / semaine pour remplir le stock
#   → 1 appel pour ~10 idées, ~4 sessions/mois
sessions_per_month = 4
batch_per_session  = max(1, round(pins_per_day * days_per_month / sessions_per_month / 10))
calls_per_month    = sessions_per_month * batch_per_session

# Tokens : ~600 in / ~2200 out par appel batch (10 idées)
tokens_in  = calls_per_month * 600
tokens_out = calls_per_month * 2200

# DeepSeek-V3 sur HF : \$0.14/M in + \$0.28/M out (src: hf.co/pricing 2025-02)
cost_llm_in  = (tokens_in  / 1_000_000) * 0.14
cost_llm_out = (tokens_out / 1_000_000) * 0.28
cost_llm_total = cost_llm_in + cost_llm_out

# ── Total ──
total_monthly = cost_images_total + cost_llm_total
total_annual  = total_monthly * 12

hf_free_credit = 0.10  # \$/mois inclus en plan Free

print()
print("  ┌─────────────────────────────────────────────────┐")
print(f"  │  📌 {pins_per_day} pins/jour  ×  {days_per_month} jours  =  {total_images} images/mois  │")
print("  └─────────────────────────────────────────────────┘")
print()
print("  📸  Images (FLUX.1-schnell vestigial HF router)")
print(f"       {total_images} images  ×  \$0.0003/img  =  \${cost_images_total:.4f}/mois")
print()
print("  🧠  LLM (DeepSeek-V3 — génération idées)")
print(f"       ≈ {calls_per_month} appels/mois  ({tokens_in} tok in / {tokens_out} tok out)")
print(f"       ≈ \${cost_llm_total:.4f}/mois")
print()
print("  ─────────────────────────────────────────────────")
print(f"  💸  Coût estimé total    : \${total_monthly:.4f} / mois")
print(f"  📅  Coût estimé annuel   : \${total_annual:.2f} / an")
print()

if total_monthly <= hf_free_credit:
    coverage = "✅ Couvert par le crédit Free HF (\$0.10/mois inclus)"
    print(f"  {coverage}")
else:
    over = total_monthly - hf_free_credit
    print(f"  ⚠️  Dépassement du Free tier (\$0.10 inclus) de \${over:.4f}/mois")
    print(f"     → Plan PRO HF (\$9/mois) inclut \$2.00 de crédits — amplement suffisant.")

print()
print("  Sources : hf.co/pricing (02/2025)  |  1 run GitHub Actions/jour")
print()
EOF
