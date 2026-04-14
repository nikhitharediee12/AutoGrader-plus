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

    def route(self, image, *args, **kwargs):
        result = self.diagram_eval.analyze(image)

        return VLMResult(
            description=result["description"],
            confidence=0.8,
            diagram_type="diagram" if result["score"] > 0 else None
        )
