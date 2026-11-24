import re
import pypdf

def audit_file(filepath):
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()
    
    print(f"=== Auditing {filepath} ===")
    forbidden = ["TODO", "TBD", "ASK ME", "dag.replanned"]
    for word in forbidden:
        if word in content:
            print(f"WARNING: Found '{word}' in {filepath}")
    
    # Check citation order in text
    cites = re.findall(r'\\cite\{([^}]+)\}', content)
    expanded_cites = []
    for c in cites:
        for item in c.split(','):
            expanded_cites.append(item.strip())
    
    seen = []
    for c in expanded_cites:
        if c not in seen:
            seen.append(c)
    
    bib_items = re.findall(r'\\bibitem\{([^}]+)\}', content)
    print("Citation first appearance order:", seen)
    print("Bibitem definition order:       ", bib_items)
    if seen == bib_items:
        print("PERFECT: Citation order matches Bibitem order exactly!")
    else:
        print("MISMATCH between citation first appearance and bibitem order:")
        print("Seen diff:", [x for x in seen if x not in bib_items])
        print("Bib diff: ", [x for x in bib_items if x not in seen])

def check_pdf(pdf_name):
    reader = pypdf.PdfReader(pdf_name)
    print(f"=== {pdf_name}: {len(reader.pages)} pages ===")

audit_file("main.tex")
audit_file("main_highlighted.tex")
check_pdf("main.pdf")
check_pdf("main_highlighted.pdf")
check_pdf("main_before_final.pdf")
