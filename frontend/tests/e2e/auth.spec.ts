import { expect, test, type Page } from "@playwright/test";

const unique = () => `${Date.now()}-${Math.floor(Math.random() * 1e6)}`;

async function openMenuIfMobile(page: Page) {
  const menu = page.getByRole("button", { name: "Open menu" });
  if (await menu.isVisible()) await menu.click();
}

test("landing page links to login and register", async ({ page }) => {
  await page.goto("/");
  await expect(
    page.getByRole("heading", { name: /Screen faster/ }),
  ).toBeVisible();
  await page.getByRole("link", { name: "Log in" }).click();
  await expect(page).toHaveURL(/\/login$/);
  await expect(
    page.getByRole("heading", { name: "Welcome back" }),
  ).toBeVisible();
});

test("register form validates input", async ({ page }) => {
  await page.goto("/register");
  await page.getByRole("button", { name: "Create account" }).click();
  await expect(
    page.getByText("Choose how you will use AgentHire"),
  ).toBeVisible();
  await expect(page.getByText("Enter your full name")).toBeVisible();
  await expect(page.getByText("Enter a valid email address")).toBeVisible();
  await expect(page.getByText("Use at least 8 characters")).toBeVisible();
});

test("recruiter can register, sees recruiter nav, logs out and back in", async ({
  page,
}) => {
  const email = `rec-${unique()}@example.com`;
  await page.goto("/register?role=recruiter");
  await page.getByLabel("Full name").fill("Priya Recruiter");
  await page.getByLabel("Email").fill(email);
  await page.getByLabel("Password", { exact: true }).fill("Password123");
  await page.getByLabel("Confirm password").fill("Password123");
  await page.getByRole("button", { name: "Create account" }).click();

  await expect(page).toHaveURL(/\/dashboard$/);
  await expect(
    page.getByRole("heading", { name: "Hello, Priya" }),
  ).toBeVisible();

  await openMenuIfMobile(page);
  const nav = page.getByRole("navigation", { name: "Main" }).last();
  await expect(nav.getByRole("link", { name: "Overview" })).toBeVisible();
  await expect(nav.getByText("Resume Screening")).toBeVisible();
  await expect(nav.getByText("Browse Jobs")).toHaveCount(0);
  await page.keyboard.press("Escape");

  // Candidate area is not allowed for a recruiter: redirected home.
  await page.goto("/candidate/home");
  await expect(page).toHaveURL(/\/dashboard$/);

  await page.getByRole("button", { name: "Account menu" }).click();
  await page.getByRole("menuitem", { name: "Log out" }).click();
  await expect(page).toHaveURL(/\/login/);

  await page.goto("/dashboard");
  await expect(page).toHaveURL(/\/login\?next=%2Fdashboard/);

  await page.getByLabel("Email").fill(email);
  await page.getByLabel("Password", { exact: true }).fill("wrong-password");
  await page.getByRole("button", { name: "Log in" }).click();
  await expect(page.getByText("Incorrect email or password.")).toBeVisible();

  await page.getByLabel("Password", { exact: true }).fill("Password123");
  await page.getByRole("button", { name: "Log in" }).click();
  await expect(page).toHaveURL(/\/dashboard$/);
});

test("candidate registers and lands on candidate home", async ({ page }) => {
  await page.goto("/register");
  await page.getByText("Candidate", { exact: true }).click();
  await page.getByLabel("Full name").fill("Arun Candidate");
  await page.getByLabel("Email").fill(`cand-${unique()}@example.com`);
  await page.getByLabel("Password", { exact: true }).fill("Password123");
  await page.getByLabel("Confirm password").fill("Password123");
  await page.getByRole("button", { name: "Create account" }).click();

  await expect(page).toHaveURL(/\/candidate\/home$/);
  await expect(
    page.getByRole("heading", { name: "Hello, Arun" }),
  ).toBeVisible();

  await page.goto("/dashboard");
  await expect(page).toHaveURL(/\/candidate\/home$/);
});

test("duplicate email shows a field error", async ({ page, request }) => {
  const email = `dup-${unique()}@example.com`;
  const r = await request.post("/api/v1/auth/register", {
    data: { name: "First", email, password: "Password123", role: "candidate" },
  });
  expect(r.status()).toBe(201);

  await page.goto("/register?role=candidate");
  await page.getByLabel("Full name").fill("Second");
  await page.getByLabel("Email").fill(email);
  await page.getByLabel("Password", { exact: true }).fill("Password123");
  await page.getByLabel("Confirm password").fill("Password123");
  await page.getByRole("button", { name: "Create account" }).click();
  await expect(
    page.getByText("An account with this email already exists."),
  ).toBeVisible();
});
