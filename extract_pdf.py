import PyPDF2
import sys

def extract_text(pdf_path):
    try:
        reader = PyPDF2.PdfReader(pdf_path)
        text = ""
        for page in reader.pages:
            extracted = page.extract_text()
            if extracted:
                text += extracted + "\n"
        return text
    except Exception as e:
        return str(e)

if __name__ == "__main__":
    with open("extracted_requirements.txt", "w", encoding="utf-8") as f:
        f.write(extract_text("Sriram_Idea_Whatsapp_GST.pdf"))
