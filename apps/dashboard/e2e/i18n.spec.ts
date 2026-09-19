import { test, expect } from "@playwright/test";

test("German is default, EN switch persists", async ({ page }, info) => {
  test.skip(info.project.name !== "desktop-1440");
  await page.goto("/");
  await expect(page.locator("aside").getByText("Kommandozentrale")).toBeVisible();
  await page.getByRole("button", { name: "EN" }).click();
  await expect(page.locator("aside").getByText("Command Center")).toBeVisible();
  await page.goto("/claims");
  await expect(page.locator("main h1")).toHaveText(/Claim registry/);
  await page.getByRole("button", { name: "DE" }).click();
  await expect(page.locator("main h1")).toHaveText(/Claim-Register/);
});
