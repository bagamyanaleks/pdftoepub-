import zipfile, sys
from lxml import etree
sys.stdout.reconfigure(encoding="utf-8")

epub_path = "converted_ebooks/Ayşe Kulin Kanadı Kırık Kuşlar Everest Yayınları (2).epub"
with zipfile.ZipFile(epub_path, "r") as z:
    print("=== IMAGES IN EPUB ===")
    for name in z.namelist():
        if "images/" in name:
            print(" ", name)

    print("\n=== CHAPTERS SUMMARY ===")
    for name in sorted(z.namelist()):
        if name.endswith(".xhtml") and "chapter" in name:
            raw = z.read(name)
            parser = etree.XMLParser(recover=False)
            doc = etree.fromstring(raw, parser=parser)
            title = doc.xpath("//xhtml:h1", namespaces={"xhtml": "http://www.w3.org/1999/xhtml"})
            imgs = doc.xpath("//xhtml:img", namespaces={"xhtml": "http://www.w3.org/1999/xhtml"})
            paras = doc.xpath("//xhtml:p", namespaces={"xhtml": "http://www.w3.org/1999/xhtml"})
            title_text = title[0].text if title else "No H1"
            img_srcs = [im.get("src") for im in imgs]
            first_p = paras[0].text[:80] if paras and paras[0].text else ""
            print(f"{name}: Title={title_text!r}, Images={img_srcs}")
            print(f"   First P: {first_p!r}")
