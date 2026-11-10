SYSTEM = (
    "You are a careful study assistant. Use ONLY the text you are given. "
    "Never invent facts. Reply with a single JSON object and nothing else."
)

SUMMARY = """Summarize the text below as {n} short bullet points covering the main ideas.
Each bullet is one plain sentence.
Return JSON: {{"bullets": ["...", "..."]}}

TEXT:
{text}"""

SUMMARY_REDUCE = """Below are bullet points taken from several parts of one document.
Merge them into {n} bullet points. Remove duplicates, keep the most important ideas.
Return JSON: {{"bullets": ["...", "..."]}}

BULLETS:
{text}"""

FLASHCARDS = """Write {n} flashcards from the text below. Each card tests one fact or concept.
The front is a clear question or term. The back is a short, correct answer.
Return JSON: {{"flashcards": [{{"front": "...", "back": "..."}}]}}

TEXT:
{text}"""

QUIZ = """Write {n} multiple-choice questions from the text below.
Rules: exactly 4 options, one correct, the other three plausible but wrong,
"answer_index" is the 0-based index of the correct option, and "explanation" is one sentence.
Return JSON: {{"questions": [{{"question": "...", "options": ["a","b","c","d"], "answer_index": 0, "explanation": "..."}}]}}

TEXT:
{text}"""

REPAIR = "Your last reply was invalid: {err}\nReturn only the corrected JSON object."
