import fitz
doc = fitz.open("2026-Humana-miniMarathon-Marathon-Course.pdf")
for i, p in enumerate(doc):
    pix = p.get_pixmap(dpi=200)
    pix.save(f"course_page_{i+1}.png")
    print(f"Page {i+1}: {pix.width}x{pix.height}")
print("done")
