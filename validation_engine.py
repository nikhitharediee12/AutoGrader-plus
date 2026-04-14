"""
AutoGrader+ | Feature 20 — Marks Validation Engine
Compares AI-predicted scores vs teacher-provided ground truth marks.
100% additive — no existing code modified.
"""

import json
from dataclasses import dataclass, field
from pathlib import Path
import pandas as pd
import io


@dataclass
class ValidationEntry:
    student_id:    str
    question_id:   str
    ai_marks:      float
    teacher_marks: float
    max_marks:     float
    diff:          float      # ai - teacher
    abs_diff:      float
    accuracy_pct:  float      # 100 - (abs_diff / max_marks * 100)


@dataclass
class ValidationReport:
    entries:          list[ValidationEntry]
    overall_accuracy: float      # mean accuracy %
    mean_abs_error:   float      # MAE in marks
    rmse:             float
    over_graded:      list        # AI > teacher by > 1 mark
    under_graded:     list        # AI < teacher by > 1 mark
    agreement_rate:   float       # % within ±1 mark


class ValidationEngine:
    """
    Ingests teacher marks (CSV or dict) and compares with AI marks.

    Teacher marks CSV format:
        student_id, question_id, marks
        Alice,Q1,8
        Alice,Q2,6
    """

    def load_teacher_marks_csv(self, file_bytes: bytes) -> pd.DataFrame:
        df = pd.read_csv(io.BytesIO(file_bytes))
        df.columns = [c.strip().lower() for c in df.columns]
        required = {"student_id", "question_id", "marks"}
        missing  = required - set(df.columns)
        if missing:
            raise ValueError(f"Teacher marks CSV missing columns: {missing}")
        df["marks"] = pd.to_numeric(df["marks"], errors="coerce")
        return df

    def load_teacher_marks_dict(self, data: dict) -> pd.DataFrame:
        """
        data format: {"Alice": {"Q1": 8, "Q2": 6}, "Bob": {"Q1": 5}}
        """
        rows = []
        for student, qs in data.items():
            for q_id, marks in qs.items():
                rows.append({"student_id": student, "question_id": q_id, "marks": marks})
        return pd.DataFrame(rows)

    def compare(
        self,
        ai_results: list,        # list of StudentResult
        teacher_df: pd.DataFrame,
        max_marks_map: dict,     # {q_id: max_marks}
    ) -> ValidationReport:

        # Build AI results lookup
        ai_map = {}
        for r in ai_results:
            ai_map[(r.student_id, r.question_id)] = r.scores.marks_awarded

        entries = []
        for _, row in teacher_df.iterrows():
            key = (str(row["student_id"]), str(row["question_id"]))
            if key not in ai_map:
                continue
            ai_m  = ai_map[key]
            t_m   = float(row["marks"])
            max_m = max_marks_map.get(str(row["question_id"]), 10.0)
            diff  = round(ai_m - t_m, 3)
            abs_d = abs(diff)
            acc   = max(0.0, 100.0 - (abs_d / max_m * 100)) if max_m else 100.0
            entries.append(ValidationEntry(
                student_id   =str(row["student_id"]),
                question_id  =str(row["question_id"]),
                ai_marks     =ai_m,
                teacher_marks=t_m,
                max_marks    =max_m,
                diff         =diff,
                abs_diff     =abs_d,
                accuracy_pct =round(acc, 2),
            ))

        if not entries:
            return ValidationReport([], 0, 0, 0, [], [], 0)

        import math
        mae   = sum(e.abs_diff for e in entries) / len(entries)
        rmse  = math.sqrt(sum(e.diff ** 2 for e in entries) / len(entries))
        oa    = sum(e.accuracy_pct for e in entries) / len(entries)
        agree = sum(1 for e in entries if e.abs_diff <= 1.0)
        agree_rate = agree / len(entries) * 100

        over  = [e for e in entries if e.diff > 1.0]
        under = [e for e in entries if e.diff < -1.0]

        return ValidationReport(
            entries          =entries,
            overall_accuracy =round(oa, 2),
            mean_abs_error   =round(mae, 3),
            rmse             =round(rmse, 3),
            over_graded      =over,
            under_graded     =under,
            agreement_rate   =round(agree_rate, 2),
        )

    def to_dataframe(self, report: ValidationReport) -> pd.DataFrame:
        rows = []
        for e in report.entries:
            rows.append({
                "Student":        e.student_id,
                "Question":       e.question_id,
                "AI Marks":       e.ai_marks,
                "Teacher Marks":  e.teacher_marks,
                "Max Marks":      e.max_marks,
                "Difference":     e.diff,
                "Accuracy %":     e.accuracy_pct,
            })
        return pd.DataFrame(rows)
