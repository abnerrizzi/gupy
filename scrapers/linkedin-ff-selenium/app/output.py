import json
import logging
import os
from datetime import datetime, timezone
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


def write_json_output(
    jobs: List[Dict[str, Any]],
    keywords: str,
    location: str,
    output_dir: str,
) -> str:
    os.makedirs(output_dir, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    filename = f"linkedin_{ts}.json"
    filepath = os.path.join(output_dir, filename)

    envelope = {
        "session_id": ts,
        "scraped_at": datetime.now(timezone.utc).isoformat(),
        "keywords": keywords,
        "location": location,
        "total_jobs": len(jobs),
        "jobs": jobs,
    }

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(envelope, f, ensure_ascii=False, indent=2)

    logger.info("JSON output written: %s (%d jobs)", filepath, len(jobs))
    return filepath
