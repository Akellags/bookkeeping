import PyPDF2
import sys

def extract_text(pdf_path):
    try:
        reader = PyPDF2.PdfReader(pdf_path)
        text = ""
        # Just extract first 5 pages to see the structure
        for i in range(min(5, len(reader.pages))):
            extracted = reader.pages[i].extract_text()
            if extracted:
                text += f"--- Page {i+1} ---\n" + extracted + "\n"
        return text
    except Exception as e:
        return str(e)

if __name__ == "__main__":
    print(extract_text(r"c:\Users\ALIENWARE\Projects\helpU\bookkeeper\docs\Goods Items HSN and Rates.pdf"))
