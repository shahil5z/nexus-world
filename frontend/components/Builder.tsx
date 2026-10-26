"use client";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { DRIVERS, toValue } from "@/lib/format";
import type { Driver, Scenario, ValidateResponse } from "@/lib/types";
import { GuardPanel } from "./Results";

export interface BuilderRow { variable: Driver; magnitude: number; start: number; duration: number }

export function buildScenario(name: string, rows: BuilderRow[]): Scenario {
  return { name, interventions: rows.map((r) => {
    const d = DRIVERS.find((x) => x.key === r.variable)!;
    return { variable: r.variable, operation: d.op, value: toValue(d.op, r.magnitude), start_month: r.start, duration_months: r.duration };
  }) };
}

/** Scenario builder within the backend limits; Reality Guard pre-check via /api/simulation/validate. */
export function Builder({ onRun, busy }: { onRun: (s: Scenario, horizon: number, nPaths: number) => void; busy: boolean }) {
  const [name, setName] = useState("Custom 1");
  const [horizon, setHorizon] = useState(24);
  const [nPaths, setNPaths] = useState(300);
  const [rows, setRows] = useState<BuilderRow[]>([{ variable: "gasoline_price", magnitude: 20, start: 0, duration: 12 }]);
  const [check, setCheck] = useState<{ v?: ValidateResponse; err?: string; pending: boolean }>({ pending: false });
  const nameOk = /^[A-Za-z0-9 _\-.+%]{1,60}$/.test(name);
  const rowsOk = rows.every((r) => Number.isFinite(r.magnitude) && r.start + 1 <= horizon && (DRIVERS.find((d) => d.key === r.variable)!.op === "add" || r.magnitude > -100));
  const dup = new Set(rows.map((r) => `${r.variable}:${r.start}`)).size !== rows.length;
  useEffect(() => {
    if (!nameOk || !rowsOk || dup || rows.length === 0) return;
    const t = setTimeout(() => {
      setCheck({ pending: true });
      api.validate(buildScenario(name, rows), horizon).then((v) => setCheck({ v, pending: false }))
        .catch((e) => setCheck({ err: (e as Error).message, pending: false }));
    }, 400);
    return () => clearTimeout(t);
  }, [name, rows, horizon, nameOk, rowsOk, dup]);
  const set = (i: number, p: Partial<BuilderRow>) => setRows((rs) => rs.map((r, k) => (k === i ? { ...r, ...p } : r)));
  const ood = check.v?.reality_guard.tier === "OOD";
  return (
    <form className="grid" style={{ gap: 12 }} onSubmit={(e) => { e.preventDefault(); onRun(buildScenario(name, rows), horizon, nPaths); }} aria-label="Scenario builder">
      <label className="field"><span>Scenario name</span>
        <input value={name} onChange={(e) => setName(e.target.value)} maxLength={60} aria-invalid={!nameOk} /></label>
      {!nameOk && <p className="alert error">Use letters, digits, space and _ - . + % only.</p>}
      {rows.map((r, i) => {
        const d = DRIVERS.find((x) => x.key === r.variable)!;
        return (
          <fieldset key={i} className="panel" style={{ padding: 10, display: "grid", gap: 8, margin: 0 }}>
            <legend className="label" style={{ padding: "0 4px" }}>Intervention {i + 1}</legend>
            <label className="field"><span>Driver</span>
              <select value={r.variable} onChange={(e) => { const nd = DRIVERS.find((x) => x.key === e.target.value)!; set(i, { variable: nd.key, magnitude: nd.def }); }}>
                {DRIVERS.map((x) => <option key={x.key} value={x.key}>{x.label}</option>)}
              </select></label>
            <label className="field"><span>Change ({d.unit})</span>
              <input type="number" value={r.magnitude} min={d.min} max={d.max} step={d.step} onChange={(e) => set(i, { magnitude: Number(e.target.value) })} /></label>
            <div className="row" style={{ flexWrap: "nowrap" }}>
              <label className="field" style={{ flex: 1 }}><span>Start month</span>
                <input type="number" min={0} max={horizon - 1} value={r.start} onChange={(e) => set(i, { start: Number(e.target.value) })} /></label>
              <label className="field" style={{ flex: 1 }}><span>Duration (mo)</span>
                <input type="number" min={1} max={36} value={r.duration} onChange={(e) => set(i, { duration: Number(e.target.value) })} /></label>
            </div>
            {rows.length > 1 && <button type="button" className="btn small" onClick={() => setRows((rs) => rs.filter((_, k) => k !== i))}>Remove</button>}
          </fieldset>
        );
      })}
      {dup && <p className="alert error">Two interventions on the same driver and start month.</p>}
      {rows.length < 4 && <button type="button" className="btn small" onClick={() => setRows((rs) => [...rs, { variable: "electricity_price", magnitude: 15, start: 0, duration: 12 }])}>Add intervention</button>}
      <div className="row" style={{ flexWrap: "nowrap" }}>
        <label className="field" style={{ flex: 1 }}><span>Horizon (mo, max 36)</span>
          <input type="number" min={1} max={36} value={horizon} onChange={(e) => setHorizon(Math.max(1, Math.min(36, Number(e.target.value))))} /></label>
        <label className="field" style={{ flex: 1 }}><span>Paths (10 to 1000)</span>
          <input type="number" min={10} max={1000} step={10} value={nPaths} onChange={(e) => setNPaths(Math.max(10, Math.min(1000, Number(e.target.value))))} /></label>
      </div>
      <div>
        <p className="label" style={{ marginBottom: 6 }}>Reality Guard pre-check</p>
        {check.err ? <p className="alert error">{check.err}</p> : <GuardPanel guard={check.v?.reality_guard} pending={check.pending} />}
      </div>
      {ood && <p className="alert">OOD scenario: this run is exploratory. Results are extrapolation outside the training data.</p>}
      <button className="btn primary" type="submit" disabled={busy || !nameOk || !rowsOk || dup} data-testid="builder-run">
        {busy ? "Running" : ood ? "Run exploratory engine simulation" : "Run engine simulation"}</button>
      <p className="muted" style={{ fontSize: "var(--fs-xs)", margin: 0 }}>Builder runs call the engine directly (/simulation/monte-carlo). Use the command box for AI analysis.</p>
    </form>
  );
}
