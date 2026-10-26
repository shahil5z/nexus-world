"use client";
import Link from "next/link";
import { useEffect, useState } from "react";
import { api, ApiError } from "@/lib/api";
import { describeIntervention, metricInfo, METRICS } from "@/lib/format";
import { localRecord, RUN_ID_RE } from "@/lib/history";
import type { AnalyzeRecord, ArenaRecord, Metric, MonteCarloResponse } from "@/lib/types";
import { FanChart } from "./FanChart";
import { Analysis, Critic, Evidence, GuardPanel, MetricCards, Panel, Trace } from "./Results";

type State = { rec?: AnalyzeRecord | ArenaRecord; from?: "server" | "browser"; missing?: boolean; invalid?: boolean };

/** Shareable run view: server run store first, then this browser's copy, otherwise an explicit not-available state. */
export function RunView({ id }: { id: string }) {
  const [s, setS] = useState<State | null>(null);
  const [mc, setMc] = useState<MonteCarloResponse | null>(null);
  const [metric, setMetric] = useState<Metric>("vmt");
  const badId = !RUN_ID_RE.test(id);
  useEffect(() => {
    if (badId) return;
    api.run(id).then((rec) => setS({ rec, from: "server" })).catch((e) => {
      const loc = localRecord(id);
      if (loc) setS({ rec: loc, from: "browser" });
      else setS({ missing: true, invalid: e instanceof ApiError && e.status === 400 });
    });
  }, [id, badId]);
  const rec = s?.rec;
  useEffect(() => {
    if (rec?.kind === "analyze" && rec.scenario && rec.horizon_months && rec.status === "ok")
      api.monteCarlo(rec.scenario, rec.horizon_months, rec.n_paths, rec.seed).then(setMc).catch(() => setMc(null));
  }, [rec]);
  if (badId) return <div className="empty">INVALID RUN ID</div>;
  if (!s) return <p className="unavailable"><span className="spinner" aria-hidden /> LOADING RUN {id}</p>;
  if (s.invalid) return <div className="empty">INVALID RUN ID</div>;
  if (s.missing || !rec) return (
    <div className="panel"><div className="panel-b">
      <h1 className="mono" style={{ fontSize: "var(--fs-l)" }}>RUN NOT AVAILABLE ON THIS INSTANCE</h1>
      <p className="muted" style={{ marginTop: 8 }}>Run {id} is not in this server&apos;s in-memory run store and not saved in this browser. Runs are not persisted across server instances in demo mode.</p>
      <Link href="/console" className="btn primary">Open console</Link>
    </div></div>
  );
  const src = <span className="tag">{s.from === "server" ? "loaded from server run store" : "loaded from this browser (server copy expired)"}</span>;
  if (rec.kind === "policy_arena") return (
    <Panel title={`Policy arena ${rec.run_id}`} right={src}>
      <table><thead><tr><th>Rank</th><th>Candidate</th><th className="num">Score</th><th>Pareto</th></tr></thead>
        <tbody>{rec.ranking.map((r) => <tr key={r.candidate}><td>{r.rank}</td><td>{r.candidate}</td><td className="num mono">{r.score.toFixed(3)}</td><td>{r.pareto}</td></tr>)}</tbody></table>
      <p className="muted" style={{ marginTop: 8, fontSize: "var(--fs-xs)" }}>{rec.scoring}</p>
    </Panel>
  );
  const mi = metricInfo(metric);
  const name = rec.scenario?.name ?? "";
  return (
    <div className="grid">
      <div className="row"><h1 className="mono" style={{ fontSize: "var(--fs-l)" }}>RUN {rec.run_id}</h1>{src}
        <span className="tag">{rec.mode === "agentic" ? `AI agents / ${rec.model}` : "ENGINE-ONLY (AI unavailable)"}</span>
        <span className="tag">{rec.created_utc}</span></div>
      {rec.scenario && <Panel title="Scenario">
        <ul style={{ margin: "0 0 10px", paddingLeft: 18 }}>{rec.scenario.interventions.map((i, k) => <li key={k}>{describeIntervention(i)}</li>)}</ul>
        <GuardPanel guard={rec.guard} /></Panel>}
      {rec.outputs?.summary && name && <MetricCards summary={mc?.summary ?? rec.outputs.summary} name={name} active={metric} onSelect={setMetric} />}
      {mc && name && <Panel title={`${mi.label} (${mi.unit})`}><FanChart months={mc.months} baseline={mc.bands[metric]?.baseline} scenario={mc.bands[metric]?.[name]}
        scenarioName={name} label={mi.label} unit={mi.unit} scale={mi.scale} dec={mi.dec} /></Panel>}
      {!rec.outputs?.summary && <p className="unavailable">{METRICS.length} METRICS: DATA UNAVAILABLE ({rec.status})</p>}
      <Panel title="Analysis"><Analysis r={rec} /></Panel>
      <Panel title="Evidence"><Evidence r={rec} /></Panel>
      <Panel title="Critic"><Critic r={rec} /></Panel>
      <Panel title="Agent trace"><Trace events={rec.trace} metrics={rec.metrics} /></Panel>
      <p className="muted mono" style={{ fontSize: "var(--fs-xs)" }}>{Object.entries(rec.versions ?? {}).map(([k, v]) => `${k} ${v}`).join(" / ")}</p>
    </div>
  );
}
