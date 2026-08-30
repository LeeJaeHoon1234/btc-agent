from config.settings import MODEL_METADATA_PATH, MODEL_PATH
from src.ml.features import latest_feature_frame
from src.ml.model_store import load_metadata, load_model


def predict_latest(df) -> dict:
    metadata = load_metadata(MODEL_METADATA_PATH)

    try:
        model = load_model(MODEL_PATH)
    except FileNotFoundError as e:
        return {
            "available": False,
            "up_probability": None,
            "metadata": metadata,
            "message": str(e),
        }

    x_latest = latest_feature_frame(df)
    probability = float(model.predict_proba(x_latest)[0][1] * 100)

    return {
        "available": True,
        "up_probability": probability,
        "metadata": metadata,
    }
