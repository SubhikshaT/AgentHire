"""Small helpers shared by tests."""
from fastapi.testclient import TestClient


def register(client: TestClient, role: str = "recruiter", email: str | None = None, name: str = "Test User"):
    email = email or f"{role}@example.com"
    r = client.post(
        "/api/v1/auth/register",
        json={"name": name, "email": email, "password": "Password123", "role": role},
    )
    assert r.status_code == 201, r.text
    return r.json()


def make_pdf(text: str) -> bytes:
    """Build a simple text PDF (one line per text line) with ReportLab."""
    import io

    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas

    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    y = 800
    for line in text.split("\n"):
        if y < 50:
            c.showPage()
            y = 800
        c.drawString(40, y, line)
        y -= 14
    c.save()
    return buf.getvalue()


def make_docx(text: str) -> bytes:
    import io

    import docx

    d = docx.Document()
    for line in text.split("\n"):
        d.add_paragraph(line)
    buf = io.BytesIO()
    d.save(buf)
    return buf.getvalue()


SAMPLE_RESUME = """Ananya Krishnan
Chennai | ananya.k@example.com | +91 98765 43210

SUMMARY
Backend developer building REST APIs in Python.

TECHNICAL SKILLS
Python, Django, PostgreSQL, Docker, Git, C

EXPERIENCE
Software Engineer | Zenith Labs
Jun 2022 - Dec 2024
- Built RESTful services with Django and PostgreSQL.

EDUCATION
B.E. Computer Science and Engineering
Kumaraguru College of Technology | 2018 - 2022

PROJECTS
Inventory Tracker: Inventory app using FastAPI and React.

CERTIFICATIONS
AWS Certified Cloud Practitioner 2023
"""


def create_job(client, title="Backend Engineer", required=("Python", "FastAPI", "PostgreSQL"), publish=True, **extra):
    body = {"title": title, "description": "Backend role", "required_skills": list(required),
            "preferred_skills": extra.pop("preferred", ["Docker"]), "minimum_experience": extra.pop("min_exp", 1),
            **extra}
    r = client.post("/api/v1/jobs", json=body)
    assert r.status_code == 201, r.text
    job = r.json()
    if publish:
        assert client.post(f"/api/v1/jobs/{job['id']}/publish").status_code == 200
    return job
