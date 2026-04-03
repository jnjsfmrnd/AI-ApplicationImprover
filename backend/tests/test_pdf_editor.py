from io import BytesIO
import unittest

from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from pypdf import PdfReader

from app.services.pdf_editor import calculate_page_upward_shift, normalize_resume_pdf_layout


def _build_two_page_pdf() -> bytes:
    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=letter)
    pdf.drawString(72, 720, "Page 1")
    pdf.showPage()
    pdf.drawString(72, 400, "Page 2 body starts too low")
    pdf.save()
    return buffer.getvalue()


class PdfEditorTests(unittest.TestCase):
    def test_calculate_page_upward_shift_detects_large_top_gap(self) -> None:
        pdf_bytes = _build_two_page_pdf()
        reader = PdfReader(BytesIO(pdf_bytes))

        shift = calculate_page_upward_shift(reader.pages[1])

        self.assertGreater(shift, 300)

    def test_normalize_resume_pdf_layout_adds_vertical_translation_to_later_pages(self) -> None:
        pdf_bytes = _build_two_page_pdf()

        normalized_pdf = normalize_resume_pdf_layout(pdf_bytes)

        reader = PdfReader(BytesIO(normalized_pdf))
        second_page_stream = reader.pages[1].get_contents().get_data().decode("latin1")
        self.assertIn(" cm", second_page_stream)
        self.assertIn(" 0.0 ", second_page_stream)
        self.assertRegex(second_page_stream, r"1 0\.0 0\.0 1 0\.0 [0-9.]+ cm")


if __name__ == "__main__":
    unittest.main()