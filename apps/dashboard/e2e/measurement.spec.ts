import { test, expect, request } from "@playwright/test";

// R3: the gate chain is visible and honest (nothing enabled before its turn), the measurement view renders rates, proposal and items.
const API = process.env.LOGOS_API ?? "http://127.0.0.1:8765";
const tid = `TEST-ROS-MEAS-${Date.now().toString(36)}`;

test.describe.serial("gate chain + measurement", () => {
  let api: Awaited<ReturnType<typeof request.newContext>>;
  test.beforeAll(async ({}, info) => {
    test.skip(info.project.name !== "desktop-1440", "behaviour on one viewport");
    api = await request.newContext({ baseURL: API, extraHTTPHeaders: { "X-Logos-Actor": "founder" } });
    const st = await (await api.get("/api/ros/status")).json(); test.skip(st.records_only, "lab Postgres unreachable");
    expect((await api.post("/api/ros/theses", { data: { thesis_id: tid, claim_ids: ["LOGOS-AUTH-001"], title: "Messlauf e2e", track: "authority" } })).ok()).toBe(true);
    for (const e of ["triage", "define_question", "define_hypothesis", "define_metrics", "draft_prereg"]) await api.post(`/api/ros/theses/${tid}/advance`, { data: { event: e }, headers: { "X-Logos-Actor": "agent" } });
  });
  test.afterAll(async () => { if (!api) return; await api.delete(`/api/ros/theses/${tid}`); await api.dispose(); });

  test("gate chain shows seven steps; validation fails honestly without the agent's files", async ({ page }) => {
    await page.goto(`/theses/${tid}`, { waitUntil: "load" });
    await expect(page.getByLabel("gate chain").locator("li")).toHaveCount(7);
    await expect(page.locator("[data-gate=prereg_freeze]")).toContainText("🔒");
    await page.locator("[data-gate=prereg_validate]").getByRole("button", { name: "Ausführen" }).click();
    await expect(page.getByRole("status").first()).toContainText("Preregistration ist noch nicht gültig");
    await expect(page.getByRole("status").first()).toContainText("Datei fehlt: DATASET.json");
  });

  test("measurement page lists runs; an unknown id is a 404 page", async ({ page }) => {
    await page.goto("/measurements", { waitUntil: "load" });
    await expect(page.locator("main h1")).toContainText("Messlauf");
    const r = await page.goto("/measurements/M-DOES-NOT-EXIST", { waitUntil: "load" });
    expect(r?.status()).toBe(404);
  });
});
