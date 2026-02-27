"""
niche_selector.py — Sélection automatique de niche
====================================================
Stratégie de scoring (par ordre de priorité) :
  1. Poids de base (_weights) : volume de recherche relatif sur Pinterest FR
  2. Rotation équilibrée : bonus exponentiel au nombre de jours sans utilisation
  3. Boost saisonnier : ×2 pour les niches en saison (périmètre mensuel)
  4. Légère randomisation ±20 % pour casser les cycles stricts

Usage :
    from niche_selector import pick_niche, pick_niche_multi, mark_used
    niche  = pick_niche()           # choix auto, 1 niche
    niches = pick_niche_multi(n=3)  # top 3 niches
    mark_used(niche)                # à appeler après génération
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


def _days_since_last_use(niche: str, last_used: dict) -> float:
    """
    Nombre de jours depuis la dernière utilisation.
    Niches jamais utilisées (null / absentes) → 999 jours (priorité max).
    """
    val = last_used.get(niche)
    if not val or val == "null":
        return 999.0
    try:
        last = datetime.fromisoformat(str(val)).date()
        return max(0.0, (date.today() - last).days)
    except (ValueError, TypeError):
        return 999.0


def _score(niche: str, data: dict, boosted: list[str], last_used: dict) -> float:
    """Score composite : poids × jours_depuis_use × boost_saison × jitter."""
    days   = _days_since_last_use(niche, last_used)
    weight = data.get("_weights", {}).get(niche, 1.0)
    boost  = 2.0 if niche in boosted else 1.0
    jitter = random.uniform(0.8, 1.2)
    return days * weight * boost * jitter


def pick_niche(verbose: bool = True) -> str:
    """
    Sélectionne automatiquement la meilleure niche unique.
    """
    data      = _load()
    niches    = data.get("niches", [])
    if not niches:
        raise ValueError("Aucune niche définie dans niche_strategy.json")

    last_used = data.get("last_used", {})
    boosted   = _current_season(data)

    scores = {n: _score(n, data, boosted, last_used) for n in niches}
    chosen = max(scores, key=scores.__getitem__)

    if verbose:
        month = datetime.now().month
        print(f"\n🎯 Niche sélectionnée automatiquement : {chosen}")
        print(f"   📅 Mois : {month}   |   🔥 Niches en saison : {boosted[:3]}...")
        if chosen in boosted:
            print(f"   ⬆️  Boost saisonnier ×2 actif")
        last = last_used.get(chosen)
        print(f"   ⏱  Dernière utilisation : {last or 'jamais'}")
        top5 = sorted(scores.items(), key=lambda x: -x[1])[:5]
        print(f"   🏆 Top 5 scores : { {k: round(v, 0) for k, v in top5} }")

    return chosen


def pick_niche_multi(n: int = 3, verbose: bool = True) -> list[str]:
    """
    Retourne les N meilleures niches selon score composite.
    Utilisé pour générer un batch diversifié en un seul run.
    """
    data      = _load()
    niches    = data.get("niches", [])
    last_used = data.get("last_used", {})
    boosted   = _current_season(data)

    scores = {ni: _score(ni, data, boosted, last_used) for ni in niches}
    top    = sorted(scores, key=scores.__getitem__, reverse=True)[:n]

    if verbose:
        month = datetime.now().month
        print(f"\n🎯 Top {n} niches sélectionnées pour le mois {month} :")
        for i, ni in enumerate(top, 1):
            flag = "⬆️ saisonnière" if ni in boosted else ""
            w    = data.get("_weights", {}).get(ni, 1.0)
            print(f"   {i}. {ni} (score {round(scores[ni], 0):.0f}  |  poids {w}) {flag}")

    return top


def mark_used(niche: str) -> None:
    """Enregistre la date d'utilisation de la niche dans niche_strategy.json."""
    data = _load()
    data.setdefault("last_used", {})[niche] = datetime.now().isoformat()
    _save(data)


if __name__ == "__main__":
    # Test rapide
    print("=== Test niche_selector ===")
    top3 = pick_niche_multi(n=3)
    print(f"\nNiches choisies : {top3}")
