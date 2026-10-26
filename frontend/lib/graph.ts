import type { CausalGraph } from "./types";

export interface LaidOutNode { id: string; x: number; y: number; layer: number; kind: "driver" | "state" | "outcome" }

// Preferred columns for known variables (left to right: exogenous drivers to household outcomes).
const COLUMN: Record<string, number> = { cpi: 0, gasoline_price: 1, electricity_price: 1, real_income: 1, unemployment: 1,
  vmt: 2, fuel_gallons: 3, co2_kt: 4, fuel_spend: 4, energy_burden_mean: 5, energy_burden_low_income: 6 };
const DRIVERS = new Set(["cpi", "gasoline_price", "electricity_price", "real_income", "unemployment"]);

/** Column layout. Nodes and edges come from the knowledge file; unknown nodes fall back to longest-path layering. */
export function layout(g: CausalGraph, width: number, height: number): LaidOutNode[] {
  const edges = g.edges.filter((e) => e.from !== e.to);
  const layer: Record<string, number> = Object.fromEntries(g.nodes.map((n) => [n, COLUMN[n] ?? 0]));
  for (let i = 0; i < g.nodes.length; i++)
    for (const e of edges) if (!(e.to in COLUMN)) layer[e.to] = Math.max(layer[e.to], layer[e.from] + 1);
  const maxL = Math.max(1, ...Object.values(layer));
  const cols: Record<number, string[]> = {};
  for (const n of g.nodes) (cols[layer[n]] ??= []).push(n);
  const padX = 52, padY = 30;
  const out: LaidOutNode[] = [];
  for (const [l, ns] of Object.entries(cols)) {
    ns.forEach((n, i) => {
      const L = Number(l);
      out.push({ id: n, layer: L, x: padX + (L / maxL) * (width - 2 * padX),
        y: padY + ((i + 0.5) / ns.length) * (height - 2 * padY),
        kind: DRIVERS.has(n) ? "driver" : edges.some((e) => e.from === n) ? "state" : "outcome" });
    });
  }
  return out;
}

export const NODE_LABEL: Record<string, string> = {
  gasoline_price: "GASOLINE $", electricity_price: "ELECTRICITY $", real_income: "REAL INCOME", unemployment: "UNEMPLOYMENT",
  cpi: "CPI", vmt: "VMT", fuel_gallons: "FUEL GAL", co2_kt: "CO2", fuel_spend: "FUEL SPEND",
  energy_burden_mean: "BURDEN MEAN", energy_burden_low_income: "BURDEN LOW-INC",
};
