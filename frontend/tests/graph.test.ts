import { describe, expect, it } from "vitest";
import g from "../lib/generated/causal_graph.json";
import { layout } from "../lib/graph";
import type { CausalGraph } from "../lib/types";

describe("causal graph", () => {
  it("lays out every node from the knowledge file and keeps drivers left of outcomes", () => {
    const n = layout(g as unknown as CausalGraph, 900, 400);
    expect(n).toHaveLength((g as unknown as CausalGraph).nodes.length);
    const x = Object.fromEntries(n.map((v) => [v.id, v.x]));
    expect(x.gasoline_price).toBeLessThan(x.co2_kt);
    expect(n.every((v) => v.x >= 0 && v.x <= 900 && v.y >= 0 && v.y <= 400)).toBe(true);
  });
});
