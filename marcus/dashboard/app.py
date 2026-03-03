from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import pandas as pd
import streamlit as st

from marcus.config.marketplaces import ALL_MARKETPLACES
from marcus.config.settings import DB_PATH
from marcus.core.models import Database

st.set_page_config(
    page_title="Marcus - Product Research",
    page_icon="📦",
    layout="wide",
)


@st.cache_resource
def get_db() -> Database:
    return Database(DB_PATH)


def main():
    st.title("Marcus")
    st.caption("Recherche de produits Marketplace")

    db = get_db()

    tab_opps, tab_products, tab_history = st.tabs(["Opportunités", "Produits", "Historique"])

    with tab_opps:
        render_opportunities(db)

    with tab_products:
        render_products(db)

    with tab_history:
        render_price_history(db)


def render_opportunities(db: Database):
    st.header("Opportunités")

    col1, col2 = st.columns(2)
    with col1:
        min_score = st.slider("Score minimum", 0.0, 100.0, 40.0, 5.0)
    with col2:
        limit = st.selectbox("Nombre max", [25, 50, 100, 200], index=1)

    rows = db.get_opportunities(min_score=min_score, limit=limit)

    if not rows:
        st.info("Aucune opportunité trouvée. Lance une recherche avec `python -m marcus.main search`.")
        return

    df = pd.DataFrame(rows)

    col_score, col_count, col_avg = st.columns(3)
    col_score.metric("Meilleur score", f"{df['score'].max():.1f}")
    col_count.metric("Total", len(df))
    col_avg.metric("Score moyen", f"{df['score'].mean():.1f}")

    display_cols = [c for c in ["asin", "title", "brand", "price", "category", "score",
                                "margin_score", "competition_score", "demand_score",
                                "bsr_score", "estimated_margin_pct"] if c in df.columns]

    st.dataframe(
        df[display_cols].style.background_gradient(subset=["score"], cmap="RdYlGn"),
        use_container_width=True,
        hide_index=True,
    )


def render_products(db: Database):
    st.header("Produits")

    marketplace_names = ["Tous"] + [m.code for m in ALL_MARKETPLACES]
    selected = st.selectbox("Marketplace", marketplace_names)
    marketplace = None if selected == "Tous" else selected

    rows = db.get_products(marketplace=marketplace, limit=200)

    if not rows:
        st.info("Aucun produit en base.")
        return

    df = pd.DataFrame(rows)
    st.dataframe(df, use_container_width=True, hide_index=True)


def render_price_history(db: Database):
    st.header("Historique des prix")

    asin = st.text_input("ASIN du produit")
    marketplace_codes = [m.code for m in ALL_MARKETPLACES]
    marketplace = st.selectbox("Marketplace", marketplace_codes, key="history_mp")

    if not asin:
        st.info("Entre un ASIN pour voir l'historique des prix.")
        return

    rows = db.get_price_history(asin, marketplace)
    if not rows:
        st.warning(f"Aucun historique pour {asin} sur {marketplace}.")
        return

    df = pd.DataFrame(rows)
    df["date"] = pd.to_datetime(df["date"])
    st.line_chart(df.set_index("date")["price"])


if __name__ == "__main__":
    main()
