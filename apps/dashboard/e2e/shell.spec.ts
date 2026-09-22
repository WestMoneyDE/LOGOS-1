import { test, expect } from "@playwright/test";

test("mobile: sidebar is a sheet, no overflow", async ({ page }, info) => {
  test.skip(info.project.name !== "mobile-390");
  await page.goto("/claims");
  await expect(page.locator("aside")).toBeHidden();
  await page.getByRole("button", { name: "Navigation" }).click();
  await expect(page.getByRole("dialog").getByText("Claims", { exact: true })).toBeVisible();
});

test("desktop: sidebar collapses and main uses full width", async ({ page }, info) => {
  test.skip(!info.project.name.startsWith("desktop"));
  await page.goto("/claims");
  const before = await page.locator("main").boundingBox();
  await page.getByRole("button", { name: /Einklappen|Collapse/ }).click();
  const after = await page.locator("main").boundingBox();
  expect(after!.width).toBeGreaterThan(before!.width + 100);
});
