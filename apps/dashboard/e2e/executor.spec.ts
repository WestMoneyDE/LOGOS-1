import { test, expect, request } from "@playwright/test";

// Phase 3: agent-job enqueue + founder gate preview + run console (synthetic run via the TEST-ROS-only hook; no Claude invocation).
const API = process.env.LOGOS_API ?? "http://127.0.0.1:8765";
const tid = `TEST-ROS-EXEC-${Date.now().toString(36)}`;

test.describe.serial("executor surface", () => {
  let api: Awaited<ReturnType<typeof request.newContext>>;
  test.beforeAll(async ({}, info) => {
    test.skip(info.project.name !== "desktop-1440", "behaviour on one viewport; layout is covered by the smoke matrix");
    api = await request.newContext({ baseURL: API, extraHTTPHeaders: { "X-Logos-Actor": "founder" } });
    const st = await (await api.get("/api/ros/status")).json(); test.skip(st.records_only, "lab Postgres unreachable");
    expect((await api.post("/api/ros/theses", { data: { thesis_id: tid, claim_ids: ["LOGOS-AUTH-001"], title: "exec e2e", track: "authority" } })).ok()).toBe(true);
  });
  test.afterAll(async () => { if (!api) return; await api.delete(`/api/ros/theses/${tid}`); await api.dispose(); });

  test("thesis workspace: enqueue agent job, gate preview lists checks, stop", async ({ page }) => {
    await page.goto(`/theses/${tid}`, { waitUntil: "load" });
    await page.getByRole("button", { name: "Agenten-Job einreihen" }).click();
    await expect(page.getByRole("status")).toContainText("waiting_governance");
    await page.getByRole("button", { name: "Gate prüfen" }).click();
    await expect(page.getByText("thesis_below_agent_ceiling")).toBeVisible();
    await expect(page.getByText("auth_evidence_fresh")).toBeVisible();
    await page.getByRole("button", { name: "Stopp" }).click();
    await expect(page.getByRole("status")).toContainText("stopped");
  });

  test("run console renders a finished synthetic run with its event stream", async ({ page }) => {
    const fr = await (await api.post(`/api/ros/test/fake-run/${tid}`)).json();
    await page.goto(`/runs/${fr.run_id}`, { waitUntil: "load" });
    await expect(page.locator("main h1")).toContainText(fr.run_id);
    await expect(page.getByLabel("run events").locator("li")).toHaveCount(5);
    await expect(page.getByText("claude-opus-5", { exact: false }).first()).toBeVisible();
    await expect(page.getByText("beendet · done")).toBeVisible();
    await page.goto("/runs", { waitUntil: "load" });
    await expect(page.locator("main table tbody tr", { hasText: fr.run_id })).toBeVisible();
  });

  test("system/claude shows evidence table and governed caps; cap is not editable", async ({ page }) => {
    await page.goto("/system/claude", { waitUntil: "load" });
    await expect(page.getByText("max_parallel_claude_sessions")).toBeVisible();
    await expect(page.getByText("founder amendment order", { exact: false }).first()).toBeVisible();
    const r = await api.post("/api/ros/governor/settings", { data: { key: "max_parallel_claude_sessions", value: 2 } });
    expect(r.status()).toBe(403);
  });
});
