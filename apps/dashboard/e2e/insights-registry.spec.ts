import { test, expect, request } from "@playwright/test";

// R4: observability tells the truth about every system, insights are record-based sentences, registry care refuses a bad edit and an agent.
const API = process.env.LOGOS_API ?? "http://127.0.0.1:8765";

test.describe("observability, insights, registry care", () => {
  test.beforeEach(async ({}, info) => { test.skip(info.project.name !== "desktop-1440", "behaviour on one viewport"); });

  test("observability lists eight systems with an honest state", async ({ page }) => {
    await page.goto("/observability", { waitUntil: "load" });
    await expect(page.getByLabel("systems").locator("[data-system]")).toHaveCount(8);
    await expect(page.locator("[data-system='MLflow']")).toContainText("reachable");
    await expect(page.getByText("Zugangsschlüssel bleiben im Server", { exact: false })).toBeVisible();
    const body = await page.content();
    expect(body).not.toContain("sk-lf");
  });

  test("insights show grouped, record-based sentences with their caveat", async ({ page }) => {
    await page.goto("/insights", { waitUntil: "load" });
    const auth = page.locator("[data-claim='LOGOS-AUTH-001']");
    await expect(auth).toContainText("Status VALIDATED_IN_FIXTURE");
    await expect(auth).toContainText("Widerlegen würde:");
    await expect(auth).toContainText("Vorsicht:");
    await expect(page.getByText("Status ist nicht Evidenzstärke", { exact: false }).first()).toBeVisible();
  });

  test("registry care: a bad edit is refused with reasons; agents are refused by the API", async ({ page }) => {
    await page.goto("/registry", { waitUntil: "load" });
    await page.getByText("Freies Feld ändern").click();
    await page.getByLabel("entity").fill("LOGOS-CP-002");
    await page.getByLabel("field").selectOption("status");
    await page.getByLabel("value").fill("SUPPORTED");
    await page.getByLabel("reason").fill("Begründung mit Verweis auf Messlauf M-1 und Artefakt");
    await page.getByRole("button", { name: "Prüfen" }).click();
    await expect(page.getByRole("status").first()).toContainText("Prüfung nicht bestanden");
    await expect(page.getByRole("status").first()).toContainText("verlangt mindestens Evidenzstärke MEDIUM");
    const agent = await request.newContext({ baseURL: API, extraHTTPHeaders: { "X-Logos-Actor": "agent" } });
    expect((await agent.post("/api/ros/registry/apply", { data: { registry: "claims", entity_id: "LOGOS-AUTH-001", field: "known_limitations", value: ["x"], reason: "lange genug begründet hier" } })).status()).toBe(403);
    await agent.dispose();
  });
});
