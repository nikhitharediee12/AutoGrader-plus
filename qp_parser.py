"""
AutoGrader+ | Feature 13 — Question Paper Parser
Extracts questions, marks, and builds QP ↔ Model Answer ↔ Student Answer mapping.
Does NOT modify any existing pipeline — feeds INTO it.
"""

import re
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional
import io


# ─────────────────────────────────────────────
# DATA STRUCTURES
# ─────────────────────────────────────────────

@dataclass
class QuestionEntry:
    q_id:        str         # "Q1", "Q2", etc.
    q_number:    int
    text:        str         # full question text
    marks:       float       # marks allocated
    model_answer: str = ""   # filled by teacher / answer key
    keywords:    list = field(default_factory=list)  # optional override


@dataclass
class QuestionPaper:
    title:     str
    questions: list[QuestionEntry]
    total_marks: float

    def get(self, q_id: str) -> Optional[QuestionEntry]:
        for q in self.questions:
            if q.q_id.upper() == q_id.upper():
                return q
        return None

    def to_dict(self) -> dict:
        return {
            "title": self.title,
            "total_marks": self.total_marks,
            "questions": [
                {
                    "q_id": q.q_id,
                    "q_number": q.q_number,
                    "text": q.text,
                    "marks": q.marks,
                    "model_answer": q.model_answer,
                    "keywords": q.keywords,
                }
                for q in self.questions
            ]
        }

    @classmethod
    def from_dict(cls, d: dict) -> "QuestionPaper":
        questions = [
            QuestionEntry(
                q_id=q["q_id"],
                q_number=q["q_number"],
                text=q["text"],
                marks=q["marks"],
                model_answer=q.get("model_answer", ""),
                keywords=q.get("keywords", []),
            )
            for q in d.get("questions", [])
        ]
        return cls(
            title=d.get("title", "Untitled"),
            questions=questions,
            total_marks=d.get("total_marks", sum(q.marks for q in questions)),
        )


# ─────────────────────────────────────────────
# QP TEXT EXTRACTOR
# ─────────────────────────────────────────────

class QPTextExtractor:
    """
    Extracts raw text from question paper files.
    Supports: PDF (pdfplumber), plain text, images (Tesseract).
    """

    def extract(self, file_bytes: bytes, mime_type: str) -> str:
        if "pdf" in mime_type:
            return self._from_pdf(file_bytes)
        elif mime_type.startswith("image"):
            return self._from_image(file_bytes)
        else:
            return file_bytes.decode("utf-8", errors="ignore")

    def _from_pdf(self, file_bytes: bytes) -> str:
        try:
            import pdfplumber
            text_parts = []
            with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
                for page in pdf.pages:
                    t = page.extract_text()
                    if t:
                        text_parts.append(t)
            return "\n".join(text_parts)
        except Exception as e:
            return f"[PDF extraction failed: {e}]"

    def _from_image(self, file_bytes: bytes) -> str:
        try:
            import pytesseract
            from PIL import Image
            img = Image.open(io.BytesIO(file_bytes))
            return pytesseract.image_to_string(img)
        except Exception as e:
            return f"[Image OCR failed: {e}]"


# ─────────────────────────────────────────────
# QUESTION DETECTOR
# ─────────────────────────────────────────────

class QuestionDetector:
    """
    Parses raw QP text to find questions and marks.

    Handles patterns like:
      Q1. What is photosynthesis? (5 marks)
      1) Define Newton's laws. [3]
      Question 2: Explain... (4 Marks)
      Q.3  Draw a diagram...    Marks: 6
    """

    # Patterns for question start
    Q_PATTERNS = [
        r'^(?:Q\.?\s*|Question\s+)(\d+)[.):\s]',   # Q1. / Question 1:
        r'^(\d+)[.)]\s+',                            # 1. / 1)
    ]

    # Patterns for marks
    MARKS_PATTERNS = [
        r'\((\d+(?:\.\d+)?)\s*[Mm]arks?\)',          # (5 marks)
        r'\[(\d+(?:\.\d+)?)\s*[Mm]arks?\]',          # [5 Marks]
        r'\[(\d+(?:\.\d+)?)\]',                       # [5]
        r'[Mm]arks?\s*:\s*(\d+(?:\.\d+)?)',          # Marks: 5
        r'\((\d+(?:\.\d+)?)\)$',                      # (5) at end of line
    ]

    def detect(self, text: str) -> list[QuestionEntry]:
        lines = text.split("\n")
        questions: list[QuestionEntry] = []
        current_q: Optional[dict] = None

        for line in lines:
            line_stripped = line.strip()
            if not line_stripped:
                if current_q:
                    current_q["text_lines"].append("")
                continue

            q_num = self._match_question_start(line_stripped)
            if q_num is not None:
                # Save previous question
                if current_q:
                    questions.append(self._build_entry(current_q))
                # Start new
                marks = self._extract_marks(line_stripped)
                current_q = {
                    "q_num": q_num,
                    "text_lines": [line_stripped],
                    "marks": marks,
                }
            else:
                if current_q:
                    # Check if this line has additional marks info
                    m = self._extract_marks(line_stripped)
                    if m and not current_q["marks"]:
                        current_q["marks"] = m
                    current_q["text_lines"].append(line_stripped)

        if current_q:
            questions.append(self._build_entry(current_q))

        # Assign default marks if none found
        for q in questions:
            if q.marks == 0.0:
                q.marks = 5.0  # default

        return questions

    def _match_question_start(self, line: str) -> Optional[int]:
        for pat in self.Q_PATTERNS:
            m = re.match(pat, line, re.IGNORECASE)
            if m:
                try:
                    return int(m.group(1))
                except (ValueError, IndexError):
                    pass
        return None

    def _extract_marks(self, text: str) -> float:
        for pat in self.MARKS_PATTERNS:
            m = re.search(pat, text)
            if m:
                try:
                    return float(m.group(1))
                except ValueError:
                    pass
        return 0.0

    def _build_entry(self, d: dict) -> QuestionEntry:
        q_num = d["q_num"]
        q_id  = f"Q{q_num}"
        full_text = " ".join(l for l in d["text_lines"] if l)
        marks = d["marks"] or 5.0
        return QuestionEntry(
            q_id=q_id,
            q_number=q_num,
            text=full_text,
            marks=marks,
        )


# ─────────────────────────────────────────────
# QP BUILDER (main entry point)
# ─────────────────────────────────────────────

class QPBuilder:
    """
    Orchestrates: file → text → questions → QuestionPaper.
    Also merges in manually provided model answers.
    """

    def __init__(self):
        self.extractor = QPTextExtractor()
        self.detector  = QuestionDetector()

    def build_from_file(
        self,
        file_bytes: bytes,
        mime_type: str,
        title: str = "Exam",
        manual_answers: dict = None,    # {q_id: answer_text}
        manual_marks: dict = None,      # {q_id: marks_float} override
        manual_keywords: dict = None,   # {q_id: [kw1, kw2]}
    ) -> QuestionPaper:

        raw_text = self.extractor.extract(file_bytes, mime_type)
        questions = self.detector.detect(raw_text)

        if not questions:
            # Fallback: treat whole text as Q1
            questions = [QuestionEntry(
                q_id="Q1", q_number=1,
                text=raw_text[:500], marks=10.0
            )]

        # Merge manual data
        if manual_answers:
            for q in questions:
                q.model_answer = manual_answers.get(q.q_id, "")
        if manual_marks:
            for q in questions:
                override = manual_marks.get(q.q_id)
                if override is not None:
                    q.marks = float(override)
        if manual_keywords:
            for q in questions:
                q.keywords = manual_keywords.get(q.q_id, [])

        total = sum(q.marks for q in questions)
        return QuestionPaper(title=title, questions=questions, total_marks=total)

    def build_from_manual(
        self,
        n_questions: int,
        title: str,
        answers: dict,      # {q_id: text}
        marks: dict,        # {q_id: float}
        keywords: dict = None,
    ) -> QuestionPaper:
        """Build QP entirely from manual inputs (no file upload required)."""
        questions = []
        for i in range(1, n_questions + 1):
            q_id = f"Q{i}"
            questions.append(QuestionEntry(
                q_id=q_id,
                q_number=i,
                text=f"Question {i}",
                marks=marks.get(q_id, 10.0),
                model_answer=answers.get(q_id, ""),
                keywords=(keywords or {}).get(q_id, []),
            ))
        total = sum(q.marks for q in questions)
        return QuestionPaper(title=title, questions=questions, total_marks=total)


# ─────────────────────────────────────────────
# ANSWER KEY PARSER
# ─────────────────────────────────────────────

class AnswerKeyParser:
    """
    Parses an uploaded answer key file and maps answers to question IDs.
    Format supported:
      Q1: <answer text>
      Q2: <answer text>
      or plain numbered:
      1. <answer text>
    """

    def parse(self, text: str) -> dict:
        """Returns {q_id: answer_text}."""
        answers = {}
        current_q = None
        lines_buf = []

        for line in text.split("\n"):
            stripped = line.strip()
            m = re.match(r'^(?:Q\.?\s*|Answer\s+)?(\d+)[.):\s]', stripped, re.IGNORECASE)
            if m:
                if current_q and lines_buf:
                    answers[f"Q{current_q}"] = " ".join(lines_buf).strip()
                current_q = int(m.group(1))
                rest = stripped[m.end():].strip()
                lines_buf = [rest] if rest else []
            else:
                if current_q and stripped:
                    lines_buf.append(stripped)

        if current_q and lines_buf:
            answers[f"Q{current_q}"] = " ".join(lines_buf).strip()

        return answers


# ─────────────────────────────────────────────
# QP ↔ STUDENT FILE MAPPER
# ─────────────────────────────────────────────

class StudentFileMapper:
    """
    Maps uploaded student files to (student_id, question_id) pairs.
    Tries multiple naming conventions.
    """

    def map(self, filenames: list[str]) -> list[dict]:
        """
        Returns list of:
        {"filename": ..., "student_id": ..., "question_id": ..., "confidence": "high"/"low"}
        """
        results = []
        for fname in filenames:
            stem  = Path(fname).stem
            entry = self._parse_filename(stem, fname)
            results.append(entry)
        return results

    def _parse_filename(self, stem: str, original: str) -> dict:
        # Convention 1: StudentName_Q1  or  StudentName_q1
        m = re.search(r'[_\-\s]([Qq])(\d+)', stem)
        if m:
            q_id = f"Q{m.group(2)}"
            student = stem[:m.start()].strip("_- ")
            return {"filename": original, "student_id": student or stem,
                    "question_id": q_id, "confidence": "high"}

        # Convention 2: Q1_StudentName
        m = re.match(r'[Qq](\d+)[_\-\s](.+)', stem)
        if m:
            return {"filename": original, "student_id": m.group(2),
                    "question_id": f"Q{m.group(1)}", "confidence": "high"}

        # Convention 3: just "StudentName" → assign to Q1
        return {"filename": original, "student_id": stem,
                "question_id": "Q1", "confidence": "low"}
