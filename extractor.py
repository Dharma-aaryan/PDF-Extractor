import os
import json
import pandas as pd

# ========== CONFIG ==========
PDF_PATH = "sample_Report.pdf"   # change to your PDF path
OUTPUT_DIR = "outputs"
# ============================

def extract_with_pypdf2(path):
    try:
        from PyPDF2 import PdfReader
        reader = PdfReader(path)
        pages = [(page.extract_text() or "") for page in reader.pages]
        return pages, "PyPDF2"
    except Exception as e:
        return None, f"PyPDF2 error: {e}"

def extract_with_pdfminer(path):
    try:
        from pdfminer.high_level import extract_text
        text = extract_text(path) or ""
        pages = [p for p in text.split("\x0c") if p.strip()]
        return (pages or [text]), "pdfminer.six"
    except Exception as e:
        return None, f"pdfminer.six error: {e}"

def ocr_pdf_to_text_pages(path, dpi=300, lang="eng", tesseract_cmd=None):
    """
    OCR fallback for scanned PDFs. Requires:
      - poppler (system) -> brew install poppler
      - tesseract (system) -> brew install tesseract
      - pdf2image, pillow, pytesseract (Python)
    """
    try:
        from pdf2image import convert_from_path
        import pytesseract
        if tesseract_cmd:
            pytesseract.pytesseract.tesseract_cmd = tesseract_cmd
    except Exception as e:
        raise RuntimeError(
            "OCR not available. Install pdf2image, pillow, pytesseract and system tesseract/poppler.\n"
            f"Import error: {e}"
        )

    images = convert_from_path(path, dpi=dpi)
    pages = []
    for img in images:
        text = pytesseract.image_to_string(img, lang=lang)
        pages.append(text)
    return pages, "OCR (pytesseract)"

def extract_text_pages(path):
    # 1) Try PyPDF2
    pages, engine = extract_with_pypdf2(path)
    if pages and any((p.strip() for p in pages)):
        return pages, engine

    # 2) Fallback to pdfminer
    pages, engine = extract_with_pdfminer(path)
    if pages and any((p.strip() for p in pages)):
        return pages, engine

    # 3) Last resort: OCR
    # If Homebrew installed tesseract at /opt/homebrew/bin/tesseract, set the path (optional).
    tesseract_path = "/opt/homebrew/bin/tesseract" if os.path.exists("/opt/homebrew/bin/tesseract") else None
    pages, engine = ocr_pdf_to_text_pages(path, tesseract_cmd=tesseract_path)
    return pages, engine

def write_json_and_csv(pages, out_dir, engine):
    os.makedirs(out_dir, exist_ok=True)
    json_path = os.path.join(out_dir, "extracted.json")
    csv_path  = os.path.join(out_dir, "extracted.csv")

    result_json = {
        "engine": engine,
        "num_pages": len(pages),
        "pages": [{"page": i+1, "text": pages[i]} for i in range(len(pages))]
    }
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(result_json, f, ensure_ascii=False, indent=2)

    rows = []
    for i, text in enumerate(pages, start=1):
        for j, line in enumerate((text or "").splitlines(), start=1):
            rows.append({"page": i, "line_no": j, "text": line})
    pd.DataFrame(rows).to_csv(csv_path, index=False)

    print(f"\n✅ Extraction complete using {engine}")
    print(f"📁 JSON saved to: {json_path}")
    print(f"📁 CSV saved to:  {csv_path}")

if __name__ == "__main__":
    if not os.path.exists(PDF_PATH):
        raise FileNotFoundError(f"PDF not found at: {PDF_PATH}")
    pages, engine = extract_text_pages(PDF_PATH)
    write_json_and_csv(pages, OUTPUT_DIR, engine)
