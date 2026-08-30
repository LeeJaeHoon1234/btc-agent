# Model artifacts

Production model artifacts are intentionally not fabricated or committed here.
Run `python scripts/train_model.py` against real historical Upbit data to create:

- `btc_lgbm.joblib`
- `btc_lgbm_metadata.json`

The runtime is designed to remain available when these files are missing; ML is then marked unavailable and the deterministic fallback path is used.
