import { expect, test } from "@playwright/test";

test("loads the triage workspace and fills the demo sample", async ({ page }) => {
  await page.goto("/");

  await expect(page.getByRole("heading", { name: "Clinical intake" })).toBeVisible();
  await expect(page.getByText("Online Gemma 4")).toBeVisible();
  await expect(page.getByText("Offline local")).toBeVisible();
  await expect(page.getByText("Clinical decision support only.")).toBeVisible();

  await page.getByRole("button", { name: "Sample" }).click();
  await expect(page.getByLabel("Transcript or symptom description")).toHaveValue(
    /18-month-old child has cough/,
  );
});
