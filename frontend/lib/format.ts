import type { Driver, Metric, Stats } from "./types";

export const METRICS: { key: Metric; label: string; short: string; unit: string; scale: number; dec: number }[] = [
  { key: "vmt", label: "Vehicle miles traveled", short: "VMT", unit: "M mi / mo", scale: 1, dec: 0 },
  { key: "co2_kt", label: "CO2 emissions", short: "CO2", unit: "kt / mo", scale: 1, dec: 0 },
  { key: "fuel_spend", label: "Motor fuel spending", short: "FUEL $", unit: "M USD / mo", scale: 1, dec: 0 },
  { key: "fuel_gallons", label: "Fuel use", short: "GAL", unit: "M gal / mo", scale: 1, dec: 0 },
  { key: "energy_burden_mean", label: "Energy burden, mean household", short: "BURDEN", unit: "% of income", scale: 100, dec: 2 },
  { key: "energy_burden_low_income", label: "Energy burden, low-income", short: "BURDEN LI", unit: "% of income", scale: 100, dec: 2 },
];
export const metricInfo = (m: Metric) => METRICS.find((x) => x.key === m)!;

export const DRIVERS: { key: Driver; label: string; op: "multiply" | "add"; unit: string; min: number; max: number; step: number; def: number }[] = [
  { key: "gasoline_price", label: "Gasoline price", op: "multiply", unit: "% change", min: -90, max: 900, step: 1, def: 20 },
  { key: "electricity_price", label: "Electricity price", op: "multiply", unit: "% change", min: -90, max: 900, step: 1, def: 15 },
  { key: "real_income", label: "Real disposable income", op: "multiply", unit: "% change", min: -90, max: 900, step: 1, def: -5 },
  { key: "unemployment", label: "Unemployment rate", op: "add", unit: "points", min: -50, max: 50, step: 0.1, def: 2 },
];

/** UI magnitude (percent change or points) to the backend intervention value. */
export function toValue(op: "multiply" | "add", magnitude: number): number {
  return op === "multiply" ? Math.round((1 + magnitude / 100) * 1e6) / 1e6 : magnitude;
}
export function describeIntervention(i: { variable: string; operation: string; value: number; start_month: number; duration_months: number }) {
  const d = DRIVERS.find((x) => x.key === i.variable)?.label ?? i.variable;
  const mag = i.operation === "multiply" ? `${fmtSigned((i.value - 1) * 100, 1)}%` : `${fmtSigned(i.value, 1)} pt`;
  return `${d} ${mag}, month ${i.start_month} for ${i.duration_months} mo`;
}

export function fmt(x: number | null | undefined, dec = 0): string {
  if (x === null || x === undefined || !Number.isFinite(x)) return "DATA UNAVAILABLE";
  return x.toLocaleString("en-US", { minimumFractionDigits: dec, maximumFractionDigits: dec });
}
export function fmtSigned(x: number | null | undefined, dec = 2): string {
  if (x === null || x === undefined || !Number.isFinite(x)) return "DATA UNAVAILABLE";
  const s = fmt(Math.abs(x), dec);
  return x > 0 ? `+${s}` : x < 0 ? `-${s}` : s;
}
export const level = (s: Stats | undefined, m: Metric) => (s ? s.median * metricInfo(m).scale : null);

export function fmtTime(iso: string): string {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "DATA UNAVAILABLE";
  return d.toLocaleTimeString("en-GB", { hour12: false }) + "." + String(d.getMilliseconds()).padStart(3, "0");
}

export const TIER_TEXT: Record<string, string> = {
  HIGH: "Inputs inside the training data distribution.",
  MEDIUM: "Some months near the edge of the training data.",
  LOW: "Partial extrapolation: some inputs beyond training data. Treat with caution.",
  OOD: "Out of distribution: results are pure extrapolation. Runs only when labelled exploratory.",
  UNKNOWN: "Reality Guard result unavailable.",
};
