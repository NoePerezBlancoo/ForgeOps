import { describe, expect, it } from "vitest";

import { formatDate, initials, labelFor } from "./format";

describe("presentation helpers", () => {
  it("translates production plan and status labels", () => {
    expect(labelFor("INDUSTRIAL")).toBe("Industrial");
    expect(labelFor("SUSPENDED")).toBe("Suspendida");
    expect(labelFor("CUSTOM")).toBe("CUSTOM");
  });

  it("creates stable two-word initials", () => {
    expect(initials("Noe Perez Blanco")).toBe("NP");
  });

  it("uses the empty date fallback", () => {
    expect(formatDate(null)).toBe("Sin fecha");
  });
});
