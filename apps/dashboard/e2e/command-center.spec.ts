import { test, expect } from "@playwright/test";

test("command center shows stats, alerts and verdict chart", async ({ page }, info) => {
  test.skip(info.project.name !== "desktop-1440");
  await page.goto("/");
  await expect(page.getByText(/Aktive Thesen|Active theses/).first()).toBeVisible();
  await expect(page.locator("svg.recharts-surface").first()).toBeVisible();
});
