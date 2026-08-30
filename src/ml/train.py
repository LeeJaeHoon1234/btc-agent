from datetime import datetime

import pandas as pd
from lightgbm import LGBMClassifier
from sklearn.metrics import accuracy_score, roc_auc_score

from src.ml.features import MODEL_FEATURE_NAMES


def create_model() -> LGBMClassifier:
    return LGBMClassifier(
        n_estimators=200,
        learning_rate=0.03,
        max_depth=3,
        random_state=42,
        verbosity=-1,
    )


def walk_forward_validate(dataset: pd.DataFrame) -> pd.DataFrame:
    df = dataset.copy()
    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values("date").reset_index(drop=True)

    results: list[dict] = []

    for test_year in sorted(df["date"].dt.year.unique()):
        train_df = df[df["date"].dt.year < test_year]
        test_df = df[df["date"].dt.year == test_year]

        if len(train_df) < 300:
            continue
        if test_df["target_up_30d"].nunique() < 2:
            continue

        model = create_model()
        model.fit(train_df[MODEL_FEATURE_NAMES], train_df["target_up_30d"])

        pred = model.predict(test_df[MODEL_FEATURE_NAMES])
        proba = model.predict_proba(test_df[MODEL_FEATURE_NAMES])[:, 1]

        results.append(
            {
                "test_year": int(test_year),
                "train_count": int(len(train_df)),
                "test_count": int(len(test_df)),
                "accuracy": float(accuracy_score(test_df["target_up_30d"], pred)),
                "auc": float(roc_auc_score(test_df["target_up_30d"], proba)),
                "actual_up_rate": float(test_df["target_up_30d"].mean()),
                "predicted_up_rate": float(pred.mean()),
            }
        )

    return pd.DataFrame(results)


def train_final_model(dataset: pd.DataFrame):
    df = dataset.copy().sort_values("date").reset_index(drop=True)
    model = create_model()
    model.fit(df[MODEL_FEATURE_NAMES], df["target_up_30d"])
    return model


def build_model_metadata(dataset: pd.DataFrame, wf_results: pd.DataFrame) -> dict:
    by_year = {}
    if not wf_results.empty:
        by_year = {
            str(int(row["test_year"])): {
                "accuracy": float(row["accuracy"]),
                "auc": float(row["auc"]),
                "test_count": int(row["test_count"]),
            }
            for _, row in wf_results.iterrows()
        }

    mean_auc = None if wf_results.empty else float(wf_results["auc"].mean())
    mean_accuracy = None if wf_results.empty else float(wf_results["accuracy"].mean())

    return {
        "trained_at": datetime.now().isoformat(timespec="seconds"),
        "trained_until": str(pd.to_datetime(dataset["date"]).max()),
        "sample_count": int(len(dataset)),
        "features": MODEL_FEATURE_NAMES,
        "walk_forward_mean_auc": mean_auc,
        "walk_forward_mean_accuracy": mean_accuracy,
        "walk_forward_by_year": by_year,
    }
