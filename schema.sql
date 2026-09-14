PRAGMA foreign_keys = ON;

CREATE TABLE subjects (
    subject_id TEXT PRIMARY KEY,
    project TEXT NOT NULL,
    indication TEXT NOT NULL,
    age INTEGER NOT NULL CHECK (age >= 0),
    gender TEXT NOT NULL CHECK (gender IN ('M', 'F')),
    treatment TEXT NOT NULL,
    response TEXT CHECK (response IN ('yes', 'no') OR response IS NULL),
    UNIQUE (project, subject_id)
);

CREATE TABLE samples (
    sample_id TEXT PRIMARY KEY,
    subject_id TEXT NOT NULL REFERENCES subjects(subject_id),
    sample_type TEXT NOT NULL,
    time_from_treatment_start REAL NOT NULL,
    UNIQUE (subject_id, sample_type, time_from_treatment_start)
);

CREATE TABLE cell_counts (
    sample_id TEXT NOT NULL REFERENCES samples(sample_id) ON DELETE CASCADE,
    population TEXT NOT NULL CHECK (population IN
        ('b_cell', 'cd8_t_cell', 'cd4_t_cell', 'nk_cell', 'monocyte')),
    count INTEGER NOT NULL CHECK (count >= 0),
    PRIMARY KEY (sample_id, population)
);

CREATE INDEX idx_subject_trial ON subjects(indication, treatment, response);
CREATE INDEX idx_sample_subset ON samples(sample_type, time_from_treatment_start);

CREATE VIEW cell_frequency_summary AS
SELECT c.sample_id AS sample,
       SUM(c.count) OVER (PARTITION BY c.sample_id) AS total_count,
       c.population,
       c.count,
       100.0 * c.count /
           NULLIF(SUM(c.count) OVER (PARTITION BY c.sample_id), 0) AS percentage
FROM cell_counts AS c;
