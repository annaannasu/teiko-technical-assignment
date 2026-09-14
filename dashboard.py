from __future__ import annotations

import sqlite3
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

from analysis import statistical_tests, trial_frequencies

ROOT = Path(__file__).resolve().parent
DB_PATH = ROOT / "cell_counts.db"

st.set_page_config(page_title="Loblaw Bio Immune Cell Analysis", layout="wide")
st.title("Loblaw Bio · Immune Cell Analysis")
import load_data
load_data.main()


def sql(query: str) -> pd.DataFrame:
    with sqlite3.connect(DB_PATH) as connection:
        return pd.read_sql_query(query, connection)


tab1, tab2, tab3 = st.tabs(["Part 2 · Overview", "Part 3 · Response", "Part 4 · Baseline"])
with tab1:
    st.subheader("Cell population frequency by sample")
    summary = sql("SELECT * FROM cell_frequency_summary ORDER BY sample, population")
    sample_search = st.text_input("Filter sample ID")
    shown = summary[summary["sample"].str.contains(sample_search, case=False)] if sample_search else summary
    st.dataframe(shown, use_container_width=True, hide_index=True)
    st.download_button("Download summary CSV", summary.to_csv(index=False), "cell_frequency_summary.csv")

with tab2:
    st.subheader("Miraclib-treated melanoma PBMC samples")
    with sqlite3.connect(DB_PATH) as connection:
        trial = trial_frequencies(connection)
    response_labels = {"yes": "Responder", "no": "Non-responder"}
    trial["response_group"] = trial.response.map(response_labels)
    fig = px.box(trial, x="population", y="percentage", color="response_group",
                 points="outliers", labels={"percentage": "Relative frequency (%)",
                 "population": "Cell population", "response_group": "Response"},
                 color_discrete_map={"Responder": "#2563eb", "Non-responder": "#f97316"})
    st.plotly_chart(fig, use_container_width=True)
    stats = statistical_tests(trial)
    st.caption("Two-sided Welch t-tests on subject-level mean frequencies; Benjamini–Hochberg FDR correction across five populations.")
    st.dataframe(stats, use_container_width=True, hide_index=True)
    significant = stats.loc[stats.significant_fdr_0_05, "population"].tolist()
    st.info("Significant at FDR 5%: " + (", ".join(significant) if significant else "none"))

with tab3:
    st.subheader("Baseline melanoma PBMC · miraclib")
    baseline = sql("""
        SELECT u.project, s.subject_id, s.sample_id, u.response, u.gender
        FROM samples s JOIN subjects u ON u.subject_id=s.subject_id
        WHERE lower(u.indication)='melanoma' AND lower(u.treatment)='miraclib'
          AND upper(s.sample_type)='PBMC' AND s.time_from_treatment_start=0
    """)
    subjects = baseline.drop_duplicates("subject_id")
    a, b, c = st.columns(3)
    a.metric("Baseline samples", len(baseline))
    b.metric("Responders / non-responders", f"{(subjects.response=='yes').sum()} / {(subjects.response=='no').sum()}")
    c.metric("Female / male", f"{(subjects.gender=='F').sum()} / {(subjects.gender=='M').sum()}")
    st.write("Samples by project")
    st.dataframe(baseline.groupby("project").size().rename("samples").reset_index(), hide_index=True)
    answer = sql("""
        SELECT AVG(c.count) average_b_cells FROM cell_counts c
        JOIN samples s ON s.sample_id=c.sample_id JOIN subjects u ON u.subject_id=s.subject_id
        WHERE c.population='b_cell' AND lower(u.indication)='melanoma'
          AND u.gender='M' AND u.response='yes' AND s.time_from_treatment_start=0
    """).iloc[0, 0]
    st.success(f"Average B-cell count for male melanoma responders at time 0 (all sample/treatment types): {answer:.2f}")
    with st.expander("View matching baseline records"):
        st.dataframe(baseline, use_container_width=True, hide_index=True)
