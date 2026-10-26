"use client";
import { useState } from "react";
import { api } from "@/lib/api";
import { fmt, fmtSigned, metricInfo } from "@/lib/format";
import type { ArenaRecord, Metric, Scenario } from "@/lib/types";
import { tierClass } from "./Results";

const OBJ: Metric[] = ["co2_kt", "energy_burden_low_income", "energy_burden_mean", "vmt", "fuel_spend"];
const DEFAULT: Record<string, number> = { co2_kt: 0.5, energy_burden_low_income: 0.5, energy_burden_mean: 0, vmt: 0, fuel_spend: 0 };

/** Policy Arena. Weights are user-visible and sent as-is; ranking and Pareto labels come from the backend. */
export function Arena({ candidates, onDone }: { candidates: Scenario[]; onDone: (r: ArenaRecord) => void }) {
  const [w, setW] = useState(DEFAULT);
  const [res, setRes] = useState<ArenaRecord | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [expl, setExpl] = useState(false);
  const sum = Object.values(w).reduce((a, b) => a + b, 0);
  const run = async () => {
    setBusy(true); setErr(null);
    try {
      const weights = Object.fromEntries(Object.entries(w).filter(([, v]) => v > 0));
      const r = await api.arena({ candidates: candidates.slice(0, 6), weights, horizon_months: 24, n_paths: 300, seed: 42, include_exploratory: expl });
      setRes(r); onDone(r);
    } catch (e) { setErr((e as Error).message); } finally { setBusy(false); }
  };
  return (
    <div className="grid" style={{ gap: 12 }} data-testid="arena">
      <p className="muted" style={{ fontSize: "var(--fs-s)", margin: 0 }}>
        Ranks {candidates.length} candidate scenario(s) on lower-is-better objectives. Score = weighted sum of min-max normalized median changes.
        The AI never sets weights or ranks.
      </p>
      {candidates.length < 2 && <div className="empty">ADD AT LEAST 2 SCENARIOS (RUN THEM FROM THE COMMAND BOX OR BUILDER)</div>}
      <fieldset style={{ border: 0, padding: 0, margin: 0, display: "grid", gap: 8, gridTemplateColumns: "repeat(auto-fill, minmax(200px, 1fr))" }}>
        <legend className="label" style={{ marginBottom: 6 }}>Weights (normalized on the server, sum now {fmt(sum, 2)})</legend>
        {OBJ.map((k) => (
          <label key={k} className="field"><span>{metricInfo(k).short}: {fmt(w[k], 2)}</span>
            <input type="range" min={0} max={1} step={0.05} value={w[k]} onChange={(e) => setW({ ...w, [k]: Number(e.target.value) })}
              aria-valuetext={`${fmt(w[k], 2)}`} /></label>
        ))}
      </fieldset>
      <div className="row">
        <label className="row" style={{ gap: 6, fontSize: "var(--fs-s)" }}><input type="checkbox" checked={expl} onChange={(e) => setExpl(e.target.checked)} style={{ width: "auto" }} /> Include OOD (exploratory)</label>
        <button className="btn small" type="button" onClick={() => setW(DEFAULT)}>Reset to default</button>
        <button className="btn primary" type="button" onClick={run} disabled={busy || candidates.length < 2 || sum <= 0} data-testid="arena-run">{busy ? "Ranking" : "Rank scenarios"}</button>
      </div>
      {err && <p className="alert error">{err}</p>}
      {res && (
        <div style={{ overflowX: "auto" }}>
          <p className="mono muted" style={{ fontSize: "var(--fs-xs)" }}>run {res.run_id} / weights {res.weights.source} / {res.scoring}</p>
          <table>
            <thead><tr><th>Rank</th><th>Candidate</th><th className="num">Score</th><th>Pareto</th><th>Tier</th>
              {Object.keys(res.weights.normalized).map((k) => <th key={k} className="num">{metricInfo(k as Metric).short} change P50 [P10 to P90]</th>)}</tr></thead>
            <tbody>{res.ranking.map((r) => (
              <tr key={r.candidate}>
                <td className="mono">{r.rank}</td><td>{r.candidate}{r.exploratory ? " (exploratory)" : ""}</td>
                <td className="num mono">{fmt(r.score, 3)}</td>
                <td><span className={`tag ${r.pareto === "non-dominated" ? "ok" : ""}`}>{r.pareto}</span>
                  {r.dominated_by.length > 0 && <span className="muted" style={{ fontSize: "var(--fs-xs)" }}> by {r.dominated_by.join(", ")}</span>}</td>
                <td><span className={`tag ${tierClass(r.tier)}`}>{r.tier}</span></td>
                {Object.keys(res.weights.normalized).map((k) => (
                  <td key={k} className="num mono">{fmtSigned(r.median_pct_delta[k])}% [{fmtSigned(r.p10_p90_pct_delta[k]?.[0])} to {fmtSigned(r.p10_p90_pct_delta[k]?.[1])}]</td>
                ))}
              </tr>
            ))}</tbody>
          </table>
          {res.excluded_ood.length > 0 && <p className="alert" style={{ marginTop: 8 }}>Excluded as OOD: {res.excluded_ood.join(", ")}</p>}
          <p className="muted" style={{ fontSize: "var(--fs-xs)", marginTop: 8 }}>{res.note}</p>
        </div>
      )}
    </div>
  );
}
