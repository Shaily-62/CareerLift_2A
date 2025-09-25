import re
import fitz  # PyMuPDF to read PDFs

# A small dictionary of skills (you can expand this list)
SKILL_KEYWORDS = [
    "python", "java", "c++", "sql", "machine learning", "deep learning",
    "tensorflow", "pytorch", "data analysis", "excel", "nlp", "cloud",
    "aws", "azure", "git", "javascript", "html", "css", "react", "flask",
    "django", "mongodb", "mysql", "postgresql","nodejs"
]

def extract_skills_from_pdf(file):
    """Extracts skills from a resume PDF based on keyword matching."""
    text = ""
    doc = fitz.open(stream=file.read(), filetype="pdf")
    for page in doc:
        text += page.get_text("text")

    text = text.lower()

    found_skills = [skill for skill in SKILL_KEYWORDS if skill in text]

    return list(set(found_skills))  # remove duplicates
