import { test, expect } from "@playwright/test";

test("German is default, EN switch persists", async ({ page }, info) => {
  test.skip(info.project.name !== "desktop-1440");
  await page.goto("/");
  await expect(page.locator("aside").first().getByText("Leitstand", { exact: true })).toBeVisible();
  await page.locator("aside").first().getByRole("button", { name: "EN", exact: true }).click();
  await expect(page.locator("aside").first().getByText("Control room", { exact: true })).toBeVisible();
  await page.goto("/claims");
  await expect(page.locator("main h1")).toHaveText(/Claim registry/);
  await page.locator("aside").first().getByRole("button", { name: "DE", exact: true }).click();
  await expect(page.locator("main h1")).toHaveText(/Claim-Register/);
});
