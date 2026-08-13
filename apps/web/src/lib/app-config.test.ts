import { describe, expect, it } from "vitest";
import { APP_DESCRIPTION, APP_NAME } from "@/lib/app-config";

describe("app identity", () => {
  it("ships the canonical app name and description", () => {
    expect(APP_NAME).toBe("4D Gaussian Splatting Volumetric Capture");
    expect(APP_DESCRIPTION).toBe(
      "Capture-to-B2 pipeline that turns synchronized multi-camera video into a trained 4D Gaussian Splatting volumetric scene on Backblaze B2"
    );
  });
});
