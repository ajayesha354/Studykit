import io
import pytest
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

TEXT = [
    "Photosynthesis is the process by which plants convert light energy into chemical energy. "
    "Chlorophyll in the chloroplasts absorbs sunlight, mainly in the red and blue wavelengths. "
    "The light reactions produce ATP and NADPH inside the thylakoid membranes of the chloroplast.",
    "The Calvin cycle uses ATP and NADPH to fix carbon dioxide into glucose in the stroma. "
    "Rubisco is the enzyme that catalyzes the first major step of carbon fixation in plants. "
    "Photosynthesis releases oxygen as a by-product, which supports respiration in most organisms.",
    "Cellular respiration is the opposite process, since glucose is broken down to release usable energy. "
    "Mitochondria produce most of the ATP in eukaryotic cells through oxidative phosphorylation. "
    "Glycolysis occurs in the cytoplasm and splits glucose into two molecules of pyruvate.",
]


@pytest.fixture
def text():
    return "\n\n".join(TEXT)


@pytest.fixture
def pdf_bytes():
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=letter)
    for para in TEXT:
        y = 740
        words, line = para.split(), ""
        for w in words:
            if len(line) + len(w) > 80:
                c.drawString(50, y, line); y -= 16; line = w
            else:
                line = f"{line} {w}".strip()
        c.drawString(50, y, line)
        c.showPage()
    c.save()
    return buf.getvalue()
