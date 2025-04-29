import fitz  # PyMuPDF
from PIL import Image
import pytesseract
import io

def pdf_to_text_ocr(pdf_path):
    # Aprire il documento PDF
    doc = fitz.open(pdf_path)
    text = ""

    # Iterare ogni pagina del documento
    for page_number, page in enumerate(doc):
        # Converti la pagina in un pixmap (immagine raster)
        pix = page.get_pixmap()
        # Converti il pixmap in un oggetto PIL Image per l'elaborazione
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)

        # Applica OCR sull'immagine usando pytesseract
        page_text = pytesseract.image_to_string(img, lang='ita')  # Specifica la lingua se necessario
        text += page_text
        print(f"Testo OCR estratto dalla pagina {page_number + 1}: {page_text[:100]}...")  # Stampa un'anteprima del testo estratto

    # Chiudi il documento
    doc.close()
    return text

# Percorso del PDF da analizzare
pdf_path = "data\\Alessandra Luca 2025Mktg-ENG.pdf"
extracted_text = pdf_to_text_ocr(pdf_path)
print("\nTesto completo estratto dal PDF:")
print(extracted_text)
