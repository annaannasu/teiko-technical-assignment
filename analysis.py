"""Run Parts 2-4 from SQLite and write reproducible result files."""
from __future__ import annotations

import sqlite3
from pathlib import Path

import pandas as pd
from scipy.stats import ttest_ind
from statsmodels.stats.multitest import multipletests

ROOT = Path(__file__).resolve().parent
DB_PATH = ROOT / "cell_counts.db"
OUTPUT = ROOT / "outputs"


def query_frame(connection: sqlite3.Connection, sql: str) -> pd.DataFrame:
    return pd.read_sql_query(sql, connection)


def trial_frequencies(connection: sqlite3.Connection) -> pd.DataFrame:
    return query_frame(connection, """
        SELECT f.*, s.subject_id, u.response
        FROM cell_frequency_summary f
        JOIN samples s ON s.sample_id = f.sample
        JOIN subjects u ON u.subject_id = s.subject_id
        WHERE lower(u.indication) = 'melanoma'
          AND lower(u.treatment) = 'miraclib'
          AND upper(s.sample_type) = 'PBMC'
          AND u.response IN ('yes', 'no')
    """)


def statistical_tests(data: pd.DataFrame) -> pd.DataFrame:
    # A patient is the independent experimental unit. Average repeated timepoints
    # before testing to avoid treating repeated samples as independent patients.
    subject = (data.groupby(["subject_id", "response", "population"], as_index=False)
                   ["percentage"].mean())
    rows = []
    for population, group in subject.groupby("population"):
        responders = group.loc[group.response == "yes", "percentage"]
        nonresponders = group.loc[group.response == "no", "percentage"]
        # Welch's two-sided t-test does not assume equal group variances.
        statistic, p_value = ttest_ind(
            responders, nonresponders, equal_var=False, alternative="two-sided"
        )
        rows.append({
            "population": population,
            "responders_n": len(responders),
            "nonresponders_n": len(nonresponders),
            "responders_mean_pct": responders.mean(),
            "nonresponders_mean_pct": nonresponders.mean(),
            "mean_difference_pct_points": responders.mean() - nonresponders.mean(),
            "welch_t_statistic": statistic,
            "p_value": p_value,
        })
    result = pd.DataFrame(rows)
    result["p_value_bh"] = multipletests(result.p_value, method="fdr_bh")[1]
    result["significant_fdr_0_05"] = result.p_value_bh < 0.05
    return result.sort_values("p_value_bh")


def main() -> None:
    if not DB_PATH.exists():
        raise FileNotFoundError("Run `python load_data.py` first.")
    OUTPUT.mkdir(exist_ok=True)
    with sqlite3.connect(DB_PATH) as connection:
        summary = query_frame(connection, "SELECT * FROM cell_frequency_summary ORDER BY sample, population")
        trial = trial_frequencies(connection)
        stats = statistical_tests(trial)
        baseline = query_frame(connection, """
            SELECT u.project, s.subject_id, s.sample_id, u.response, u.gender
            FROM samples s JOIN subjects u ON u.subject_id = s.subject_id
            WHERE lower(u.indication)='melanoma' AND lower(u.treatment)='miraclib'
              AND upper(s.sample_type)='PBMC' AND s.time_from_treatment_start=0
        """)
        subjects = baseline.drop_duplicates("subject_id")
        part4 = pd.DataFrame({
            "metric": ["baseline_samples", "responders", "non_responders", "female", "male"],
            "value": [len(baseline), (subjects.response == "yes").sum(),
                      (subjects.response == "no").sum(), (subjects.gender == "F").sum(),
                      (subjects.gender == "M").sum()],
        })
        projects = baseline.groupby("project").size().rename("sample_count").reset_index()
        answer = query_frame(connection, """
            SELECT AVG(c.count) AS average_b_cells
            FROM cell_counts c JOIN samples s ON s.sample_id=c.sample_id
            JOIN subjects u ON u.subject_id=s.subject_id
            WHERE c.population='b_cell' AND lower(u.indication)='melanoma'
              AND u.gender='M' AND u.response='yes' AND s.time_from_treatment_start=0
        """).iloc[0, 0]
    summary.to_csv(OUTPUT / "cell_frequency_summary.csv", index=False)
    stats.to_csv(OUTPUT / "response_statistics.csv", index=False)
    part4.to_csv(OUTPUT / "baseline_counts.csv", index=False)
    projects.to_csv(OUTPUT / "baseline_projects.csv", index=False)
    (OUTPUT / "required_answer.txt").write_text(f"{answer:.2f}\n")
    print(stats.to_string(index=False))
    print(f"\nRequired form answer: {answer:.2f}")


if __name__ == "__main__":
    main()
