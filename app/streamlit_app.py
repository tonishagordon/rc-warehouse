"""
One Cast, Four Shows: a data story built on the Reality Competition Warehouse.

Four pages, all dark and editorial:
- The story (story.py): five findings and quick facts.
- Game moves (moves.py): idols, votes and competition wins vs. results.
- The crystal ball (predictions.py): three predictive models, one tab each.
- Look anyone up (explorer.py): any player's whole career.

Reads the Parquet exports of the dbt marts (data/marts/), so it runs anywhere
without the pipeline. Rebuild them with: bash scripts/build_warehouse.sh
Run locally (from the repo root): streamlit run app/streamlit_app.py
"""

import streamlit as st

from common import inject_css

st.set_page_config(page_title="One Cast, Four Shows", layout="centered")
inject_css()

page = st.navigation(
    [st.Page("story.py", title="The story", default=True),
     st.Page("moves.py", title="Game moves", url_path="moves"),
     st.Page("predictions.py", title="The crystal ball", url_path="predictions"),
     st.Page("explorer.py", title="Look anyone up", url_path="lookup")],
    position="top",
)
page.run()
