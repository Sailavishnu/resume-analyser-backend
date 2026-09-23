import urllib.request
import json
try:
    import pymupdf as fitz
except ImportError:
    import fitz

doc = fitz.open()
page = doc.new_page()
page.insert_text((50, 72), "Saila Vishnu G\nBackend & Fullstack Developer\nEmail: test@gmail.com | Phone: 9876543210\n\nSKILLS\nJavaScript, Python, React, FastAPI, Docker, PostgreSQL, MongoDB\n\nPROJECTS\nPlacement Preparation Platform (PPP)\nBuilt unified MERN platform with JWT authentication, real-time messaging, and AI mock interviews.\n\nEXPERIENCE\nWeb Developer Intern at Tech Corp\nOptimized database indexing and handled API performance under load.\n\nEDUCATION\nBachelor of Engineering in Computer Science (2024-2028)")
pdf_bytes = doc.write()

boundary = "----WebKitFormBoundary7MA4YWxkTrZu0gW"
body = bytearray()
body.extend(f"--{boundary}\r\n".encode())
body.extend(b'Content-Disposition: form-data; name="file"; filename="sample_resume.pdf"\r\n')
body.extend(b"Content-Type: application/pdf\r\n\r\n")
body.extend(pdf_bytes)
body.extend(f"\r\n--{boundary}--\r\n".encode())

req = urllib.request.Request(
    "http://127.0.0.1:8000/api/v1/resumes/upload?slot=primary",
    data=body,
    headers={"Content-Type": f"multipart/form-data; boundary={boundary}"}
)

try:
    res = urllib.request.urlopen(req)
    data = json.loads(res.read().decode())
    print("SUCCESSFUL UPLOAD TO CLOUDINARY & MONGO:")
    print(json.dumps(data, indent=2))
except urllib.error.HTTPError as e:
    print("HTTP ERROR:", e.code, e.read().decode())
except Exception as e:
    print("ERROR:", e)
