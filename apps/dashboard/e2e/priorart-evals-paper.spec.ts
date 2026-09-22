import { test, expect, request } from "@playwright/test";

// R5: the literature matrix is honest about gaps, agent quality is measured deterministically, the paper draft cites records and leaves gaps open.
const API = process.env.LOGOS_API ?? "http://127.0.0.1:8765";

test.describe("prior art, evals, paper", () => {
  test.beforeEach(async ({}, info) => { test.skip(info.project.name !== "desktop-1440", "behaviour on one viewport"); });

  test("literature matrix shows six tracks with their gaps", async ({ page }) => {
    await page.goto("/prior-art/matrix", { waitUntil: "load" });
    await expect(page.getByLabel("prior art matrix").locator("[data-track]")).toHaveCount(6);
    const auth = page.locator("[data-track=authority]");
    await expect(auth).toContainText("2 Quellen");
    await expect(auth).toContainText("weitere Quelle(n)");
    await expect(page.getByText("Neuheit ist damit nicht belegt", { exact: false }).first()).toBeVisible();
  });

  test("agent quality page states NO_DATA honestly and lists the check profiles", async ({ page }) => {
    await page.goto("/evals", { waitUntil: "load" });
    await expect(page.getByText("kein Modell bewertet ein Modell", { exact: false }).first()).toBeVisible();
    await expect(page.getByText("TRIAGE", { exact: false }).first()).toBeVisible();
  });

  test("paper draft is generated from records, keeps TO_BE_WRITTEN and does not change maturity", async ({ page }) => {
    await page.goto("/publications/PAPER-2/draft", { waitUntil: "load" });
    const md = page.getByLabel("paper draft");
    await expect(md).toContainText("TO_BE_WRITTEN");
    await expect(md).toContainText("Was dieses Papier nicht behauptet");
    await expect(md).toContainText("Reifegrad im Register: **INTERNAL_DRAFT**");
    const api = await request.newContext({ baseURL: API });
    const before = await (await api.get("/api/registries/publications")).json();
    const status = before.papers.find((p: any) => p.paper_id === "PAPER-2").manuscript_status;
    expect(status).toBe("INTERNAL_DRAFT");
    await api.dispose();
  });
});
