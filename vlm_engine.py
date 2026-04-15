from vlm_moondream import MoonDreamVLM
def analyze_image(image):
    """
    Simple VLM simulation (replace later with real model)
    """
    return {
        "description": "Detected a diagram or graphical content in the answer."
    }
class VLMResult:
    def __init__(self, description="", confidence=0.8, diagram_type=None):
        self.description = description
        self.confidence = confidence
        self.diagram_type = diagram_type


class DiagramEvaluator:
    def __init__(self):
        self.vlm_available = True

    def analyze(self, image):
        try:
            result = analyze_image(image)  # ✅ direct call

            description = result.get("description", "")

            score = 0.0
            if description:
                score = min(len(description) / 100, 1.0)

            return {
                "description": description,
                "score": round(score, 2)
            }

        except Exception as e:
            return {
                "description": f"Error analyzing diagram: {e}",
                "score": 0.0
            }


class VLMRouter:
    def __init__(self):
        self.diagram_eval = DiagramEvaluator()
        try:
            self.moondream = MoonDreamVLM()
        except Exception as e:
            print("❌ Moondream failed:", e)
            self.moondream = None

    def route(self, image, *args, **kwargs):

        # 🔥 Try Moondream first (SAFE)
        if self.moondream:
            try:
                result = self.moondream.analyze(image)

                if result.get("description") and not result["description"].lower().startswith("moondream error"):
                    print("🔥 USING MOONDREAM VLM")

                    return VLMResult(
                        description=result.get("description", ""),
                        confidence=result.get("confidence", 0.8),
                        diagram_type="diagram"
                    )

            except Exception as e:
                print("❌ Moondream runtime error:", e)

        # 🔁 fallback (old system)
        result = self.diagram_eval.analyze(image)

        return VLMResult(
            description=result["description"],
            confidence=0.8,
            diagram_type="diagram" if result["score"] > 0 else None
        )