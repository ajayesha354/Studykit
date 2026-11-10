"""No-LLM engine. Frequency-based sentence ranking plus cloze cards and quizzes.

Honest limits: it only reuses sentences from the document. Good for quick review and for
running offline. Use an LLM backend for real question writing and abstractive summaries.
"""
import random
import re
from collections import Counter

from .chunking import split_sentences
from .schemas import Flashcard, QuizQuestion

STOP = set(
    """a about above after again all also am an and any are as at be because been before being below between
both but by can could did do does doing down during each few for from further had has have having he her here
hers him his how i if in into is it its itself just me more most my no nor not now of off on once only or other
our out over own same she should so some such than that the their them then there these they this those through
to too under until up very was we were what when where which while who whom why will with would you your
also however thus therefore may might must shall one two three use used using like many much""".split()
)
WORD = re.compile(r"[A-Za-z][A-Za-z\-]{3,}")


def _freq(text: str) -> Counter:
    return Counter(w.lower() for w in WORD.findall(text) if w.lower() not in STOP)


def _ranked(text: str) -> list[tuple[float, int, str]]:
    freq = _freq(text)
    out = []
    for i, s in enumerate(split_sentences(text)):
        if not 40 <= len(s) <= 300:
            continue
        words = [w.lower() for w in WORD.findall(s) if w.lower() not in STOP]
        if len(words) < 4:
            continue
        score = sum(freq[w] for w in set(words)) / (len(words) ** 0.5)
        out.append((score, i, s))
    return sorted(out, reverse=True)


def _key_term(sentence: str, freq: Counter) -> str | None:
    cands = [w for w in WORD.findall(sentence) if w.lower() not in STOP and len(w) > 4]
    return max(cands, key=lambda w: (freq[w.lower()], len(w))) if cands else None


class ExtractiveEngine:
    name = "extractive"

    def __init__(self, seed: int = 7):
        self.rng = random.Random(seed)

    def summarize(self, chunks: list[str], n: int) -> list[str]:
        text = "\n\n".join(chunks)
        top = sorted(_ranked(text)[:n], key=lambda t: t[1])  # keep document order
        return [s for _, _, s in top]

    def flashcards(self, chunks: list[str], n: int) -> list[Flashcard]:
        text = "\n\n".join(chunks)
        freq = _freq(text)
        cards, used = [], set()
        for _, _, s in _ranked(text):
            term = _key_term(s, freq)
            if not term or term.lower() in used:
                continue
            used.add(term.lower())
            front = re.sub(re.escape(term), "_____", s, count=1, flags=re.I)
            cards.append(Flashcard(front=f"Fill in the blank: {front}", back=term))
            if len(cards) == n:
                break
        return cards

    def quiz(self, chunks: list[str], n: int) -> list[QuizQuestion]:
        text = "\n\n".join(chunks)
        freq = _freq(text)
        pool = [w for w, _ in freq.most_common(60) if len(w) > 4]
        qs, used = [], set()
        for _, _, s in _ranked(text):
            term = _key_term(s, freq)
            if not term or term.lower() in used:
                continue
            same_case = [w for w in pool if w != term.lower() and w[0].isupper() == term[0].isupper()]
            distractors = self.rng.sample(same_case or pool, 3) if len(same_case or pool) >= 3 else []
            if len({d.lower() for d in distractors}) < 3:
                continue
            used.add(term.lower())
            opts = distractors + [term.lower() if term.islower() else term]
            self.rng.shuffle(opts)
            qs.append(
                QuizQuestion(
                    question="Which word best completes this sentence? "
                    + re.sub(re.escape(term), "_____", s, count=1, flags=re.I),
                    options=opts,
                    answer_index=opts.index(term.lower() if term.islower() else term),
                    explanation=f"Original sentence: {s}",
                )
            )
            if len(qs) == n:
                break
        return qs
