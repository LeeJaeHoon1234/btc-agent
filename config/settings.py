import os
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "data"
MODEL_DIR = DATA_DIR / "models"
MODEL_PATH = MODEL_DIR / "btc_lgbm.joblib"
MODEL_METADATA_PATH = MODEL_DIR / "btc_lgbm_metadata.json"

MARKET = os.getenv("BTC_MARKET", "KRW-BTC")
HISTORY_YEARS = int(os.getenv("BTC_HISTORY_YEARS", "8"))

OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-5.6-terra")
USE_LLM = os.getenv("USE_LLM", "true").lower() in {"1", "true", "yes", "y"}

MAX_CRITIC_ITERATIONS = int(os.getenv("MAX_CRITIC_ITERATIONS", "2"))
SIMILARITY_TOP_K = int(os.getenv("SIMILARITY_TOP_K", "5"))
SIMILARITY_EXCLUDE_RECENT_DAYS = int(
    os.getenv("SIMILARITY_EXCLUDE_RECENT_DAYS", "90")
)

# V3 research layer
RESEARCH_TIMEOUT_SECONDS = int(os.getenv("RESEARCH_TIMEOUT_SECONDS", "8"))

USE_SPECIALIST_LLM = os.getenv("USE_SPECIALIST_LLM", "true").lower() in {"1", "true", "yes", "y"}

# V3.1 public-service cost and abuse guard
COST_GUARD_ENABLED = os.getenv("COST_GUARD_ENABLED", "true").lower() in {"1", "true", "yes", "y"}
IP_HOURLY_REQUEST_LIMIT = int(os.getenv("IP_HOURLY_REQUEST_LIMIT", "6"))
IP_DAILY_REQUEST_LIMIT = int(os.getenv("IP_DAILY_REQUEST_LIMIT", "10"))
IP_DAILY_LLM_ANALYSIS_LIMIT = int(os.getenv("IP_DAILY_LLM_ANALYSIS_LIMIT", "3"))
GLOBAL_DAILY_LLM_ANALYSIS_LIMIT = int(os.getenv("GLOBAL_DAILY_LLM_ANALYSIS_LIMIT", "30"))
MAX_LLM_CALLS_PER_ANALYSIS = int(os.getenv("MAX_LLM_CALLS_PER_ANALYSIS", "8"))
MAX_LLM_TOKENS_PER_ANALYSIS = int(os.getenv("MAX_LLM_TOKENS_PER_ANALYSIS", "30000"))
