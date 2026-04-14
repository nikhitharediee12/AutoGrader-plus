"""
AutoGrader+ | Hybrid Evaluation Engine
Combines: TF-IDF cosine similarity + keyword overlap + length scoring
         + OCR confidence weighting + VLM diagram scoring
"""

import re
import math
from dataclasses import dataclass, field
from typing import Optional

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np

from ocr_pipeline import OCRResult
from vlm_engine import VLMResult, DiagramEvaluator


# ─────────────────────────────────────────────
# DATA STRUCTURES
# ─────────────────────────────────────────────

@dataclass
class ScoreBreakdown:
    similarity_score: float      # TF-IDF cosine
    keyword_score:    float      # keyword overlap ratio
    length_score:     float      # answer length adequacy
    diagram_score:    float      # diagram/graph evaluation
    ocr_confidence:   float      # OCR quality weight
    vlm_confidence:   float      # VLM quality weight
    final_score:      float      # weighted aggregate (0–100)
    max_marks:        float
    marks_awarded:    float
    feedback:         list = field(default_factory=list)
    matched_keywords: list = field(default_factory=list)
    missing_keywords: list = field(default_factory=list)


@dataclass
class StudentResult:
    student_id:  str
    question_id: str
    raw_text:    str             # OCR extracted
    vlm_desc:    str             # VLM interpretation
    scores:      ScoreBreakdown
    ocr_method:  str
    vlm_model:   str
    has_diagram: bool


# ─────────────────────────────────────────────
# TEXT UTILITIES
# ─────────────────────────────────────────────

STOPWORDS = {
    "a", "an", "the", "is", "are", "was", "were", "be", "been",
    "being", "have", "has", "had", "do", "does", "did", "will",
    "would", "could", "should", "may", "might", "shall", "can",
    "to", "of", "in", "for", "on", "with", "at", "by", "from",
    "up", "about", "into", "through", "during", "it", "its", "this",
    "that", "these", "those", "and", "but", "or", "nor", "so", "yet",
}

def clean_text(text: str) -> str:
    text = text.lower()
    text = re.sub(r'[^a-z0-9\s]', ' ', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def extract_keywords(text: str) -> set:
    words = clean_text(text).split()
    return {w for w in words if w not in STOPWORDS and len(w) > 2}


# ─────────────────────────────────────────────
# SCORING COMPONENTS
# ─────────────────────────────────────────────

class TFIDFScorer:
    def score(self, answer: str, model_answer: str) -> float:
        if not answer.strip() or not model_answer.strip():
            return 0.0
        try:
            vec = TfidfVectorizer(stop_words="english", ngram_range=(1, 2))
            mat = vec.fit_transform([model_answer, answer])
            sim = cosine_similarity(mat[0:1], mat[1:2])[0][0]
            return float(sim)
        except Exception:
            return 0.0


class KeywordScorer:
    def score(self, answer: str, model_answer: str,
              required_keywords: list = None) -> tuple:
        """Returns (score 0–1, matched, missing)."""
        if required_keywords:
            keywords = {k.lower() for k in required_keywords}
        else:
            keywords = extract_keywords(model_answer)
            # Keep only the most informative (top 15 by length as proxy)
            keywords = set(sorted(keywords, key=len, reverse=True)[:15])

        if not keywords:
            return 1.0, [], []

        answer_words = set(clean_text(answer).split())
        matched = [k for k in keywords if k in answer_words]
        missing = [k for k in keywords if k not in answer_words]
        score = len(matched) / len(keywords)
        return score, matched, missing


class LengthScorer:
    """
    Penalizes answers that are too short; gives full credit when length
    is ≥ 60% of model answer length. No penalty for being longer.
    """
    MIN_RATIO = 0.30   # below this → 0
    FULL_RATIO = 0.60  # at/above this → 1.0

    def score(self, answer: str, model_answer: str) -> float:
        a_len = len(answer.split())
        m_len = len(model_answer.split())
        if m_len == 0:
            return 1.0
        ratio = a_len / m_len
        if ratio <= self.MIN_RATIO:
            return 0.0
        if ratio >= self.FULL_RATIO:
            return 1.0
        # Linear interpolation in [MIN_RATIO, FULL_RATIO]
        return (ratio - self.MIN_RATIO) / (self.FULL_RATIO - self.MIN_RATIO)


# ─────────────────────────────────────────────
# HYBRID EVALUATOR
# ─────────────────────────────────────────────

class HybridEvaluator:
    """
    Merges all scoring signals into a final grade.

    Weights (sum to 1.0):
        TF-IDF similarity : 0.40
        Keyword overlap   : 0.30
        Length adequacy   : 0.10
        Diagram score     : 0.20  (if diagram present, else redistributed)
    """

    W_SIM  = 0.35
    W_KEY  = 0.20
    W_LEN  = 0.25
    W_DIAG = 0.20

    def __init__(self):
        self.tfidf    = TFIDFScorer()
        self.keyword  = KeywordScorer()
        self.length   = LengthScorer()
        self.diagram  = DiagramEvaluator()

    def evaluate(
        self,
        ocr_result:       OCRResult,
        vlm_result:       Optional[VLMResult],
        model_answer:     str,
        max_marks:        float = 10.0,
        required_keywords: list = None,
        expected_elements: list = None,
    ) -> ScoreBreakdown:

        # --- merge OCR text + VLM description ---
        answer_text = self._merge_inputs(ocr_result, vlm_result)

        # --- individual scores ---
        sim_score   = self.tfidf.score(answer_text, model_answer)
        # 🔥 soften similarity
        sim_score = min(sim_score + 0.5, 1.0)
        key_score, matched, missing = self.keyword.score(
            answer_text, model_answer, required_keywords
        )
        key_score = min(key_score + 0.4, 1.0)
        len_score   = self.length.score(answer_text, model_answer)

        diag_score  = 0.0
        diag_feedback = []
        has_diagram = (
            ocr_result.has_diagram_hint or
            (vlm_result and vlm_result.diagram_type in ("graph", "diagram"))
        )

        if has_diagram and vlm_result:
            diag_eval  = self.diagram.evaluate(vlm_result, expected_elements)
            diag_score = diag_eval["diagram_score"]
            diag_feedback = diag_eval["feedback"]

        # --- weight adjustment if no diagram ---
        if not has_diagram:
            # Redistribute diagram weight to similarity
            w_sim  = self.W_SIM + self.W_DIAG * 0.6
            w_key  = self.W_KEY + self.W_DIAG * 0.4
            w_len  = self.W_LEN
            w_diag = 0.0
        else:
            w_sim, w_key, w_len, w_diag = (
                self.W_SIM, self.W_KEY, self.W_LEN, self.W_DIAG
            )

        # --- OCR confidence penalty ---
        ocr_conf   = ocr_result.confidence
        vlm_conf   = vlm_result.confidence if vlm_result else 0.0
        conf_weight = self._confidence_weight(ocr_conf, vlm_conf, has_diagram)

        raw_score = (
            w_sim  * sim_score +
            w_key  * key_score +
            w_len  * len_score +
            w_diag * diag_score
        )
        # Apply confidence dampening only when very low confidence
        adjusted = raw_score * conf_weight
        final_pct = min(adjusted, 1.0)
        # 🔥 final generosity boost
        final_pct = min(final_pct + 0.15, 1.0)
        marks = round(final_pct * max_marks, 2)
        # 🔥 minimum base marks based on answer length
        word_count = len(answer_text.split())

        if word_count > 5:
            marks = max(marks, max_marks * 0.7)

        if word_count > 15:
            marks = max(marks, max_marks * 0.85)
        
        if word_count > 30:
            marks = max(marks, max_marks * 0.95)
        # 🔥 Minimum marks safety
        if marks < 1.0 and len(answer_text.split()) > 5:
            marks = 1.0

        # --- feedback ---
        feedback = []
        if sim_score >= 0.80:  feedback.append("✓ Answer is highly similar to model answer")
        elif sim_score >= 0.55: feedback.append("~ Answer is partially aligned")
        else:                   feedback.append("✗ Low semantic similarity")

        if key_score >= 0.75:  feedback.append(f"✓ Key terms covered ({len(matched)} matched)")
        elif matched:           feedback.append(f"~ Partial keyword coverage ({len(matched)}/{len(matched)+len(missing)})")
        else:                   feedback.append("✗ Missing important keywords")

        if len_score < 0.5:    feedback.append("✗ Answer seems too short")
        elif len_score >= 0.9:  feedback.append("✓ Good answer length")

        feedback.extend(diag_feedback)

        if ocr_conf < 0.4:
            feedback.append(f"⚠ Low OCR confidence ({ocr_conf:.0%}) — handwriting unclear")

        return ScoreBreakdown(
            similarity_score=round(sim_score, 4),
            keyword_score   =round(key_score, 4),
            length_score    =round(len_score, 4),
            diagram_score   =round(diag_score, 4),
            ocr_confidence  =round(ocr_conf, 4),
            vlm_confidence  =round(vlm_conf, 4),
            final_score     =round(final_pct * 100, 2),
            max_marks       =max_marks,
            marks_awarded   =marks,
            feedback        =feedback,
            matched_keywords=matched,
            missing_keywords=missing,
        )

    def _merge_inputs(self, ocr: OCRResult,
                      vlm: Optional[VLMResult]) -> str:
        parts = []
        if ocr.text and "[DIAGRAM" not in ocr.text:
            parts.append(ocr.text)
        if vlm and vlm.description and "[VLM unavailable" not in vlm.description:
            parts.append(vlm.description)
        return " ".join(parts) if parts else ""

    def _confidence_weight(self, ocr_conf: float, vlm_conf: float,
                           has_diagram: bool) -> float:
        """
        Returns a weight in [0.6, 1.0].
        Very low confidence → slight dampening, never zero.
        """
        if has_diagram and vlm_conf > 0.5:
            return 0.85 + 0.15 * vlm_conf
        base = max(ocr_conf, vlm_conf)
        if base >= 0.6:
            return 1.0
        # Linear: 0.0 → 0.60, 0.6 → 1.0
        return 0.60 + (base / 0.6) * 0.40


# ─────────────────────────────────────────────
# BATCH GRADER
# ─────────────────────────────────────────────

class BatchGrader:
    """Grades multiple students across multiple questions."""

    def __init__(self):
        from ocr_pipeline import OCRRouter
        from vlm_engine import VLMRouter
        self.ocr     = OCRRouter()
        self.vlm     = VLMRouter()
        self.grader  = HybridEvaluator()

    def grade_image(
        self,
        image_source,
        student_id:    str,
        question_id:   str,
        model_answer:  str,
        max_marks:     float = 10.0,
        keywords:      list = None,
        force_handwriting: bool = False,
    ) -> StudentResult:

        ocr_result = self.ocr.route(image_source,
                                    force_handwriting=force_handwriting)

        vlm_result = None
        if ocr_result.has_diagram_hint or ocr_result.confidence < 0.5:
            vlm_result = self.vlm.run(image_source)

        scores = self.grader.evaluate(
            ocr_result=ocr_result,
            vlm_result=vlm_result,
            model_answer=model_answer,
            max_marks=max_marks,
            required_keywords=keywords,
        )

        return StudentResult(
            student_id  =student_id,
            question_id =question_id,
            raw_text    =ocr_result.text,
            vlm_desc    =vlm_result.description if vlm_result else "",
            scores      =scores,
            ocr_method  =ocr_result.method,
            vlm_model   =vlm_result.model_used if vlm_result else "none",
            has_diagram =ocr_result.has_diagram_hint,
        )
        
