import { test, expect, request } from "@playwright/test";

// R2: control room — worker switches, master switch, thesis cards with autopilot toggles, live ticker; agent cannot flip switches.
const API = process.env.LOGOS_API ?? "http://127.0.0.1:8765";
const tid = `TEST-ROS-LS-${Date.now().toString(36)}`;

test.describe.serial("leitstand", () => {
  let api: Awaited<ReturnType<typeof request.newContext>>;
  test.beforeAll(async ({}, info) => {
    test.skip(info.project.name !== "desktop-1440", "behaviour on one viewport");
    api = await request.newContext({ baseURL: API, extraHTTPHeaders: { "X-Logos-Actor": "founder" } });
    const st = await (await api.get("/api/ros/status")).json(); test.skip(st.records_only, "lab Postgres unreachable");
    expect((await api.post("/api/ros/theses", { data: { thesis_id: tid, claim_ids: ["LOGOS-AUTH-001"], title: "Leitstand e2e", track: "authority" } })).ok()).toBe(true);
  });
  test.afterAll(async () => { if (!api) return; await api.post(`/api/ros/autopilot/theses/${tid}`, { data: { enabled: false } }); await api.delete(`/api/ros/theses/${tid}`); await api.dispose(); });

  test("switches, cards and ticker render; thesis toggle persists; agent is refused", async ({ page }) => {
    await page.goto("/", { waitUntil: "load" });
    await expect(page.locator("[data-worker=host]")).toBeVisible();
    await expect(page.locator("[data-worker=docker]")).toBeVisible();
    await expect(page.getByRole("switch", { name: "Forschung" })).toBeVisible();
    await expect(page.getByLabel("live ticker")).toBeVisible();
    const card = page.locator(`[data-thesis="${tid}"]`);
    await expect(card).toContainText("1. Idee");
    await card.getByLabel("arbeiten lassen").check();
    await expect.poll(async () => (await (await api.get("/api/ros/autopilot")).json()).theses?.[tid]?.enabled).toBe(true);
    const agent = await request.newContext({ baseURL: API, extraHTTPHeaders: { "X-Logos-Actor": "agent" } });
    expect((await agent.post("/api/ros/autopilot/master", { data: { enabled: true } })).status()).toBe(403);
    expect((await agent.post("/api/ros/workers/host/start")).status()).toBe(403);
    await agent.dispose();
  });

  test("run console explains an empty run and lists the agent feed for a synthetic run", async ({ page }) => {
    const fr = await (await api.post(`/api/ros/test/fake-run/${tid}`)).json();
    await page.goto(`/runs/${fr.run_id}`, { waitUntil: "load" });
    await expect(page.getByText("Auftrag an den Agenten", { exact: true })).toBeVisible();
    await expect(page.getByText("Was der Agent tut", { exact: true })).toBeVisible();
    await expect(page.getByLabel("agent feed").locator("li").first()).toContainText("🏁 OK");
    await page.goto("/traces", { waitUntil: "load" });
    await expect(page.getByLabel("trace statistics")).toBeVisible();
    await expect(page.getByText("Läufe je Tag", { exact: false })).toBeVisible();
  });
});
