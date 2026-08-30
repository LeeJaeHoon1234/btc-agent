import os
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "data"
MODEL_DIR = DATA_DIR / "models"
MODEL_PATH = MODEL_DIR / "btc_lgbm.joblib"
MODEL_METADATA_PATH = MODEL_DIR / "btc_lgbm_metadata.json"

MARKET = os.getenv("BTC_MARKET", "KRW-BTC")
HISTORY_YEARS = int(os.getenv("BTC_HISTORY_YEARS", "8"))

OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-5.6")
USE_LLM = os.getenv("USE_LLM", "true").lower() in {"1", "true", "yes", "y"}

MAX_CRITIC_ITERATIONS = int(os.getenv("MAX_CRITIC_ITERATIONS", "2"))
SIMILARITY_TOP_K = int(os.getenv("SIMILARITY_TOP_K", "5"))
SIMILARITY_EXCLUDE_RECENT_DAYS = int(
    os.getenv("SIMILARITY_EXCLUDE_RECENT_DAYS", "90")
)
