/** Builds a small, valid text PDF in memory (no dependencies), so every test run has unique resume files. */
export function makePdf(lines: string[]): Buffer {
  const esc = (s: string) =>
    s.replace(/\\/g, "\\\\").replace(/\(/g, "\\(").replace(/\)/g, "\\)");
  const content = [
    "BT",
    "/F1 10 Tf",
    "14 TL",
    "50 800 Td",
    ...lines.map((l) => `(${esc(l)}) '`),
    "ET",
  ].join("\n");
  const objects = [
    "<< /Type /Catalog /Pages 2 0 R >>",
    "<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
    "<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>",
    "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    `<< /Length ${Buffer.byteLength(content)} >>\nstream\n${content}\nendstream`,
  ];
  let out = "%PDF-1.4\n";
  const offsets: number[] = [];
  objects.forEach((o, i) => {
    offsets.push(Buffer.byteLength(out));
    out += `${i + 1} 0 obj\n${o}\nendobj\n`;
  });
  const xref = Buffer.byteLength(out);
  out += `xref\n0 ${objects.length + 1}\n0000000000 65535 f \n`;
  out += offsets
    .map((n) => `${String(n).padStart(10, "0")} 00000 n \n`)
    .join("");
  out += `trailer\n<< /Size ${objects.length + 1} /Root 1 0 R >>\nstartxref\n${xref}\n%%EOF\n`;
  return Buffer.from(out, "latin1");
}

export function resumeLines(
  name: string,
  email: string,
  variant: "backend" | "frontend",
): string[] {
  const backend = [
    name,
    `${email} | +91 98765 43210 | Chennai`,
    "SUMMARY",
    "Backend developer building REST APIs in Python.",
    "TECHNICAL SKILLS",
    "Python, Django, PostgreSQL, Docker, Git",
    "EXPERIENCE",
    "Software Engineer | Zenith Labs",
    "Jun 2021 - Dec 2024",
    "- Built RESTful services with Django and PostgreSQL.",
    "EDUCATION",
    "B.E. Computer Science and Engineering",
    "Kumaraguru College of Technology | 2017 - 2021",
    "PROJECTS",
    "Inventory Tracker: Inventory app using FastAPI and React.",
  ];
  const frontend = [
    name,
    `${email} | +91 90000 11111`,
    "SKILLS",
    "JavaScript, React, HTML, CSS, Figma",
    "EXPERIENCE",
    "Frontend Developer | Pixel Co",
    "Jan 2022 - Dec 2024",
    "- Built React dashboards.",
    "EDUCATION",
    "B.Sc. Mathematics",
    "Some College | 2018 - 2021",
  ];
  return variant === "backend" ? backend : frontend;
}
