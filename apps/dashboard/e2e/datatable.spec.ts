import { test, expect } from "@playwright/test";

test("experiments table: search, inspector, short hash", async ({ page }, info) => {
  test.skip(!info.project.name.startsWith("desktop"));
  await page.goto("/experiments");
  await page.getByPlaceholder(/Suchen|Search/).fill("CPA-RERUN");
  await expect(page.getByRole("row")).toHaveCount(2);                                       // header + 1
  await expect(page.getByText(/^99525f856a/)).toBeVisible();                                 // short hash
  await page.getByRole("row").nth(1).click();
  await expect(page.getByRole("complementary").getByText("99525f856ae0653c99e97804bba1b7d00abf7565c3439b63e9a0fd5ed051786e")).toBeVisible();
});
