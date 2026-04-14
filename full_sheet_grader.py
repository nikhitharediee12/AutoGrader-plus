from answer_sheet_processor import AnswerSheetProcessor
from ocr_pipeline import OCRResult
from evaluation_engine import HybridEvaluator, StudentResult


class FullSheetGrader:
    def __init__(self):
        self.processor = AnswerSheetProcessor()
        self.evaluator = HybridEvaluator()

    def grade(
        self,
        full_text: str,
        student_id: str,
        model_answers: dict,
        max_marks_map: dict
    ):
        segments = self.processor.split(full_text)

        results = []

        for seg in segments:
            q_id = seg.question_id

            # 🔥 ensure model answer always exists
            model_answer = model_answers.get(q_id)
            if not model_answer:
                model_answer = "No model answer provided."

            max_marks = max_marks_map.get(q_id, 10.0)

            ocr_result = OCRResult(
                text=seg.answer_text,
                confidence=0.9,
                has_diagram_hint=False,
            )

            vlm_result = None

            score = self.evaluator.evaluate(   # ✅ FIXED
                ocr_result=ocr_result,
                vlm_result=vlm_result,
                model_answer=model_answer,
                max_marks=max_marks
            )

            results.append(StudentResult(
                student_id=student_id,
                question_id=q_id,
                raw_text=seg.answer_text,
                vlm_desc="",
                scores=score,
                ocr_method="full_sheet",
                vlm_model="none",
                has_diagram=False
            ))

        return results