import { expect, test, type Page } from "@playwright/test";

import { makePdf, resumeLines } from "./pdf";

// Full workflows from the project brief. They run against the real backend with LLM_PROVIDER=none,
// so interview answers end as "AI evaluation pending" (that state is asserted on purpose).
test.describe.configure({ mode: "serial" });
test.use({ viewport: { width: 1360, height: 900 } });
test.skip(
  ({ isMobile }) => isMobile,
  "Full flows run on desktop; mobile is covered by auth.spec.ts",
);

const run = `${Date.now()}`;
const recruiter = { name: "Rhea Recruiter", email: `rhea-${run}@example.com` };
const candidate = { name: "Nila Raman", email: `nila-${run}@example.com` };
const password = "Password123";

async function register(
  page: Page,
  who: { name: string; email: string },
  role: "recruiter" | "candidate",
) {
  await page.goto(`/register?role=${role}`);
  await page.getByLabel("Full name").fill(who.name);
  await page.getByLabel("Email").fill(who.email);
  await page.getByLabel("Password", { exact: true }).fill(password);
  await page.getByLabel("Confirm password").fill(password);
  await page.getByRole("button", { name: "Create account" }).click();
}

test("recruiter: job → bulk upload → profile → matching → interview → candidate answers → report PDF", async ({
  browser,
}) => {
  test.setTimeout(240_000);
  // The candidate registers first, so the recruiter's upload links to their account (same email).
  const cctx = await browser.newContext();
  const cpage = await cctx.newPage();
  await register(cpage, candidate, "candidate");
  await expect(cpage).toHaveURL(/\/candidate\/home$/);

  const rctx = await browser.newContext();
  const page = await rctx.newPage();
  await register(page, recruiter, "recruiter");
  await expect(page).toHaveURL(/\/dashboard$/);
  await expect(page.getByText("Start by creating a job")).toBeVisible();

  // Create a job by pasting a description and extracting requirements
  await page.getByRole("link", { name: "New job" }).first().click();
  await page.getByLabel("Job title").fill(`Backend Engineer ${run}`);
  await page
    .getByLabel("Full description")
    .fill(
      "Backend Engineer\nRequirements:\n- 2+ years of experience with Python, FastAPI and PostgreSQL\n- REST APIs\nNice to have:\n- Docker, Kubernetes",
    );
  await page
    .getByRole("button", { name: "Extract requirements from description" })
    .click();
  await expect(page.getByText(/Found \d+ required/)).toBeVisible();
  await expect(
    page.getByRole("button", { name: "Remove FastAPI" }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Create job" }).click();
  await expect(page).toHaveURL(/\/jobs\/[0-9a-f-]+$/);
  await page.getByRole("button", { name: "Publish" }).click();
  await expect(page.getByText("Job is now published")).toBeVisible();

  // Bulk upload: two valid resumes and one invalid file
  await page.getByRole("button", { name: "Upload resumes" }).first().click();
  await page.getByLabel("Resume files").setInputFiles([
    {
      name: "nila.pdf",
      mimeType: "application/pdf",
      buffer: makePdf(resumeLines(candidate.name, candidate.email, "backend")),
    },
    {
      name: "meera.pdf",
      mimeType: "application/pdf",
      buffer: makePdf(
        resumeLines(`Meera Iyer`, `meera-${run}@example.com`, "frontend"),
      ),
    },
  ]);
  await expect(page.getByText("2 files uploaded")).toBeVisible();
  await expect(page.getByText(/skills found/)).toHaveCount(2, {
    timeout: 60_000,
  });
  await page.getByRole("button", { name: "Done" }).click();

  // Run matching and read the explanation
  await page.getByRole("button", { name: "Run matching" }).click();
  await expect(page.getByText(/Scored 2 candidates/)).toBeVisible({
    timeout: 60_000,
  });
  const rows = page.locator("table tbody tr");
  await expect(rows).toHaveCount(2);
  await expect(rows.first()).toContainText(candidate.name); // backend profile ranks first
  await rows.first().getByRole("button", { name: "Why?" }).click();
  const dialog = page.getByRole("dialog");
  await expect(dialog.getByText("Semantic similarity")).toBeVisible();
  await expect(
    dialog.getByText("FastAPI", { exact: true }).first(),
  ).toBeVisible();
  await expect(dialog.getByText(/not a probability/i).first()).toBeVisible();
  await page.keyboard.press("Escape");

  // Review the profile and correct a field
  await rows.first().getByRole("link", { name: candidate.name }).click();
  await expect(
    page.getByRole("heading", { name: candidate.name }),
  ).toBeVisible();
  await expect(page.getByText("Django", { exact: true }).first()).toBeVisible();
  await page.getByRole("button", { name: "Correct details" }).click();
  await page.getByLabel("Phone").fill("+91 99999 00000");
  await page.getByRole("button", { name: "Save", exact: true }).click();
  await expect(page.getByText("+91 99999 00000")).toBeVisible();

  // Create an interview (question bank, since no LLM is configured)
  await page.getByRole("button", { name: "Create interview" }).click();
  await page.getByRole("dialog").getByLabel("Questions").selectOption("3");
  await page.getByRole("button", { name: "Generate questions" }).click();
  await expect(page).toHaveURL(/\/interviews\/[0-9a-f-]+$/, {
    timeout: 30_000,
  });
  await expect(page.getByText(/Questions are ready/)).toBeVisible();
  await expect(page.locator("ol > li")).toHaveCount(3);
  const interviewUrl = page.url();

  // The candidate takes the interview
  await cpage.goto("/candidate/interviews");
  await cpage
    .getByRole("link", { name: new RegExp(`Backend Engineer ${run}`) })
    .click();
  await cpage.getByRole("button", { name: "Start interview" }).click();
  for (let i = 0; i < 3; i++) {
    await expect(cpage.getByText(`Question ${i + 1} of 3`)).toBeVisible();
    await cpage
      .getByLabel("Your answer")
      .fill(
        `Answer ${i + 1}: I would design clear REST endpoints, validate input and return proper status codes.`,
      );
    await cpage.getByRole("button", { name: "Submit answer" }).click();
  }
  await cpage.getByRole("button", { name: "Submit interview" }).click();
  await expect(cpage.getByText("Overall interview score")).toBeVisible();
  await expect(cpage.getByText("AI evaluation pending").first()).toBeVisible();

  // Recruiter sees the answers, tries evaluation, and downloads the report
  await page.goto(interviewUrl);
  await expect(page.getByText("AI evaluation pending").first()).toBeVisible();
  await expect(
    page.getByText("Basic concept coverage check (not a score)").first(),
  ).toBeVisible();
  await page.getByRole("button", { name: "Evaluate pending" }).click();
  await expect(page.getByText(/still need an AI model/)).toBeVisible();
  await page.getByRole("button", { name: "Generate report" }).click();
  await expect(page).toHaveURL(/\/reports\/[0-9a-f-]+$/, { timeout: 30_000 });
  await expect(page.getByText("Job compatibility")).toBeVisible();
  await page
    .getByLabel("New comment")
    .fill("Good backend fit. Check FastAPI depth in next round.");
  await page.getByRole("button", { name: "Add comment" }).click();
  await expect(page.getByText("Recruiter comment ·").first()).toBeVisible();
  const [download] = await Promise.all([
    page.waitForEvent("download"),
    page.getByRole("link", { name: "Download PDF" }).click(),
  ]);
  const path = await download.path();
  const { readFileSync } = await import("node:fs");
  expect(readFileSync(path!).subarray(0, 4).toString()).toBe("%PDF");

  // Pipeline: move the candidate (Rejected/Selected need confirmation)
  await page.goto("/candidates");
  await page.getByRole("link", { name: candidate.name }).click();
  await page.getByLabel("Recruitment stage").first().selectOption("selected");
  await expect(
    page.getByText("This is a hiring decision made by you"),
  ).toBeVisible();
  await page.getByRole("button", { name: "Mark as Selected" }).click();
  await expect(page.getByText("Moved to Selected")).toBeVisible();

  // Dashboard numbers come from the data we just created
  await page.goto("/dashboard");
  await expect(
    page.getByText("Interviews completed").locator(".."),
  ).toContainText("1");
  await rctx.close();
  await cctx.close();
});

test("candidate: register → upload resume → apply → practice interview → feedback", async ({
  page,
  request,
}) => {
  test.setTimeout(180_000);
  // A recruiter publishes a job through the API (setup only)
  const rec = { name: "Api Recruiter", email: `api-rec-${run}@example.com` };
  const r = await request.post("/api/v1/auth/register", {
    data: { ...rec, password, role: "recruiter" },
  });
  expect(r.status()).toBe(201);
  const job = await (
    await request.post("/api/v1/jobs", {
      data: {
        title: `Data Analyst ${run}`,
        description: "Python SQL",
        required_skills: ["Python", "SQL"],
        minimum_experience: 1,
      },
    })
  ).json();
  expect((await request.post(`/api/v1/jobs/${job.id}/publish`)).status()).toBe(
    200,
  );

  const me = { name: "Arun Kumar", email: `arun-${run}@example.com` };
  await register(page, me, "candidate");
  await expect(
    page.getByText("Upload your resume to get started"),
  ).toBeVisible();
  await page.getByRole("link", { name: "Upload resume" }).click();
  await page
    .getByLabel("Resume files")
    .setInputFiles({
      name: "arun.pdf",
      mimeType: "application/pdf",
      buffer: makePdf(resumeLines(me.name, me.email, "backend")),
    });
  await expect(page.getByText(/skills found/)).toBeVisible({ timeout: 60_000 });
  await expect(page.getByRole("heading", { name: me.name })).toBeVisible({
    timeout: 15_000,
  });

  await page.goto("/candidate/jobs");
  const card = page.locator("li", { hasText: `Data Analyst ${run}` });
  await card.getByRole("button", { name: "Apply" }).click();
  await expect(page.getByText("Application sent")).toBeVisible();
  await expect(card.getByText("Applied")).toBeVisible();

  await page.goto("/candidate/applications");
  await expect(page.getByText(`Data Analyst ${run}`)).toBeVisible();
  await page.getByRole("button", { name: "Practice interview" }).click();
  await page.getByRole("dialog").getByLabel("Questions").selectOption("3");
  await page.getByRole("button", { name: "Generate questions" }).click();
  await expect(page).toHaveURL(/\/candidate\/interviews\/[0-9a-f-]+$/, {
    timeout: 30_000,
  });
  await page.getByRole("button", { name: "Start interview" }).click();
  await page
    .getByLabel("Your answer")
    .fill("Partial answer typed before leaving.");
  await page.waitForTimeout(11_000); // autosave every 10 s
  await page.reload();
  await expect(page.getByLabel("Your answer")).toHaveValue(
    "Partial answer typed before leaving.",
  );
  await page.getByRole("button", { name: "Finish interview" }).click();
  await page.getByRole("button", { name: "Finish interview" }).last().click();
  await expect(page.getByText("Overall interview score")).toBeVisible();

  await page.goto("/candidate/feedback");
  await expect(page.getByText(`Data Analyst ${run}`)).toBeVisible();

  // Privacy: candidate cannot open recruiter pages or other people's data
  await page.goto("/jobs");
  await expect(page).toHaveURL(/\/candidate\/home$/);
  const other = await page.request.get(`/api/v1/jobs/${job.id}/applications`);
  expect(other.status()).toBe(403);
});
