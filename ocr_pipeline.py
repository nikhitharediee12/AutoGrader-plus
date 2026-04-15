class OCRResult:
    def __init__(self, text="", confidence=0.9, has_diagram_hint=False):
        self.text = text
        self.confidence = confidence
        self.has_diagram_hint = has_diagram_hint


class OCRRouter:
    def route(self, image, *args, **kwargs):
        # simulate OCR output
        return OCRResult(
            text="This is a sample student answer extracted via OCR.",
            confidence=0.9,
            has_diagram_hint=False
        )

    def extract_full_text(self, file_bytes):
        import pdfplumber
        import io
        import pytesseract
        from PIL import Image

        text = ""

        with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
            for page in pdf.pages:

                # Step 1: try normal text extraction
                t = page.extract_text()

                if t and t.strip():
                    text += t + "\n"
                else:
                    # 🔥 fallback OCR
                    img = page.to_image(resolution=300).original
                    ocr_text = pytesseract.image_to_string(img)

                    if ocr_text:
                        text += ocr_text + "\n"

        return text
    def extract_images_from_pdf(self, file_bytes):
        import pdfplumber
        import io
        from PIL import Image

        images = []

        with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
            for page in pdf.pages:
                img = page.to_image(resolution=300).original
                images.append(img)

        return images