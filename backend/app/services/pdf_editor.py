from io import BytesIO

from pypdf import PdfReader, PdfWriter, Transformation


def _extract_top_text_y(page) -> float | None:
    highest_y: float | None = None

    def visitor(text: str, _cm: list[float], tm: list[float], _font_dict: dict | None, font_size: float) -> None:
        nonlocal highest_y
        if not text or not text.strip() or len(tm) < 6:
            return

        y_position = float(tm[5]) + max(float(font_size), 0.0)
        if highest_y is None or y_position > highest_y:
            highest_y = y_position

    try:
        page.extract_text(visitor_text=visitor)
    except Exception:
        return None

    return highest_y


def calculate_page_upward_shift(
    page,
    *,
    desired_top_padding: float = 40.0,
    minimum_excess_padding: float = 36.0,
) -> float:
    page_height = float(page.mediabox.top) - float(page.mediabox.bottom)
    highest_y = _extract_top_text_y(page)
    if highest_y is None:
        return 0.0

    current_top_padding = page_height - highest_y
    excess_padding = current_top_padding - desired_top_padding
    if excess_padding <= minimum_excess_padding:
        return 0.0

    return excess_padding


def normalize_resume_pdf_layout(pdf_bytes: bytes) -> bytes:
    if not pdf_bytes:
        raise ValueError("PDF content is empty.")

    reader = PdfReader(BytesIO(pdf_bytes))
    writer = PdfWriter()

    if reader.metadata:
        writer.add_metadata(dict(reader.metadata))

    for index, page in enumerate(reader.pages):
        writer.add_page(page)

        if index == 0:
            continue

        upward_shift = calculate_page_upward_shift(page)
        if upward_shift <= 0:
            continue

        writer.pages[-1].add_transformation(
            Transformation().translate(tx=0, ty=upward_shift)
        )

    buffer = BytesIO()
    writer.write(buffer)
    return buffer.getvalue()