"""
niche_selector.py — Sélection automatique de niche
====================================================
Stratégie :
  1. Rotation équilibrée : on préfère les niches les moins récemment utilisées
  2. Boost saisonnier   : ×2 priorité pour les niches en saison
  3. Légère randomisation pour éviter les répétitions strictes

Usage :
    from niche_selector import pick_niche, mark_used
    niche = pick_niche()        # choix auto
    mark_used(niche)            # à appeler après génération
"""

import json
import random
from datetime import datetime, date
from pathlib import Path

STRATEGY_FILE = Path(__file__).resolve().parent.parent / "data" / "niche_strategy.json"


def _load() -> dict:
    with open(STRATEGY_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def _save(data: dict) -> None:
    with open(STRATEGY_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def _current_season(data: dict) -> list[str]:
    """Retourne les niches boostées pour le mois courant."""
    month = datetime.now().month
    for season_range, niches in data.get("seasonal_boost", {}).items():
        start_m, end_m = map(int, season_range.split("-"))
        if start_m <= end_m:
            if start_m <= month <= end_m:
                return niches
        else:  # chevauchement d'année (ex: 12-02)
            if month >= start_m or month <= end_m:
                return niches
    return []


def _days_since_last_use(niche: str, last_used: dict) -> int:
    """Nombre de jours depuis la dernière utilisation (0 si jamais utilisé)."""
    if niche not in last_used or not last_used[niche]:
        return 999  # jamais utilisé → haute priorité
    last = datetime.fromisoformat(last_used[niche]).date()
    return (date.today() - last).days


def pick_niche(verbose: bool = True) -> str:
    """
    Sélectionne automatiquement la meilleure niche selon :
      - ancienneté depuis la dernière utilisation (plus c'est vieux = mieux)
      - boost ×2 si niche en saison
      - légère randomisation ±20 % pour éviter les cycles stricts
    """
    data = _load()
    niches = data.get("niches", [])
    if not niches:
        raise ValueError("Aucune niche définie dans niche_strategy.json")

    last_used   = data.get("last_used", {})
    boosted     = _current_season(data)

    # Score = jours_depuis_dernière_use × (2 si en saison sinon 1) × rand(0.8-1.2)
    scores = {}
    for n in niches:
        days   = _days_since_last_use(n, last_used)
        boost  = 2.0 if n in boosted else 1.0
        jitter = random.uniform(0.8, 1.2)
        scores[n] = days * boost * jitter

    chosen = max(scores, key=scores.__getitem__)

    if verbose:
        print(f"\n🎯 Niche sélectionnée automatiquement : {chosen}")
        if chosen in boosted:
            print(f"   ⬆️  Boost saisonnier actif (mois {datetime.now().month})")
        print(f"   ⏱  Dernière utilisation : {last_used.get(chosen, 'jamais')}")
        print(f"   Scores : { {k: round(v,1) for k, v in sorted(scores.items(), key=lambda x: -x[1])[:5]} }")

    return chosen


def mark_used(niche: str) -> None:
    """Enregistre la date d'utilisation de la niche dans niche_strategy.json."""
    data = _load()
    data.setdefault("last_used", {})[niche] = datetime.now().isoformat()
    _save(data)


if __name__ == "__main__":
    niche = pick_niche()
    print(f"\nNiche choisie : {niche}")
