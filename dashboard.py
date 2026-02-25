import streamlit as st
import pandas as pd
from pathlib import Path
import os
from dotenv import load_dotenv

# Load config
load_dotenv()
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"

st.set_page_config(page_title="Pinterest Autopilot Dashboard", page_icon="📌", layout="wide")

st.title("📌 Pinterest Autopilot - Dashboard")
st.markdown("Suivez la génération de vos épingles, vos quotas API et vos publications automatiques.")
st.markdown("---")

col1, col2, col3 = st.columns(3)

# Load data
ideas_file = DATA_DIR / "pins_ideas_to_fill.csv"
published_file = DATA_DIR / "pins_input.csv"

ideas_count = 0
if ideas_file.exists():
    df_ideas = pd.read_csv(ideas_file)
    ideas_count = len(df_ideas)

pub_count = 0
if published_file.exists():
    df_pub = pd.read_csv(published_file)
    pub_count = len(df_pub)

col1.metric("Idées en attente", f"{ideas_count} 💡")
col2.metric("Pins Prêts/Publiés", f"{pub_count} ✅")

# Keys status
hf_key = bool(os.getenv("HF_TOKEN"))
together_key = bool(os.getenv("TOGETHER_API_KEY"))

status_text = f"HF: {'✅' if hf_key else '❌'} | Together: {'✅' if together_key else '❌'}"
col3.metric("Clés API Détectées", status_text)

if not together_key:
    st.warning("⚠️ La clé `TOGETHER_API_KEY` est manquante dans votre fichier `.env`. Le bot utilisera Hugging Face par défaut, ce qui peut épuiser rapidement votre quota gratuit.")

st.markdown("---")

st.subheader("📝 Idées générées (Flux Pinterest)")
if ideas_file.exists():
    st.dataframe(df_ideas, use_container_width=True)
else:
    st.info("Aucune idée générée pour le moment. Lancez `01_generate_ideas.sh`.")

st.subheader("✅ Catalogue de Pins (Prêts & Publiés)")
if published_file.exists():
    st.dataframe(df_pub, use_container_width=True)
else:
    st.info("Aucun pin dans le catalogue pour le moment.")
