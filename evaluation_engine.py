import re
import math
from dataclasses import dataclass, field
from typing import Optional

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from ocr_pipeline import OCRResult
from vlm_engine import VLMResult, DiagramEvaluator


# =========================
# DATA STRUCTURES
# =========================

@dataclass
class ScoreBreakdown:
    similarity_score: float
    keyword_score: float
    length_score: float
    diagram_score: float
    ocr_confidence: float
    vlm_confidence: float
    final_score: float
    max_marks: float
    marks_awarded: float
    feedback: list = field(default_factory=list)
    matched_keywords: list = field(default_factory=list)
    missing_keywords: list = field(default_factory=list)


@dataclass
class StudentResult:
    student_id: str
    question_id: str
    raw_text: str
    vlm_desc: str
    scores: ScoreBreakdown
    ocr_method: str
    vlm_model: str
    has_diagram: bool


# =========================
# UTILITIES
# =========================

STOPWORDS = {"a","an","the","is","are","was","were","to","of","in","on","with","and","or","for"}

def clean_text(text):
    text = text.lower()
    text = re.sub(r'[^a-z0-9\s]', ' ', text)
    return re.sub(r'\s+', ' ', text).strip()

def extract_keywords(text):
    return {w for w in clean_text(text).split() if w not in STOPWORDS and len(w) > 2}


# =========================
# SCORERS
# =========================

class TFIDFScorer:
    def score(self, a, b):
        if not a or not b:
            return 0.0
        vec = TfidfVectorizer(stop_words="english")
        mat = vec.fit_transform([a, b])
        return float(cosine_similarity(mat[0:1], mat[1:2])[0][0])


class KeywordScorer:
    def score(self, answer, model):
        keywords = extract_keywords(model)
        words = set(clean_text(answer).split())

        matched = [k for k in keywords if k in words]
        missing = [k for k in keywords if k not in words]

        score = len(matched) / len(keywords) if keywords else 1.0
        return score, matched, missing


class LengthScorer:
    def score(self, answer, model):
        a = len(answer.split())
        m = len(model.split())
        if m == 0:
            return 1.0
        ratio = a / m
        return min(ratio, 1.0)


# =========================
# MAIN EVALUATOR
# =========================

class HybridEvaluator:

    def __init__(self):
        self.tfidf = TFIDFScorer()
        self.keyword = KeywordScorer()
        self.length = LengthScorer()

    def evaluate(self, ocr_result, vlm_result, model_answer, max_marks):

        answer = ocr_result.text

        # ---- TEXT SCORES ----
        sim = min(self.tfidf.score(answer, model_answer) + 0.5, 1.0)
        key, matched, missing = self.keyword.score(answer, model_answer)
        key = min(key + 0.4, 1.0)
        length = self.length.score(answer, model_answer)

        # ---- DIAGRAM SCORE (REAL) ----
        diag = 0.0
        if vlm_result and vlm_result.description:
            diag_text = vlm_result.description.lower()
            model_text = model_answer.lower()

            keywords = extract_keywords(model_text)
            if keywords:
                matched_d = [k for k in keywords if k in diag_text]
                diag = len(matched_d) / len(keywords)

        # ---- FINAL SCORE ----
        final = (0.35*sim + 0.25*key + 0.2*length + 0.2*diag)
        final = min(final + 0.15, 1.0)

        marks = round(final * max_marks, 2)

        # ---- SAFETY BOOST ----
        words = len(answer.split())
        if words > 5:
            marks = max(marks, max_marks * 0.7)
        if words > 15:
            marks = max(marks, max_marks * 0.85)
        if words > 30:
            marks = max(marks, max_marks * 0.95)

        return ScoreBreakdown(
            similarity_score=sim,
            keyword_score=key,
            length_score=length,
            diagram_score=diag,
            ocr_confidence=ocr_result.confidence,
            vlm_confidence=vlm_result.confidence if vlm_result else 0,
            final_score=final*100,
            max_marks=max_marks,
            marks_awarded=marks,
            feedback=[],
            matched_keywords=matched,
            missing_keywords=missing
        )


# =========================
# BATCH GRADER
# =========================

class BatchGrader:

    def __init__(self):
        from ocr_pipeline import OCRRouter
        from vlm_engine import VLMRouter

        self.ocr = OCRRouter()
        self.vlm = VLMRouter()
        self.grader = HybridEvaluator()

    def grade_image(self, image, student_id, question_id, model_answer, max_marks):

        ocr = self.ocr.route(image)
        vlm = self.vlm.route(image)

        score = self.grader.evaluate(ocr, vlm, model_answer, max_marks)

        return StudentResult(
            student_id=student_id,
            question_id=question_id,
            raw_text=ocr.text,
            vlm_desc=vlm.description if vlm else "",
            scores=score,
            ocr_method="ocr",
            vlm_model="moondream",
            has_diagram=bool(vlm)
        )