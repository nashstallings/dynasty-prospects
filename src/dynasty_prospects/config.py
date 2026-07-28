"""Project-wide configuration for the dynasty prospects pipeline."""

PROJECT_ID = "ff-python-api"        # your GCP project
DATASET_ID = "dynasty_prospects"    # BigQuery dataset for this pipeline
DRAFT_CLASS = 2027

# College seasons of production to pull (most recent years of tape per player)
CFBD_SEASONS = [2024, 2025, 2026]

# HS recruiting classes to cover (players draft-eligible in 2027 mostly recruited 2021-2024)
RECRUITING_CLASS_YEARS = [2021, 2022, 2023, 2024]
