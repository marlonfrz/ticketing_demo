import { describe, expect, it } from "vitest";

import { hasUnsavedChanges } from "./formState";

const initialForm = {
  title: "",
  description: "",
  capacity: "",
};

describe("hasUnsavedChanges", () => {
  it("returns false when the form matches its initial values", () => {
    expect(hasUnsavedChanges({ ...initialForm }, initialForm)).toBe(false);
  });

  it("tracks changes and becomes clean again when values are restored", () => {
    expect(
      hasUnsavedChanges({ ...initialForm, title: "Nuevo evento" }, initialForm)
    ).toBe(true);
    expect(hasUnsavedChanges({ ...initialForm }, initialForm)).toBe(false);
  });

  it("treats a selected file as an unsaved change", () => {
    expect(hasUnsavedChanges({ ...initialForm }, initialForm, true)).toBe(true);
  });
});
