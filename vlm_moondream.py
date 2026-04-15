from transformers import AutoModelForCausalLM, AutoTokenizer
from PIL import Image
import torch


class MoonDreamVLM:
    def __init__(self):
        model_id = "vikhyatk/moondream2"

        self.tokenizer = AutoTokenizer.from_pretrained(model_id)
        self.model = AutoModelForCausalLM.from_pretrained(
            model_id,
            trust_remote_code=True
        )

    def analyze(self, image):
        try:
            if not isinstance(image, Image.Image):
                return {
                    "description": "Invalid image format",
                    "confidence": 0.0
                }

            prompt = "Describe this diagram or graph clearly."

            description = self.model.answer_question(
                image,
                prompt,
                self.tokenizer
            )

            return {
                "description": description,
                "confidence": 0.9
            }

        except Exception as e:
            return {
                "description": f"Moondream error: {e}",
                "confidence": 0.0
            }