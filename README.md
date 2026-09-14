# Teiko Technical Assignment — Immune Cell Analysis

## Running the project in GitHub Codespaces

Run these commands from the repository root:

```bash
make setup
make pipeline
make dashboard
```

Once Streamlit starts, open the forwarded port to view the dashboard. The dashboard displays the results from Parts 2–4 using the database created by the pipeline.

## Dashboard

**Hosted dashboard:** link

Running `make pipeline` rebuilds `cell_counts.db` from scratch and creates:

* `outputs/cell_frequency_summary.csv` — cell frequencies for Part 2
* `outputs/response_statistics.csv` — statistical results for Part 3
* `outputs/baseline_counts.csv` and `outputs/baseline_projects.csv` — subset results for Part 4
* `outputs/required_answer.txt` — answer to the final B-cell question

To run the tests:

```bash
make test
```

## Data model

I separated the data into three tables: `subjects`, `samples`, and `cell_counts`. Subject information is stored once per patient, while sample type and timepoint information is stored in `samples`. I used long format for `cell_counts`, with one row per sample and cell population.

The `cell_frequency_summary` view calculates the total cell count and relative frequency for each population and returns the five columns requested in Part 2.

## Statistical analysis

For Part 3, I filtered the data to PBMC samples from melanoma patients treated with miraclib who had a response of either `yes` or `no`.

Since each subject has multiple timepoints, I averaged the relative frequencies within each subject before testing so that the same patient would not be counted as multiple independent observations. I used a two-sided Welch’s t-test because it does not assume that the two response groups have equal variances. I also applied Benjamini–Hochberg correction because five cell populations were tested.

The dashboard boxplots show the original sample-level values so the distributions across all collected samples can still be viewed.
