import { describe, expect, it } from "vitest";
import { describeIntervention, fmt, fmtSigned, toValue } from "../lib/format";

describe("format", () => {
  it("maps UI magnitudes to backend values", () => {
    expect(toValue("multiply", 20)).toBe(1.2);
    expect(toValue("multiply", -5)).toBe(0.95);
    expect(toValue("add", 2)).toBe(2);
  });
  it("shows DATA UNAVAILABLE instead of inventing numbers", () => {
    expect(fmt(undefined)).toBe("DATA UNAVAILABLE");
    expect(fmt(NaN)).toBe("DATA UNAVAILABLE");
    expect(fmtSigned(null)).toBe("DATA UNAVAILABLE");
  });
  it("signs values and never emits an em dash", () => {
    expect(fmtSigned(1.234)).toBe("+1.23");
    expect(fmtSigned(-0.5, 1)).toBe("-0.5");
    const d = describeIntervention({ variable: "gasoline_price", operation: "multiply", value: 1.2, start_month: 0, duration_months: 12 });
    expect(d).toBe("Gasoline price +20.0%, month 0 for 12 mo");
    expect(d).not.toContain("\u2014");
  });
});
