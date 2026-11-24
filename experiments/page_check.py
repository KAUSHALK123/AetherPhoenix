import pypdf

def check(pdf_name):
    print("=== " + pdf_name + " ===")
    reader = pypdf.PdfReader(pdf_name)
    print("Total pages:", len(reader.pages))
    for i, page in enumerate(reader.pages):
        text = page.extract_text()
        print(f"Page {i+1}: chars={len(text)}, first line: {text[:60].strip().replace(chr(10), ' ')}")

check("main_before_final.pdf")
check("main.pdf")
