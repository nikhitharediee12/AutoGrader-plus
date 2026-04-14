"""
AutoGrader+ | Feature 14 — Student-Level Feedback System
Generates structured per-student, per-question feedback.
Extends StudentResult — does NOT modify evaluation_engine.py.
"""

import json
from dataclasses import dataclass, field
from typing import Optional
import re

# Import existing data structures (read-only usage)
# from evaluation_engine import StudentResult, ScoreBreakdown


# ─────────────────────────────────────────────
# FEEDBACK DATA STRUCTURES
# ─────────────────────────────────────────────

@dataclass
class QuestionFeedback:
    question:         str
    score:            float
    max_score:        float
    marks_awarded:    float
    max_marks:        float
    missing_keywords: list
    concept_gaps:     list
    partial_areas:    list
    feedback:         str
    performance_tag:  str   # "excellent" | "good" | "partial" | "poor"


@dataclass
class OverallFeedback:
    strengths:   list
    weak_areas:  list
    suggestions: list
    performance_summary: str


@dataclass
class StudentReport:
    student_name:      str
    total_score:       float      # percentage
    total_marks:       float
    max_total_marks:   float
    question_feedback: list       # list of QuestionFeedback dicts
    overall_feedback:  OverallFeedback
    grade:             str        # A / B / C / D / F

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2)

    def to_dict(self) -> dict:
        return {
            "student_name":   self.student_name,
            "total_score":    f"{self.total_score:.1f}%",
            "total_marks":    f"{self.total_marks}/{self.max_total_marks}",
            "grade":          self.grade,
            "question_feedback": [
                {
                    "question":         qf.question,
                    "score":            f"{qf.score:.1f}%",
                    "marks":            f"{qf.marks_awarded}/{qf.max_marks}",
                    "performance":      qf.performance_tag,
                    "missing_keywords": qf.missing_keywords,
                    "concept_gaps":     qf.concept_gaps,
                    "partial_areas":    qf.partial_areas,
                    "feedback":         qf.feedback,
                }
                for qf in self.question_feedback
            ],
            "overall_feedback": {
                "strengths":   self.overall_feedback.strengths,
                "weak_areas":  self.overall_feedback.weak_areas,
                "suggestions": self.overall_feedback.suggestions,
                "summary":     self.overall_feedback.performance_summary,
            }
        }


# ─────────────────────────────────────────────
# CONCEPT GAP ANALYZER
# ─────────────────────────────────────────────

class ConceptGapAnalyzer:
    """
    Identifies conceptual gaps from missing keywords and low scores.
    Rule-based — no model required.
    """

    # Domain-concept keyword clusters
    CONCEPT_CLUSTERS = {
        "definition":    ["define", "definition", "meaning", "refers", "known as"],
        "process":       ["process", "steps", "procedure", "method", "how", "mechanism"],
        "comparison":    ["difference", "similar", "unlike", "compare", "contrast", "versus"],
        "cause_effect":  ["because", "therefore", "leads to", "result", "cause", "effect", "due to"],
        "example":       ["example", "instance", "such as", "e.g.", "for example", "illustration"],
        "formula":       ["formula", "equation", "calculate", "compute", "=", "per", "rate"],
        "diagram":       ["draw", "diagram", "label", "sketch", "graph", "figure", "plot"],
        "explain":       ["explain", "describe", "discuss", "elaborate", "justify"],
    }

    def analyze(self, question_text: str, missing_keywords: list,
                student_answer: str, model_answer: str) -> list:
        """Returns list of identified concept gap strings."""
        gaps = []
        q_lower  = question_text.lower()
        ans_lower = student_answer.lower()

        # Check which concept clusters are expected but absent
        for concept, indicators in self.CONCEPT_CLUSTERS.items():
            q_needs = any(ind in q_lower for ind in indicators)
            if q_needs:
                ans_covers = any(ind in ans_lower for ind in indicators)
                if not ans_covers:
                    gaps.append(self._gap_message(concept, question_text))

        # Missing keyword clustering
        if len(missing_keywords) > 5:
            gaps.append(f"Multiple key terms absent ({len(missing_keywords)} missing) — review core concepts")
        elif missing_keywords:
            top_missing = missing_keywords[:4]
            gaps.append(f"Key concepts not addressed: {', '.join(top_missing)}")

        return gaps[:4]  # cap at 4

    def _gap_message(self, concept: str, question: str) -> str:
        msgs = {
            "definition":   "No clear definition provided",
            "process":      "Steps/process not described",
            "comparison":   "Comparison not addressed",
            "cause_effect": "Cause-effect relationship missing",
            "example":      "Supporting examples not given",
            "formula":      "Mathematical expression or formula missing",
            "diagram":      "Diagram/sketch not attempted or incomplete",
            "explain":      "Explanation lacks depth",
        }
        return msgs.get(concept, f"'{concept}' aspect not covered")


# ─────────────────────────────────────────────
# FEEDBACK GENERATOR
# ─────────────────────────────────────────────

class FeedbackGenerator:
    """
    Generates structured feedback for each student from their graded results.
    Takes a list of StudentResult objects for ONE student.
    """

    def __init__(self):
        self.gap_analyzer = ConceptGapAnalyzer()

    def generate(
        self,
        student_id: str,
        results: list,           # list of StudentResult for this student
        question_texts: dict,    # {q_id: question_text} from QP
        model_answers: dict,     # {q_id: model_answer_text}
    ) -> StudentReport:

        q_feedbacks = []
        total_marks     = 0.0
        max_total_marks = 0.0

        for r in results:
            qf = self._question_feedback(r, question_texts, model_answers)
            q_feedbacks.append(qf)
            total_marks     += r.scores.marks_awarded
            max_total_marks += r.scores.max_marks

        total_pct = (total_marks / max_total_marks * 100) if max_total_marks else 0.0
        grade     = self._letter_grade(total_pct)
        overall   = self._overall_feedback(q_feedbacks, total_pct)

        return StudentReport(
            student_name      =student_id,
            total_score       =round(total_pct, 2),
            total_marks       =round(total_marks, 2),
            max_total_marks   =round(max_total_marks, 2),
            question_feedback =q_feedbacks,
            overall_feedback  =overall,
            grade             =grade,
        )

    def _question_feedback(self, result, question_texts: dict,
                           model_answers: dict) -> QuestionFeedback:
        s       = result.scores
        q_id    = result.question_id
        q_text  = question_texts.get(q_id, f"Question {q_id}")
        m_ans   = model_answers.get(q_id, "")
        s_ans   = result.raw_text or ""

        # Concept gaps
        gaps = self.gap_analyzer.analyze(
            question_text    =q_text,
            missing_keywords =s.missing_keywords,
            student_answer   =s_ans,
            model_answer     =m_ans,
        )

        # Partial areas
        partials = self._partial_areas(s)

        # Performance tag
        tag = self._perf_tag(s.final_score)

        # Natural language feedback
        fb = self._generate_fb_text(s, q_id, result.has_diagram)

        return QuestionFeedback(
            question         =q_id,
            score            =s.final_score,
            max_score        =100.0,
            marks_awarded    =s.marks_awarded,
            max_marks        =s.max_marks,
            missing_keywords =s.missing_keywords[:6],
            concept_gaps     =gaps,
            partial_areas    =partials,
            feedback         =fb,
            performance_tag  =tag,
        )

    def _partial_areas(self, s) -> list:
        areas = []
        if 0.3 < s.similarity_score < 0.7:
            areas.append("Partial semantic alignment with model answer")
        if 0.3 < s.keyword_score < 0.7:
            areas.append("Some key terms covered but not all")
        if s.length_score < 0.6:
            areas.append("Answer could be more detailed")
        if s.diagram_score > 0 and s.diagram_score < 0.6:
            areas.append("Diagram present but incomplete")
        return areas

    def _generate_fb_text(self, s, q_id: str, has_diagram: bool) -> str:
        parts = []

        # Similarity
        if s.final_score >= 80:
            parts.append(f"Excellent answer for {q_id}.")
        elif s.final_score >= 60:
            parts.append(f"Good answer for {q_id}, with room for improvement.")
        elif s.final_score >= 40:
            parts.append(f"Partial understanding demonstrated for {q_id}.")
        else:
            parts.append(f"Answer for {q_id} needs significant improvement.")

        # Keywords
        if s.missing_keywords:
            kws = ", ".join(f"'{k}'" for k in s.missing_keywords[:3])
            parts.append(f"Key terms to include: {kws}.")

        # Length
        if s.length_score < 0.4:
            parts.append("Answer is too brief — elaborate more.")
        elif s.length_score > 0.95:
            parts.append("Answer length is appropriate.")

        # OCR
        if s.ocr_confidence < 0.4:
            parts.append("Note: Handwriting was difficult to read — ensure legibility.")

        # Diagram
        if has_diagram and s.diagram_score < 0.5:
            parts.append("Diagram/graph needs labels, axes, or proper structure.")

        return " ".join(parts)

    def _overall_feedback(self, q_feedbacks: list,
                          total_pct: float) -> OverallFeedback:
        strengths  = []
        weak_areas = []
        suggestions = []

        # Aggregate
        scores = [qf.score for qf in q_feedbacks]
        avg    = sum(scores) / len(scores) if scores else 0

        # Strengths
        strong_qs = [qf.question for qf in q_feedbacks if qf.score >= 70]
        if strong_qs:
            strengths.append(f"Strong performance in: {', '.join(strong_qs)}")
        if avg >= 70:
            strengths.append("Consistent understanding across most questions")

        all_missing = []
        for qf in q_feedbacks:
            all_missing.extend(qf.missing_keywords)
        if not all_missing:
            strengths.append("Good keyword coverage throughout")

        # Weak areas
        weak_qs = [qf.question for qf in q_feedbacks if qf.score < 50]
        if weak_qs:
            weak_areas.append(f"Needs improvement in: {', '.join(weak_qs)}")

        # Common missing keywords
        from collections import Counter
        kw_counts = Counter(all_missing)
        common_missing = [kw for kw, cnt in kw_counts.most_common(4) if cnt >= 1]
        if common_missing:
            weak_areas.append(f"Recurring missing concepts: {', '.join(common_missing)}")

        # Concept gaps aggregate
        all_gaps = []
        for qf in q_feedbacks:
            all_gaps.extend(qf.concept_gaps)
        if all_gaps:
            unique_gaps = list(dict.fromkeys(all_gaps))[:3]
            weak_areas.extend(unique_gaps)

        # Suggestions
        if total_pct < 40:
            suggestions += [
                "Review all class notes and textbook chapters",
                "Practice writing detailed answers with key terminology",
                "Seek help from instructor for foundational concepts",
            ]
        elif total_pct < 60:
            suggestions += [
                "Focus on weak questions identified above",
                "Practice including technical keywords in answers",
                "Review model answers to understand expected depth",
            ]
        elif total_pct < 80:
            suggestions += [
                "Strengthen answers in weak areas",
                "Ensure all parts of each question are addressed",
                "Include examples and diagrams where relevant",
            ]
        else:
            suggestions += [
                "Excellent work — maintain this standard",
                "Consider helping peers in study groups",
                "Explore advanced topics for deeper understanding",
            ]

        # Performance summary
        summary = self._summary_text(total_pct, len(strong_qs), len(weak_qs))

        return OverallFeedback(
            strengths   =strengths or ["Answer attempts show effort"],
            weak_areas  =weak_areas or ["No significant weaknesses detected"],
            suggestions =suggestions,
            performance_summary=summary,
        )

    def _summary_text(self, pct: float, n_strong: int, n_weak: int) -> str:
        if pct >= 80:
            return f"Outstanding performance ({pct:.1f}%). Student demonstrates thorough understanding."
        elif pct >= 65:
            return f"Good performance ({pct:.1f}%). Strong in {n_strong} question(s), some gaps to address."
        elif pct >= 50:
            return f"Satisfactory ({pct:.1f}%). Partial understanding shown. Targeted revision recommended."
        elif pct >= 35:
            return f"Below average ({pct:.1f}%). Significant gaps across {n_weak} question(s). Needs focused study."
        else:
            return f"Needs substantial improvement ({pct:.1f}%). Foundational concepts require review."

    def _letter_grade(self, pct: float) -> str:
        if pct >= 90: return "A+"
        if pct >= 80: return "A"
        if pct >= 70: return "B"
        if pct >= 60: return "C"
        if pct >= 50: return "D"
        return "F"

    @staticmethod
    def perf_tag(score: float) -> str:
        if score >= 80: return "excellent"
        if score >= 60: return "good"
        if score >= 40: return "partial"
        return "poor"

    def _perf_tag(self, score: float) -> str:
        return self.perf_tag(score)


# ─────────────────────────────────────────────
# BATCH FEEDBACK GENERATOR
# ─────────────────────────────────────────────

class BatchFeedbackGenerator:
    """
    Groups StudentResult list by student_id and generates
    one StudentReport per student.
    """

    def __init__(self):
        self.gen = FeedbackGenerator()

    def generate_all(
        self,
        all_results: list,       # list of StudentResult
        question_texts: dict,    # {q_id: q_text}
        model_answers: dict,     # {q_id: model_answer}
    ) -> dict:
        """Returns {student_id: StudentReport}"""
        from collections import defaultdict
        by_student = defaultdict(list)
        for r in all_results:
            by_student[r.student_id].append(r)

        reports = {}
        for student_id, results in by_student.items():
            reports[student_id] = self.gen.generate(
                student_id    =student_id,
                results       =results,
                question_texts=question_texts,
                model_answers =model_answers,
            )
        return reports
