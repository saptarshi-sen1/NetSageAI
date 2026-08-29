import json
import logging
from pathlib import Path
from typing import Optional, Dict, Any

from backend.ai.diagnosis import DiagnosisResult
from backend.ai.schemas import AIDiagnosis
from backend.rules.models import Finding

DATA_DIR = Path("data")
CACHE_FILE = DATA_DIR / "diagnoses.json"

logger = logging.getLogger(__name__)

def _load_cache() -> Dict[str, Any]:
    if not CACHE_FILE.exists():
        return {}
    try:
        with open(CACHE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Failed to load diagnosis cache: {e}")
        return {}

def _save_cache(data: Dict[str, Any]) -> None:
    try:
        DATA_DIR.mkdir(exist_ok=True)
        with open(CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        logger.error(f"Failed to save diagnosis cache: {e}")

def get_cached(case_id: str) -> Optional[DiagnosisResult]:
    cache = _load_cache()
    if case_id not in cache:
        return None
    
    entry = cache[case_id]
    try:
        diagnosis = AIDiagnosis.model_validate(entry["ai_diagnosis"])
        findings = [Finding.from_dict(f) if hasattr(Finding, 'from_dict') else Finding(**f) for f in entry["rule_findings"]]
        
        return DiagnosisResult(
            case_id=case_id,
            ai_diagnosis=diagnosis,
            rule_findings=findings,
            mock_mode=entry.get("mock_mode", False),
            model_used=entry.get("model_used"),
            raw_response=entry.get("raw_response"),
            fallback_occurred=entry.get("fallback_occurred", False)
        )
    except Exception as e:
        logger.warning(f"Failed to deserialize cached diagnosis for {case_id}: {e}")
        return None

def save_to_cache(case_id: str, result: DiagnosisResult) -> None:
    if not result.ai_diagnosis or result.error:
        return # Don't cache errors
        
    cache = _load_cache()
    cache[case_id] = {
        "model_used": result.model_used,
        "mock_mode": result.mock_mode,
        "ai_diagnosis": result.ai_diagnosis.model_dump(),
        "rule_findings": [f.to_dict() if hasattr(f, 'to_dict') else f.__dict__ for f in result.rule_findings],
        "raw_response": result.raw_response,
        "fallback_occurred": result.fallback_occurred
    }
    _save_cache(cache)
