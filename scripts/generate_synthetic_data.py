"""Generate the SYNTHETIC demo/evaluation dataset (fictional people, fictional companies).

Outputs (in sample_data/):
  synthetic_jobs/jobs.json                 10 job descriptions
  synthetic_candidates/*.pdf|*.docx        30 resumes in 3 different layouts
  synthetic_candidates/manifest.json       design facts per resume (archetype, years) - NOT read by the app
  labels.json                              relevance labels 0-3 for every (job, candidate) pair

Labels come only from the written rule in sample_data/README.md (archetype + years of
experience). They are produced here, from the design manifest, and never from the
matching code - so the evaluation is not circular.

Run:  python scripts/generate_synthetic_data.py      (deterministic: same output every time)
"""
from __future__ import annotations

import io
import json
import random
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "sample_data"
TODAY = date(2026, 10, 1)
rng = random.Random(20261102)

# ----------------------------------------------------------------- archetypes
ARCH = {
    "python_backend": {
        "title": "Backend Engineer (Python)", "dept": "Platform Engineering", "min_exp": 2,
        "required": ["Python", "FastAPI", "PostgreSQL", "REST APIs"], "preferred": ["Docker", "Redis"],
        "edu": "B.E./B.Tech in Computer Science or related field",
        "resp": ["Design and build REST APIs", "Write tests and review code", "Improve database performance"],
        "cand_skills": [["Python", "Django", "Postgres", "REST", "Docker", "Git"],
                        ["Python", "FastAPI", "PostgreSQL", "Redis", "Linux"],
                        ["Python", "Flask", "MySQL", "RESTful APIs", "Celery", "Docker"]],
        "work": "Built RESTful backend services in Python and tuned PostgreSQL queries",
        "project": ("Order Tracking API", "REST API for order tracking using {s0} and {s2} with JWT authentication"),
    },
    "java_backend": {
        "title": "Java Developer", "dept": "Payments", "min_exp": 3,
        "required": ["Java", "Spring Boot", "MySQL", "Microservices"], "preferred": ["Kafka", "Docker"],
        "edu": "Bachelor's degree in Computer Science",
        "resp": ["Develop Spring Boot microservices", "Maintain payment workflows"],
        "cand_skills": [["Java", "Spring Boot", "Hibernate", "MySQL", "Microservices", "Kafka"],
                        ["Core Java", "Spring", "Oracle", "REST APIs", "Maven"],
                        ["Java", "Springboot", "MySQL", "Jenkins", "Docker"]],
        "work": "Developed Spring Boot microservices for payment processing",
        "project": ("Bank Ledger Service", "Ledger microservice built with {s0} and {s1} using event sourcing"),
    },
    "frontend": {
        "title": "Frontend Developer (React)", "dept": "Web", "min_exp": 1,
        "required": ["JavaScript", "TypeScript", "React", "HTML", "CSS"], "preferred": ["Next.js", "Tailwind CSS"],
        "edu": "Any graduate degree",
        "resp": ["Build responsive React interfaces", "Work with designers on UI components"],
        "cand_skills": [["JavaScript", "ReactJS", "HTML5", "CSS3", "Redux", "Figma"],
                        ["TypeScript", "React", "Next.js", "Tailwind", "Jest"],
                        ["JavaScript", "Angular", "HTML", "SCSS", "Bootstrap"]],
        "work": "Built responsive web interfaces and reusable UI components",
        "project": ("Portfolio Builder", "Drag and drop site builder made with {s1} and {s0}"),
    },
    "fullstack_js": {
        "title": "Full Stack Developer (MERN)", "dept": "Product", "min_exp": 2,
        "required": ["Node.js", "Express.js", "React", "MongoDB"], "preferred": ["TypeScript", "AWS"],
        "edu": "B.E./B.Tech or MCA",
        "resp": ["Build features end to end", "Own APIs and UI for product modules"],
        "cand_skills": [["Node.js", "Express", "React", "MongoDB", "JavaScript"],
                        ["NodeJS", "NestJS", "TypeScript", "React", "PostgreSQL"],
                        ["JavaScript", "Node", "Vue.js", "MongoDB", "AWS"]],
        "work": "Built full stack features with a Node.js backend and a JavaScript frontend",
        "project": ("Event Booking App", "Event booking platform with {s0} APIs and a {s2} frontend"),
    },
    "data_science": {
        "title": "Data Scientist", "dept": "Analytics", "min_exp": 2,
        "required": ["Python", "Machine learning", "scikit-learn", "pandas", "Statistics"], "preferred": ["SQL", "Tableau"],
        "edu": "Master's or Bachelor's in Statistics, Mathematics, Computer Science or related field",
        "resp": ["Build predictive models", "Present insights to stakeholders"],
        "cand_skills": [["Python", "Machine Learning", "sklearn", "Pandas", "Statistics", "SQL"],
                        ["R", "Statistics", "Python", "Data Analysis", "Tableau"],
                        ["Python", "ML", "XGBoost", "NumPy", "Matplotlib", "Power BI"]],
        "work": "Built churn and demand forecasting models and presented results to business teams",
        "project": ("Customer Churn Model", "Churn prediction with {s0} and {s2}, deployed as a batch job"),
    },
    "ml_nlp": {
        "title": "Machine Learning Engineer (NLP)", "dept": "AI Research", "min_exp": 3,
        "required": ["Python", "PyTorch", "Natural language processing", "Transformers"], "preferred": ["LLM", "Docker"],
        "edu": "M.Tech/M.S. or B.Tech in Computer Science or Artificial Intelligence",
        "resp": ["Fine-tune language models", "Ship NLP features to production"],
        "cand_skills": [["Python", "PyTorch", "NLP", "Hugging Face", "LLMs", "Docker"],
                        ["Python", "TensorFlow", "Deep Learning", "NLP", "spaCy"],
                        ["Python", "PyTorch", "Computer Vision", "OpenCV", "Deep Learning"]],
        "work": "Trained and deployed deep learning models for text and document understanding",
        "project": ("Ticket Classifier", "Support ticket classifier fine-tuned with {s1} on 50k labelled tickets"),
    },
    "data_engineering": {
        "title": "Data Engineer", "dept": "Data Platform", "min_exp": 3,
        "required": ["Python", "SQL", "Apache Spark", "Apache Airflow"], "preferred": ["Apache Kafka", "AWS"],
        "edu": "Bachelor's degree in Engineering",
        "resp": ["Build batch and streaming pipelines", "Maintain the data warehouse"],
        "cand_skills": [["Python", "SQL", "PySpark", "Airflow", "Kafka", "AWS"],
                        ["Scala", "Spark", "Hadoop", "SQL", "Hive"],
                        ["Python", "SQL", "ETL pipelines", "Snowflake", "dbt"]],
        "work": "Built ETL pipelines that load event data into the data warehouse",
        "project": ("Clickstream Pipeline", "Streaming pipeline using {s2} and {s4} for clickstream events"),
    },
    "devops": {
        "title": "DevOps Engineer", "dept": "Infrastructure", "min_exp": 2,
        "required": ["Docker", "Kubernetes", "AWS", "CI/CD", "Linux"], "preferred": ["Terraform", "Ansible"],
        "edu": "Any bachelor's degree",
        "resp": ["Run Kubernetes clusters", "Automate deployments"],
        "cand_skills": [["Docker", "K8s", "AWS", "Jenkins", "Linux", "Terraform"],
                        ["Azure", "Docker", "GitHub Actions", "Bash", "Ansible"],
                        ["Linux", "Shell scripting", "Nginx", "Docker", "GCP"]],
        "work": "Automated deployments and maintained container infrastructure",
        "project": ("Self-hosted CI", "CI/CD platform on {s0} with automated rollbacks"),
    },
    "mobile": {
        "title": "Android Developer", "dept": "Mobile", "min_exp": 1,
        "required": ["Kotlin", "Android development"], "preferred": ["Flutter", "Firebase"],
        "edu": "B.E./B.Tech in any branch",
        "resp": ["Build Android app features", "Fix crashes and improve performance"],
        "cand_skills": [["Kotlin", "Android", "Firebase", "Java"],
                        ["Flutter", "Dart", "Firebase", "Android"],
                        ["Swift", "iOS", "React Native", "JavaScript"]],
        "work": "Built mobile app features used by thousands of users",
        "project": ("Expense Tracker App", "Mobile expense tracker built with {s0} and {s2}"),
    },
    "qa_automation": {
        "title": "QA Automation Engineer", "dept": "Quality", "min_exp": 0,
        "required": ["Test automation", "API testing", "Python"], "preferred": ["Postman", "CI/CD"],
        "edu": "Bachelor's degree",
        "resp": ["Write automated UI and API tests", "Report and track defects"],
        "cand_skills": [["Selenium", "Python", "Pytest", "Postman", "Jira"],
                        ["Manual Testing", "Selenium", "Java", "TestNG", "SQL"],
                        ["Cypress", "JavaScript", "Postman", "API Testing", "Jenkins"]],
        "work": "Automated regression tests and API checks for web applications",
        "project": ("Regression Suite", "Automated regression suite with {s0} running in CI"),
    },
}
ADJACENT = {
    "python_backend": {"java_backend", "fullstack_js", "data_engineering"},
    "java_backend": {"python_backend"},
    "frontend": {"fullstack_js", "mobile"},
    "fullstack_js": {"frontend", "python_backend"},
    "data_science": {"ml_nlp", "data_engineering"},
    "ml_nlp": {"data_science"},
    "data_engineering": {"data_science", "python_backend"},
    "devops": {"python_backend"},
    "mobile": {"frontend"},
    "qa_automation": {"java_backend", "python_backend"},
}
# each archetype gets a fresher, a mid-level and a senior candidate
YEARS = [0, 3, 7]

FIRST = ["Aarav", "Diya", "Kabir", "Isha", "Rohan", "Sneha", "Vikram", "Nila", "Arjun", "Kavya", "Farhan", "Leela",
         "Nikhil", "Tara", "Siddharth", "Meghna", "Pranav", "Anika", "Rahul", "Zoya", "Varun", "Pooja", "Karthik",
         "Riya", "Imran", "Lakshmi", "Dev", "Shruti", "Aditya", "Neha"]
LAST = ["Raman", "Menon", "Bose", "Pillai", "Kapoor", "Nair", "Rao", "Sethi", "Iyer", "Das", "Khan", "Joseph",
        "Verma", "Shetty", "Reddy", "Ghosh", "Mehta", "Banerjee", "Patil", "Qureshi", "Saxena", "Varma", "Krish",
        "Thomas", "Ali", "Subramanian", "Malhotra", "Kulkarni", "Chandra", "Agarwal"]
COMPANIES = ["Northwind Labs", "Bluepeak Systems", "Quantro Tech", "Lumen Softworks", "Orbitly", "Cedar Analytics",
             "Kestrel Digital", "Monsoon Apps", "Ironleaf Solutions", "Tidewater IT", "Sparrow Cloud", "Vantage Bits"]
COLLEGES = ["Greenfield Institute of Technology", "Riverbank College of Engineering", "Lakeside University",
            "Hillcrest Institute of Science", "Coastal Engineering College"]
DEGREES = {
    "cs": ("B.E. Computer Science and Engineering", "bachelors"),
    "it": ("B.Tech Information Technology", "bachelors"),
    "ece": ("B.E. Electronics and Communication", "bachelors"),
    "mca": ("MCA Computer Applications", "masters"),
    "msc": ("M.Sc. Statistics", "masters"),
}
CERTS = {
    "devops": "AWS Certified Solutions Architect – Associate",
    "data_engineering": "Databricks Certified Data Engineer Associate",
    "java_backend": "Oracle Certified Professional Java SE",
    "data_science": "Machine Learning Specialization (Coursera)",
}

MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def ym_back(months_ago: int) -> tuple[int, int]:
    total = TODAY.year * 12 + (TODAY.month - 1) - months_ago
    return total // 12, total % 12 + 1


def fmt(y, m, style):
    return f"{MONTHS[m - 1]} {y}" if style != 2 else f"{m:02d}/{y}"


def build_candidates():
    cands = []
    i = 0
    for arch, spec in ARCH.items():
        for variant, years in enumerate(YEARS):
            first, last = FIRST[i], LAST[i]
            skills = list(spec["cand_skills"][variant])
            rng.shuffle(skills)
            layout = i % 3
            deg_key = rng.choice(["cs", "it", "cs", "ece", "mca"] if arch != "data_science" else ["msc", "cs"])
            grad_year = TODAY.year - years - (0 if years else 0) - (1 if years else 0)
            jobs = []
            if years == 0:
                s, e = ym_back(10), ym_back(5)
                jobs.append({"title": f"{spec['title'].split('(')[0].strip()} Intern", "company": rng.choice(COMPANIES),
                             "start": s, "end": e, "present": False,
                             "bullets": [spec["work"] + ".", f"Used {skills[0]} and {skills[1]} daily."]})
            else:
                remaining = years * 12
                cursor = 0
                n_jobs = 1 if years < 5 else 2
                for j in range(n_jobs):
                    length = remaining - cursor if j == n_jobs - 1 else remaining // 2
                    s, e = ym_back(cursor + length - 1), ym_back(cursor)
                    jobs.append({"title": ("Senior " if j == 0 and years >= 5 else "") + spec["title"].split("(")[0].strip(),
                                 "company": rng.choice(COMPANIES), "start": s, "end": e, "present": j == 0,
                                 "bullets": [spec["work"] + f" using {skills[j % len(skills)]}.",
                                             f"Worked with {skills[(j + 1) % len(skills)]} and {skills[(j + 2) % len(skills)]}."]})
                    cursor += length
            pname, ptemplate = spec["project"]
            proj = (pname, ptemplate.format(**{f"s{k}": spec["cand_skills"][variant][k] for k in range(len(spec["cand_skills"][variant]))}))
            certs = [CERTS[arch]] if arch in CERTS and years >= 3 else []
            cands.append({
                "id": f"cand{i + 1:02d}", "name": f"{first} {last}",
                "email": f"{first.lower()}.{last.lower()}@example.com",
                "phone": f"+91 9{rng.randint(100000000, 999999999)}",
                "archetype": arch, "years": years, "skills": skills, "layout": layout,
                "degree": DEGREES[deg_key][0], "college": rng.choice(COLLEGES),
                "edu_years": (grad_year - (2 if DEGREES[deg_key][1] == "masters" else 4), grad_year),
                "jobs": jobs, "project": proj, "certs": certs,
                "summary": (f"{'Fresh graduate' if years == 0 else f'Engineer with {years} years of experience'} "
                            f"interested in {spec['title'].split('(')[0].strip().lower()} work."),
            })
            i += 1
    return cands


def resume_lines(c: dict) -> list[tuple[str, str]]:
    """Return (kind, text) lines. kind: name|contact|heading|text|bullet."""
    L = c["layout"]
    H = {0: ["PROFESSIONAL SUMMARY", "TECHNICAL SKILLS", "WORK EXPERIENCE", "EDUCATION", "PROJECTS", "CERTIFICATIONS"],
         1: ["Profile", "Skills", "Experience", "Education", "Projects", "Certifications"],
         2: ["Career Objective", "Key Skills", "Professional Experience", "Academic Background", "Academic Projects",
             "Courses"]}[L]
    out = [("name", c["name"]), ("contact", f"{c['email']} | {c['phone']} | Bengaluru, India")]
    out += [("heading", H[0]), ("text", c["summary"])]
    out += [("heading", H[1])]
    if L == 1:
        out.append(("text", ", ".join(c["skills"])))
    else:
        half = len(c["skills"]) // 2 or 1
        out.append(("bullet", "Languages & frameworks: " + ", ".join(c["skills"][:half])))
        out.append(("bullet", "Tools: " + ", ".join(c["skills"][half:])))
    out.append(("heading", H[2]))
    for j in c["jobs"]:
        start = fmt(*j["start"], L)
        end = "Present" if j["present"] else fmt(*j["end"], L)
        if L == 0:
            out.append(("text", f"{j['title']} | {j['company']}"))
            out.append(("text", f"{start} - {end}"))
        elif L == 1:
            out.append(("text", f"{j['title']} at {j['company']}"))
            out.append(("text", f"{start} – {end}"))
        else:
            out.append(("text", f"{j['company']}, {j['title']}"))
            out.append(("text", f"{start} to {end}"))
        out += [("bullet", b) for b in j["bullets"]]
    out.append(("heading", H[3]))
    out.append(("text", c["degree"]))
    out.append(("text", f"{c['college']} | {c['edu_years'][0]} - {c['edu_years'][1]} | CGPA: {rng.choice(['7.6', '8.1', '8.7', '9.0'])}/10"))
    out.append(("heading", H[4]))
    out.append(("text", f"{c['project'][0]}: {c['project'][1]}"))
    if c["certs"]:
        out.append(("heading", H[5]))
        out += [("bullet", f"{x} - {TODAY.year - 1}") for x in c["certs"]]
    return out


def render_pdf(lines, path: Path, layout: int):
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas

    c = canvas.Canvas(str(path), pagesize=A4)
    c.setTitle("Synthetic resume (fictional person)")
    y = 800
    for kind, text in lines:
        if y < 60:
            c.showPage()
            y = 800
        if kind == "name":
            c.setFont("Helvetica-Bold", 18); c.drawString(50, y, text); y -= 22
        elif kind == "contact":
            c.setFont("Helvetica", 9); c.drawString(50, y, text); y -= 22
        elif kind == "heading":
            y -= 6
            c.setFont("Helvetica-Bold", 11 if layout == 0 else 12); c.drawString(50, y, text); y -= 16
        elif kind == "bullet":
            c.setFont("Helvetica", 10); c.drawString(60, y, "• " + text); y -= 14
        else:
            c.setFont("Helvetica", 10)
            words, line = text.split(), ""
            for w in words:
                if len(line) + len(w) > 95:
                    c.drawString(50, y, line); y -= 14; line = ""
                line += w + " "
            c.drawString(50, y, line.strip()); y -= 14
    c.save()


def render_docx(lines, path: Path):
    import docx
    from docx.shared import Pt

    d = docx.Document()
    for kind, text in lines:
        if kind == "name":
            p = d.add_paragraph(); r = p.add_run(text); r.bold = True; r.font.size = Pt(18)
        elif kind == "heading":
            d.add_heading(text, level=2)
        elif kind == "bullet":
            d.add_paragraph(text, style="List Bullet")
        else:
            d.add_paragraph(text)
    d.save(str(path))


def job_description(spec: dict) -> str:
    lines = [spec["title"], f"Department: {spec['dept']}", "",
             f"We are a fictional company hiring a {spec['title'].lower()}.", "", "Responsibilities:"]
    lines += [f"- {r}" for r in spec["resp"]]
    lines += ["", "Requirements:"]
    exp = "Freshers welcome" if spec["min_exp"] == 0 else f"{spec['min_exp']}+ years of experience"
    lines += [f"- {exp}", f"- Strong skills in {', '.join(spec['required'])}", f"- {spec['edu']}",
              "- Good communication and teamwork"]
    lines += ["", "Nice to have:", f"- {', '.join(spec['preferred'])}"]
    return "\n".join(lines)


def label(job_arch: str, job_min: float, c: dict) -> int:
    """THE LABEL RULE (documented in sample_data/README.md)."""
    meets = c["years"] >= job_min
    if c["archetype"] == job_arch:
        return 3 if meets else 2
    if c["archetype"] in ADJACENT[job_arch] or job_arch in ADJACENT[c["archetype"]]:
        return 2 if meets else 1
    return 0


def main():
    (OUT / "synthetic_jobs").mkdir(parents=True, exist_ok=True)
    cdir = OUT / "synthetic_candidates"
    cdir.mkdir(parents=True, exist_ok=True)
    for f in cdir.glob("cand*"):
        f.unlink()

    jobs = []
    for n, (arch, spec) in enumerate(ARCH.items(), start=1):
        jobs.append({"id": f"job{n:02d}", "archetype": arch, "title": spec["title"], "department": spec["dept"],
                     "minimum_experience": spec["min_exp"], "description": job_description(spec), "synthetic": True})
    (OUT / "synthetic_jobs" / "jobs.json").write_text(json.dumps(jobs, indent=2), encoding="utf-8")

    cands = build_candidates()
    manifest = []
    for c in cands:
        lines = resume_lines(c)
        fname = f"{c['id']}.docx" if c["layout"] == 1 else f"{c['id']}.pdf"
        if c["layout"] == 1:
            render_docx(lines, cdir / fname)
        else:
            render_pdf(lines, cdir / fname, c["layout"])
        manifest.append({"id": c["id"], "file": fname, "name": c["name"], "email": c["email"],
                         "archetype": c["archetype"], "years": c["years"], "layout": c["layout"], "synthetic": True})
    (cdir / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    labels = {j["id"]: {c["id"]: label(j["archetype"], j["minimum_experience"], c) for c in cands} for j in jobs}
    (OUT / "labels.json").write_text(json.dumps({
        "_note": "Synthetic relevance labels 0-3. Produced only from the rule in sample_data/README.md "
                 "(archetype + years), never from the matching code.",
        "labels": labels}, indent=2), encoding="utf-8")
    print(f"Wrote {len(jobs)} jobs, {len(cands)} resumes, {sum(len(v) for v in labels.values())} labels to {OUT}")


if __name__ == "__main__":
    main()
