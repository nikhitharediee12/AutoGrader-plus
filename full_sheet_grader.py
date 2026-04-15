from answer_sheet_processor import AnswerSheetProcessor
from ocr_pipeline import OCRResult, OCRRouter
from evaluation_engine import HybridEvaluator, StudentResult
from vlm_engine import VLMRouter


class FullSheetGrader:
    def __init__(self):
        self.processor = AnswerSheetProcessor()
        self.evaluator = HybridEvaluator()

        # ✅ REQUIRED (your error was here)
        self.ocr = OCRRouter()
        self.vlm = VLMRouter()

    def grade(
        self,
        full_text: str,
        student_id: str,
        model_answers: dict,
        max_marks_map: dict,
        file_bytes=None   # ✅ IMPORTANT
    ):
        segments = self.processor.split(full_text)

        # ✅ Extract images from PDF (for VLM)
        images = []
        if file_bytes:
            try:
                images = self.ocr.extract_images_from_pdf(file_bytes)
            except Exception as e:
                print("Image extraction failed:", e)
                images = []

        results = []

        for seg in segments:
            q_id = seg.question_id

            # ✅ Ensure model answer always exists
            model_answer = model_answers.get(q_id)
            if not model_answer:
                model_answer = "No model answer provided."

            max_marks = max_marks_map.get(q_id, 10.0)

            # ✅ OCR result (from split text)
            ocr_result = OCRResult(
                text=seg.answer_text,
                confidence=0.9,
                has_diagram_hint=False,
            )

            # ✅ VLM integration
            vlm_result = None

            for img in images:
                try:
                    temp = self.vlm.route(img)
                    if temp and temp.description:
                        vlm_result = temp
                        break
                except:
                    continue

            # ✅ Evaluation
            score = self.evaluator.evaluate(
                ocr_result=ocr_result,
                vlm_result=vlm_result,
                model_answer=model_answer,
                max_marks=max_marks
            )

            # ✅ Final result object
            results.append(StudentResult(
                student_id=student_id,
                question_id=q_id,
                raw_text=seg.answer_text,
                vlm_desc=vlm_result.description if vlm_result else "",
                scores=score,
                ocr_method="full_sheet",
                vlm_model="moondream" if vlm_result else "none",
                has_diagram=bool(vlm_result)
            ))

        return results