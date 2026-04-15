import re
from dataclasses import dataclass


@dataclass
class AnswerSegment:
    question_id: str
    answer_text: str


class AnswerSheetProcessor:
    """
    Takes full OCR text and splits into question-wise answers.
    """

    def split(self, full_text: str) -> list[AnswerSegment]:

    # 🔥 UNIVERSAL QUESTION PATTERN
        pattern = r'(?:^|\n)\s*(?:Q|Question|Ans)?\s*\(?([1-9]|1[0-9]|20)\)?[\.\:\)]?'

        matches = list(re.finditer(pattern, full_text, re.IGNORECASE))

        segments = []

        for i, match in enumerate(matches):
            q_num = match.group(1)
            q_id = f"Q{q_num}"

            start = match.end()
            end = matches[i + 1].start() if i + 1 < len(matches) else len(full_text)

            answer_text = full_text[start:end].strip()

            # 🔥 FILTER GARBAGE
            if not answer_text or len(answer_text.split()) < 3:
                continue

            segments.append(AnswerSegment(
                question_id=q_id,
                answer_text=answer_text
            ))

        # 🔥 REMOVE DUPLICATES
        seen = set()
        final_segments = []

        for seg in segments:
            if seg.question_id not in seen:
                seen.add(seg.question_id)
                final_segments.append(seg)

        return final_segments