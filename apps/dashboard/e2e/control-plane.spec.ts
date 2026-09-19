import { test, expect, request } from "@playwright/test";

// Phase 2 control plane: thesis workspace, founder gate, board, work orders, decisions, queue — against the live API with TEST-ROS-* rows that are removed afterwards.
const API = process.env.LOGOS_API ?? "http://127.0.0.1:8765";
const tid = `TEST-ROS-E2E-${Date.now().toString(36)}`;

test.describe.serial("control plane", () => {
  let api: Awaited<ReturnType<typeof request.newContext>>;
  test.beforeAll(async ({}, info) => {
    test.skip(info.project.name !== "desktop-1440", "one viewport is enough for behaviour; layout is covered by the smoke matrix");
    api = await request.newContext({ baseURL: API, extraHTTPHeaders: { "X-Logos-Actor": "founder" } });
    const st = await (await api.get("/api/ros/status")).json();
    test.skip(st.records_only, "lab Postgres unreachable");
    expect((await api.post("/api/ros/theses", { data: { thesis_id: tid, claim_ids: ["LOGOS-AUTH-001"], title: "e2e thesis", track: "authority" } })).ok()).toBe(true);
  });
  test.afterAll(async () => { if (!api) return; await api.delete(`/api/ros/theses/${tid}`); await api.dispose(); });

  test("workspace: agent advances, founder gate locked for agent, founder passes it, events logged", async ({ page }) => {
    await page.goto(`/theses/${tid}`, { waitUntil: "load" });
    await expect(page.locator("main h1")).toContainText(tid);
    await page.getByLabel("Handelnder").selectOption("agent");
    await page.getByRole("button", { name: "triage → TRIAGE" }).click();
    await expect(page.getByRole("status")).toContainText("triage → TRIAGE");
    for (const b of ["define_question → QUESTION_DEFINED", "define_hypothesis → HYPOTHESIS_DEFINED", "define_metrics → METRICS_DEFINED", "draft_prereg → PREREG_DRAFT"]) {
      await page.getByRole("button", { name: b }).click(); await expect(page.getByRole("status")).toContainText(b.split(" → ")[0]);
    }
    const gate = page.getByRole("button", { name: "🔒 freeze_prereg → PREREG_FROZEN" });
    await expect(gate).toBeDisabled();                                   // agent may not pass a founder gate
    await page.getByLabel("Handelnder").selectOption("founder");
    await expect(gate).toBeEnabled(); await gate.click();
    await expect(page.getByRole("status")).toContainText("freeze_prereg → PREREG_FROZEN");
    await expect(page.locator("main table tbody tr")).toHaveCount(7);      // create + 6 transitions
    await page.getByPlaceholder("Notiz für den nächsten Agenten-Job …").fill("e2e note");
    await page.getByRole("button", { name: "Notiz speichern" }).click();
    await expect(page.getByText("e2e note")).toBeVisible();
  });

  test("board shows the thesis in its column; illegal drop is rejected by the API", async ({ page }) => {
    await page.goto("/board", { waitUntil: "load" });
    const card = page.locator("[data-column=PREREG_FROZEN]").getByText(tid);
    await expect(card).toBeVisible();
    const detail = await (await api.post(`/api/ros/theses/${tid}/advance`, { data: { event: "triage" } })).json();
    expect(detail.detail.reason).toBe("no such transition");
  });

  test("work orders: DRAFT via API, approve in UI, DAG renders", async ({ page }) => {
    const spec = { question: "e2e q", scope: "s", hypothesis: "h", falsification_criterion: "f", metrics: ["m"], governance: { g: 1 }, caps: { c: 1 } };
    expect((await api.post("/api/ros/work-orders", { data: { work_order_id: `${tid}-W`, thesis_id: tid, spec }, headers: { "X-Logos-Actor": "agent" } })).ok()).toBe(true);
    await page.goto("/work-orders", { waitUntil: "load" });
    await expect(page.locator("svg[aria-label='work order DAG']")).toBeVisible();
    await page.locator("main table tbody tr", { hasText: `${tid}-W` }).click();
    await page.getByRole("button", { name: "🔒 approve" }).click();
    await expect(page.getByRole("status")).toContainText("approve → APPROVED");
    const wos = await (await api.get("/api/ros/work-orders")).json();
    expect(wos.ready).toContain(`${tid}-W`);
  });

  test("decisions: approve card; queue: enqueue claude job waits for governance, stop works", async ({ page }) => {
    expect((await api.post("/api/ros/decisions", { data: { decision_id: `${tid}-D`, kind: "gate", subject_ref: tid, why: "e2e why", if_approved: "yes", if_rejected: "no" } })).ok()).toBe(true);
    await page.goto("/decisions", { waitUntil: "load" });
    const card = page.locator(`[data-decision="${tid}-D"]`);
    await card.getByRole("button", { name: "Freigeben" }).click();
    await expect(card).toContainText("APPROVED");
    await page.goto("/queue", { waitUntil: "load" });
    await page.getByLabel("kind").selectOption("thesis_advance");
    await page.getByLabel("thesis").selectOption(tid);
    await page.getByRole("button", { name: "Job einreihen" }).click();
    await expect(page.getByRole("status")).toContainText("waiting_governance");
    await page.locator("main table tbody tr", { hasText: tid }).first().click();
    await page.getByRole("button", { name: "Stopp" }).click();
    await expect(page.getByRole("status").last()).toContainText("stopped");
  });
});
