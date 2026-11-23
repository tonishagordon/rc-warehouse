"""
One Cast, Four Shows: a data story built on the Reality Competition Warehouse.

Two pages, both dark and editorial:
- The story (story.py): five findings, quick facts and a look-anyone-up explorer.
- The crystal ball (predictions.py): three predictive models, one tab each.

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
     st.Page("predictions.py", title="The crystal ball", url_path="predictions")],
    position="top",
)
page.run()
