"""
AutoGrader+ | File-Based Storage System
No database. Uses: folders + CSV + JSON.

Folder structure:
  data/
  ├── uploads/
  │   ├── {session_id}/
  │   │   ├── q{n}_{student_id}.{ext}
  │   │   └── manifest.json
  ├── results/
  │   ├── {session_id}/
  │   │   ├── scores.csv
  │   │   ├── details.json
  │   │   └── report.html
  ├── sessions.json          ← index of all sessions
  └── analytics_cache.json  ← aggregated stats
"""

import csv
import json
import shutil
import hashlib
from datetime import datetime
from pathlib import Path
from typing import Optional
import pandas as pd

from evaluation_engine import StudentResult, ScoreBreakdown


# ─────────────────────────────────────────────
# PATHS
# ─────────────────────────────────────────────

BASE_DIR      = Path("data")
UPLOADS_DIR   = BASE_DIR / "uploads"
RESULTS_DIR   = BASE_DIR / "results"
SESSIONS_FILE = BASE_DIR / "sessions.json"
CACHE_FILE    = BASE_DIR / "analytics_cache.json"

for d in (UPLOADS_DIR, RESULTS_DIR):
    d.mkdir(parents=True, exist_ok=True)


# ─────────────────────────────────────────────
# SESSION MANAGER
# ─────────────────────────────────────────────

class SessionManager:
    """Creates and tracks grading sessions."""

    def create_session(self, name: str = None) -> str:
        ts  = datetime.now().strftime("%Y%m%d_%H%M%S")
        sid = f"session_{ts}"
        if name:
            safe = "".join(c if c.isalnum() or c in "-_" else "_" for c in name)
            sid  = f"{safe}_{ts}"

        (UPLOADS_DIR / sid).mkdir(parents=True, exist_ok=True)
        (RESULTS_DIR / sid).mkdir(parents=True, exist_ok=True)

        meta = {
            "session_id": sid,
            "name": name or sid,
            "created_at": datetime.now().isoformat(),
            "status": "in_progress",
            "student_count": 0,
            "question_count": 0,
        }
        self._update_index(sid, meta)
        return sid

    def get_session(self, session_id: str) -> Optional[dict]:
        sessions = self._load_index()
        return sessions.get(session_id)

    def list_sessions(self) -> list:
        return list(self._load_index().values())

    def finalize_session(self, session_id: str, stats: dict):
        sessions = self._load_index()
        if session_id in sessions:
            sessions[session_id].update({
                "status": "completed",
                "finalized_at": datetime.now().isoformat(),
                **stats
            })
            self._save_index(sessions)

    def _load_index(self) -> dict:
        if SESSIONS_FILE.exists():
            return json.loads(SESSIONS_FILE.read_text())
        return {}

    def _save_index(self, data: dict):
        SESSIONS_FILE.write_text(json.dumps(data, indent=2))

    def _update_index(self, sid: str, meta: dict):
        sessions = self._load_index()
        sessions[sid] = meta
        self._save_index(sessions)


# ─────────────────────────────────────────────
# FILE SAVER
# ─────────────────────────────────────────────

class FileSaver:
    """Handles saving uploads and results."""

    def save_upload(self, session_id: str, file_bytes: bytes,
                    filename: str, student_id: str,
                    question_id: str) -> Path:
        """
        Save uploaded file.
        Naming: q{question_id}_{student_id}{ext}
        """
        ext   = Path(filename).suffix.lower()
        safe  = _safe_name(student_id)
        fname = f"q{question_id}_{safe}{ext}"
        dest  = UPLOADS_DIR / session_id / fname
        dest.write_bytes(file_bytes)
        self._update_manifest(session_id, fname, {
            "original_name": filename,
            "student_id": student_id,
            "question_id": question_id,
            "saved_at": datetime.now().isoformat(),
            "size_bytes": len(file_bytes),
        })
        return dest

    def save_results(self, sid, results):
        import pandas as pd
        from pathlib import Path

        save_dir = Path("data/results") / sid
        save_dir.mkdir(parents=True, exist_ok=True)

        rows = []

        for r in results:
            rows.append({
                "student_id": r.student_id,
                "question_id": r.question_id,
                "marks_awarded": r.scores.marks_awarded,
                "max_marks": r.scores.max_marks,
                "final_score": r.scores.final_score,
                "similarity_score": r.scores.similarity_score,
                "keyword_score": r.scores.keyword_score,
                "length_score": r.scores.length_score,
                "diagram_score": r.scores.diagram_score,
                "has_diagram": r.has_diagram,
                "vlm_model": r.vlm_model
            })

        # ✅ prevent empty CSV crash
        if not rows:
            return

        df = pd.DataFrame(rows)
        df.to_csv(save_dir / "scores.csv", index=False)

    def _update_manifest(self, session_id: str, fname: str, meta: dict):
        manifest_path = UPLOADS_DIR / session_id / "manifest.json"
        manifest = {}
        if manifest_path.exists():
            manifest = json.loads(manifest_path.read_text())
        manifest[fname] = meta
        manifest_path.write_text(json.dumps(manifest, indent=2))


# ─────────────────────────────────────────────
# RESULT RETRIEVER
# ─────────────────────────────────────────────

class ResultRetriever:
    """Reads past results from files."""

    def load_scores(self, session_id: str) -> Optional[pd.DataFrame]:
        p = RESULTS_DIR / session_id / "scores.csv"
        if not p.exists():
            return None
        return pd.read_csv(p)

    def load_details(self, session_id: str) -> Optional[list]:
        p = RESULTS_DIR / session_id / "details.json"
        if not p.exists():
            return None
        return json.loads(p.read_text())

    def load_all_scores(self) -> pd.DataFrame:
        """Aggregate all sessions into one DataFrame."""
        frames = []
        for session_dir in RESULTS_DIR.iterdir():
            csv_p = session_dir / "scores.csv"
            if csv_p.exists():
                try:
                    df = pd.read_csv(csv_p)
                    if df.empty:
                        continue
                except:
                    continue
                df["session_id"] = session_dir.name
                frames.append(df)
        if frames:
            return pd.concat(frames, ignore_index=True)
        return pd.DataFrame()

    def get_upload_path(self, session_id: str,
                        student_id: str, question_id: str) -> Optional[Path]:
        base = UPLOADS_DIR / session_id
        safe = _safe_name(student_id)
        for ext in (".pdf", ".png", ".jpg", ".jpeg", ".tiff"):
            p = base / f"q{question_id}_{safe}{ext}"
            if p.exists():
                return p
        return None

    def list_uploads(self, session_id: str) -> list:
        manifest_path = UPLOADS_DIR / session_id / "manifest.json"
        if manifest_path.exists():
            return list(json.loads(manifest_path.read_text()).values())
        return []


# ─────────────────────────────────────────────
# ANALYTICS ENGINE
# ─────────────────────────────────────────────

class AnalyticsEngine:
    """Pandas-based analytics. No database."""

    def compute(self, df: pd.DataFrame) -> dict:
        if df.empty:
            return {}

        numeric_cols = ["final_score", "similarity_score",
                        "keyword_score", "length_score", "marks_awarded"]
        for c in numeric_cols:
            if c in df.columns:
                df[c] = pd.to_numeric(df[c], errors="coerce")

        stats = {
            "total_students":  int(df["student_id"].nunique()),
            "total_questions": int(df["question_id"].nunique()) if "question_id" in df.columns else 0,
            "class_average":   round(float(df["final_score"].mean()), 2) if "final_score" in df.columns else 0,
            "highest_score":   round(float(df["final_score"].max()), 2) if "final_score" in df.columns else 0,
            "lowest_score":    round(float(df["final_score"].min()), 2) if "final_score" in df.columns else 0,
            "std_dev":         round(float(df["final_score"].std()), 2) if "final_score" in df.columns else 0,
            "pass_rate":       self._pass_rate(df),
            "weak_questions":  self._weak_questions(df),
            "top_students":    self._top_students(df),
            "score_distribution": self._distribution(df),
        }
        return stats

    def _pass_rate(self, df: pd.DataFrame, pass_threshold: float = 50.0) -> float:
        if "final_score" not in df.columns:
            return 0.0
        passing = (df["final_score"] >= pass_threshold).sum()
        return round(passing / len(df) * 100, 1)

    def _weak_questions(self, df: pd.DataFrame) -> list:
        if "question_id" not in df.columns or "final_score" not in df.columns:
            return []
        q_avg = (df.groupby("question_id")["final_score"]
                   .mean()
                   .sort_values()
                   .head(3))
        return [{"question": str(q), "avg_score": round(float(s), 2)}
                for q, s in q_avg.items()]

    def _top_students(self, df: pd.DataFrame) -> list:
        if "student_id" not in df.columns or "final_score" not in df.columns:
            return []
        s_avg = (df.groupby("student_id")["final_score"]
                   .mean()
                   .sort_values(ascending=False)
                   .head(5))
        return [{"student": str(s), "avg_score": round(float(v), 2)}
                for s, v in s_avg.items()]

    def _distribution(self, df: pd.DataFrame) -> dict:
        if "final_score" not in df.columns:
            return {}
        bins = {"0-20": 0, "21-40": 0, "41-60": 0, "61-80": 0, "81-100": 0}
        for score in df["final_score"].dropna():
            if score <= 20:   bins["0-20"] += 1
            elif score <= 40: bins["21-40"] += 1
            elif score <= 60: bins["41-60"] += 1
            elif score <= 80: bins["61-80"] += 1
            else:             bins["81-100"] += 1
        return bins


# ─────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────

def _safe_name(name: str) -> str:
    return "".join(c if c.isalnum() else "_" for c in name)[:32]


def _result_to_row(r: StudentResult) -> dict:
    s = r.scores
    return {
        "student_id":       r.student_id,
        "question_id":      r.question_id,
        "marks_awarded":    s.marks_awarded,
        "max_marks":        s.max_marks,
        "final_score":      s.final_score,
        "similarity_score": s.similarity_score,
        "keyword_score":    s.keyword_score,
        "length_score":     s.length_score,
        "diagram_score":    s.diagram_score,
        "ocr_confidence":   s.ocr_confidence,
        "ocr_method":       r.ocr_method,
        "vlm_model":        r.vlm_model,
        "has_diagram":      r.has_diagram,
        "graded_at":        datetime.now().isoformat(),
    }


def _result_to_dict(r: StudentResult) -> dict:
    return {
        **_result_to_row(r),
        "raw_text":       r.raw_text,
        "vlm_description": r.vlm_desc,
        "feedback":       r.scores.feedback,
        "matched_keywords": r.scores.matched_keywords,
        "missing_keywords": r.scores.missing_keywords,
    }
