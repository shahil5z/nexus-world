"use client";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { fmt } from "@/lib/format";

type Eval = { holdout_metrics?: { test?: Record<string, { mae: number; n: number }> };
  backtests?: Record<string, { engine_mape_pct: number; seasonal_naive_mape_pct: number; engine_beats_naive: boolean }>;
  tensorflow?: { selected: boolean; val_mae: number; best_other_val_mae: number } };

/** Live numbers from /api/model/evaluate. Shows DATA UNAVAILABLE rather than placeholder figures. */
export function ModelEvidence() {
  const [d, setD] = useState<Eval | null>(null);
  const [err, setErr] = useState(false);
  useEffect(() => { api.modelEvaluate().then((x) => setD(x as Eval)).catch(() => setErr(true)); }, []);
  if (err) return <p className="unavailable">MODEL EVALUATION: DATA UNAVAILABLE (backend unreachable)</p>;
  if (!d) return <p className="unavailable"><span className="spinner" aria-hidden /> LOADING MODEL EVALUATION</p>;
  const bt = Object.entries(d.backtests ?? {});
  return (
    <div className="grid" style={{ gridTemplateColumns: "repeat(auto-fit, minmax(300px, 1fr))" }}>
      <div className="panel">
        <div className="panel-h"><h3>Historical backtests</h3><span className="label">MAPE on VMT</span></div>
        <table>
          <thead><tr><th>Window</th><th className="num">Engine</th><th className="num">Seasonal naive</th><th>Beats naive</th></tr></thead>
          <tbody>
            {bt.length === 0 && <tr><td colSpan={4} className="unavailable">DATA UNAVAILABLE</td></tr>}
            {bt.map(([k, v]) => (
              <tr key={k}><td className="mono">{k}</td><td className="num">{fmt(v.engine_mape_pct, 2)}%</td>
                <td className="num">{fmt(v.seasonal_naive_mape_pct, 2)}%</td>
                <td><span className={`tag ${v.engine_beats_naive ? "ok" : "caution"}`}>{v.engine_beats_naive ? "yes" : "no"}</span></td></tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="panel">
        <div className="panel-h"><h3>TensorFlow ensemble</h3><span className="label">evaluated</span></div>
        <div className="panel-b">
          {d.tensorflow ? (
            <dl className="kv">
              <dt>Selected</dt><dd>{d.tensorflow.selected ? "yes" : "no, not used at runtime"}</dd>
              <dt>Val MAE</dt><dd>{fmt(d.tensorflow.val_mae, 5)}</dd>
              <dt>Best other</dt><dd>{fmt(d.tensorflow.best_other_val_mae, 5)}</dd>
            </dl>
          ) : <p className="unavailable">DATA UNAVAILABLE</p>}
          <p className="muted" style={{ marginTop: 10, fontSize: "var(--fs-s)" }}>
            The ensemble did not beat the persistence baseline on validation, so the runtime uses a Ridge transition model.
          </p>
        </div>
      </div>
    </div>
  );
}
