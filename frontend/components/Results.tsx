"use client";
import type { AnalyzeRecord, EvidenceItem, GuardResult, Metric, Summary, TraceEvent } from "@/lib/types";
import { fmt, fmtSigned, fmtTime, METRICS, TIER_TEXT } from "@/lib/format";
import { STAGES, stageStates } from "@/lib/stages";

export function tierClass(t?: string) {
  return t === "HIGH" ? "ok" : t === "MEDIUM" ? "accent" : t === "LOW" ? "caution" : t === "OOD" ? "block" : "";
}

export function Panel({ title, right, children, id }: { title: string; right?: React.ReactNode; children: React.ReactNode; id?: string }) {
  return (
    <section className="panel" aria-labelledby={id ? `${id}-h` : undefined} id={id}>
      <div className="panel-h"><h2 id={id ? `${id}-h` : undefined}>{title}</h2>{right}</div>
      <div className="panel-b">{children}</div>
    </section>
  );
}

export function GuardPanel({ guard, pending }: { guard?: GuardResult | null; pending?: boolean }) {
  if (pending) return <p className="unavailable"><span className="spinner" aria-hidden /> CHECKING</p>;
  if (!guard) return <p className="unavailable">REALITY GUARD: DATA UNAVAILABLE</p>;
  const reasons: string[] = [];
  if (guard.max_mahalanobis > guard.train_mahalanobis_p95)
    reasons.push(`Max Mahalanobis distance ${fmt(guard.max_mahalanobis, 2)} exceeds the training P95 of ${fmt(guard.train_mahalanobis_p95, 2)} (P99 ${fmt(guard.train_mahalanobis_p99, 2)}).`);
  if (guard.isolation_forest_anomalies > 0) reasons.push(`Isolation Forest flagged ${guard.isolation_forest_anomalies} month(s) as anomalous.`);
  for (const f of guard.out_of_range_features)
    reasons.push(`Feature ${f.feature} reaches ${fmt(f.min_seen, 3)} to ${fmt(f.max_seen, 3)}; training range ${fmt(f.train_min, 3)} to ${fmt(f.train_max, 3)}.`);
  return (
    <div className="grid" style={{ gap: 8 }}>
      <div className="row"><span className={`tag ${tierClass(guard.tier)}`} data-testid="guard-tier"><span className="dot" />{guard.tier}</span>
        <span className="muted" style={{ fontSize: "var(--fs-s)" }}>{TIER_TEXT[guard.tier]}</span></div>
      <div className="mono muted" style={{ fontSize: "var(--fs-xs)" }}>
        Months by tier: {(["HIGH", "MEDIUM", "LOW", "OOD"] as const).map((t) => `${t} ${guard.months_by_tier?.[t] ?? 0}`).join(" / ")}
      </div>
      <details>
        <summary className="label">Reasons ({reasons.length})</summary>
        {reasons.length === 0 ? <p className="muted" style={{ marginTop: 6 }}>All inputs inside the training ranges.</p> :
          <ul style={{ margin: "6px 0 0", paddingLeft: 18, fontSize: "var(--fs-s)" }}>{reasons.map((r) => <li key={r}>{r}</li>)}</ul>}
      </details>
    </div>
  );
}

export function StageList({ events, running }: { events: TraceEvent[]; running: boolean }) {
  const st = stageStates(events, running);
  const mark = { pending: "·", active: "", done: "✓", error: "×", skipped: "-" } as const;
  return (
    <ol className="stages" aria-label="Pipeline stages" aria-live="polite">
      {STAGES.map((s) => (
        <li key={s.key} data-state={st[s.key]}>
          <span className="mark" aria-hidden>{st[s.key] === "active" ? <span className="spinner" /> : mark[st[s.key]]}</span>
          <span>{s.label}</span><span className="sr-only">{st[s.key]}</span>
          <span aria-hidden>{st[s.key] === "skipped" ? "not run" : st[s.key] === "pending" ? "" : st[s.key]}</span>
        </li>
      ))}
    </ol>
  );
}

export function MetricCards({ summary, name, active, onSelect }: { summary?: Summary | null; name: string; active: Metric; onSelect: (m: Metric) => void }) {
  if (!summary?.[name] || !summary.baseline) return <div className="empty">METRICS: DATA UNAVAILABLE</div>;
  return (
    <div className="cards" role="group" aria-label="Metric cards: baseline vs counterfactual, select to chart">
      {METRICS.map((m) => {
        const c = summary[name][m.key], b = summary.baseline[m.key];
        const pd = c?.pct_delta;
        return (
          <button key={m.key} className="card" aria-pressed={active === m.key} onClick={() => onSelect(m.key)} data-testid={`card-${m.key}`}>
            <span className="label">{m.short} <span style={{ textTransform: "none" }}>({m.unit}, horizon mean)</span></span>
            <span className="big">{pd ? `${fmtSigned(pd.median, 2)}%` : "DATA UNAVAILABLE"}</span>
            <span className="pair"><span>Baseline P50</span><span>{fmt(b?.level.median * m.scale, m.dec)}</span></span>
            <span className="pair"><span>Scenario P50</span><span>{fmt(c?.level.median * m.scale, m.dec)}</span></span>
            <span className="pair"><span>Scenario P10 / P90</span><span>{fmt(c?.level.p10 * m.scale, m.dec)} / {fmt(c?.level.p90 * m.scale, m.dec)}</span></span>
            <span className="pair"><span>Change P10 to P90</span><span>{pd ? `${fmtSigned(pd.p10, 2)}% to ${fmtSigned(pd.p90, 2)}%` : "n/a"}</span></span>
          </button>
        );
      })}
    </div>
  );
}

export function Analysis({ r }: { r: AnalyzeRecord }) {
  const x = r.explanation;
  if (!x) return <div className="empty">ANALYSIS: DATA UNAVAILABLE</div>;
  const src = r.explanation_source === "llm" ? "AI explainer agent" : "Deterministic template (AI unavailable)";
  const block = (h: string, body: React.ReactNode) => body ? <section><h3>{h}</h3>{body}</section> : null;
  return (
    <div className="analysis" data-testid="analysis">
      <p className="label" style={{ marginBottom: 4 }}>Source: {src}{r.grounding ? ` / grounding ${r.grounding.ok ? "passed" : "failed"}` : ""}</p>
      {block("Executive result", <p>{x.executive_result}</p>)}
      {block("Key outcomes", x.key_outcomes?.length ? <ul>{x.key_outcomes.map((k) => <li key={k}>{k}</li>)}</ul> : null)}
      {block("Scenario", <p>{x.scenario}</p>)}
      {block("Baseline vs counterfactual", <><p>{x.baseline}</p><p>{x.counterfactual}</p></>)}
      {block("Uncertainty", <p>{x.uncertainty}</p>)}
      {block("Key modeled drivers", <p>{x.key_modeled_drivers}</p>)}
      {block("Critique", <p>{x.critique}</p>)}
      {block("Assumptions", x.assumptions?.length ? <ul>{x.assumptions.map((k) => <li key={k}>{k}</li>)}</ul> : null)}
      {block("Limitations", x.limitations?.length ? <ul>{x.limitations.map((k) => <li key={k}>{k}</li>)}</ul> : null)}
      {x.recommendation && block("Recommendation", <p>{x.recommendation}</p>)}
    </div>
  );
}

export function Evidence({ r }: { r: AnalyzeRecord }) {
  const claims = r.grounding?.claims ?? [];
  const sheet = new Map<string, EvidenceItem>((r.evidence_sheet ?? []).map((e) => [e.id, e]));
  if (!claims.length && !sheet.size) return <div className="empty">EVIDENCE: DATA UNAVAILABLE</div>;
  return (
    <div className="grid" style={{ gap: 6 }} data-testid="evidence">
      {claims.map((c, i) => {
        const ev = c.evidence_id ? sheet.get(c.evidence_id) : undefined;
        return (
          <details key={i} className="panel" style={{ padding: "8px 10px" }}>
            <summary style={{ fontSize: "var(--fs-s)" }}><span className="tag">{c.evidence_id ?? "unlinked"}</span> {c.text}</summary>
            <dl className="kv" style={{ marginTop: 8 }}>
              <dt>Field</dt><dd>{c.field}</dd>
              <dt>Tool</dt><dd>{c.tool ?? ev?.tool ?? "DATA UNAVAILABLE"}</dd>
              <dt>Tool call</dt><dd>{c.tool_call_id ?? ev?.tool_call_id ?? "DATA UNAVAILABLE"}</dd>
              <dt>Run id</dt><dd>{c.run_id ?? ev?.run_id ?? "DATA UNAVAILABLE"}</dd>
              <dt>Value</dt><dd>{ev ? `${ev.display} ${ev.unit}` : c.value !== undefined ? String(c.value) : "DATA UNAVAILABLE"}</dd>
              {ev && <><dt>Path</dt><dd>{ev.path}</dd></>}
            </dl>
          </details>
        );
      })}
      <details>
        <summary className="label">Full evidence sheet ({sheet.size})</summary>
        <div style={{ overflowX: "auto" }}>
          <table>
            <thead><tr><th>Id</th><th>Label</th><th className="num">Value</th><th>Tool</th><th>Run id</th></tr></thead>
            <tbody>{[...sheet.values()].map((e) => (
              <tr key={e.id}><td className="mono">{e.id}</td><td>{e.label}</td><td className="num mono">{e.display} {e.unit}</td>
                <td className="mono">{e.tool}</td><td className="mono">{e.run_id}</td></tr>
            ))}</tbody>
          </table>
        </div>
      </details>
    </div>
  );
}

export function Critic({ r }: { r: AnalyzeRecord }) {
  const c = r.critic;
  if (!c) return <div className="empty">CRITIC: DATA UNAVAILABLE</div>;
  const cls = c.verdict === "OK" ? "ok" : c.verdict === "CAUTION" ? "caution" : "block";
  return (
    <div className="grid" style={{ gap: 8 }} data-testid="critic">
      <div className="row"><span className={`tag ${cls}`}><span className="dot" />{c.verdict}</span>
        <span className="muted" style={{ fontSize: "var(--fs-s)" }}>Final verdict is the stricter of deterministic rules and the critic agent.</span></div>
      <div>
        <p className="label">Deterministic rules: {c.deterministic.verdict}</p>
        <ul style={{ margin: 0, paddingLeft: 18, fontSize: "var(--fs-s)" }}>
          {c.deterministic.reasons.map((x, i) => <li key={i}><span className="mono">[{x.level}]</span> {x.reason}</li>)}
          {c.deterministic.reasons.length === 0 && <li>No rule fired.</li>}
        </ul>
      </div>
      <div>
        <p className="label">Critic agent: {c.llm ? c.llm.verdict : "not run (AI unavailable)"}</p>
        {c.llm && <ul style={{ margin: 0, paddingLeft: 18, fontSize: "var(--fs-s)" }}>{c.llm.reasons.map((x, i) => <li key={i}>{x}</li>)}</ul>}
      </div>
    </div>
  );
}

export function Trace({ events, metrics }: { events: TraceEvent[]; metrics?: AnalyzeRecord["metrics"] }) {
  if (!events.length) return <div className="empty">TRACE: NO EVENTS YET</div>;
  const total = Math.max(1, ...events.map((e) => e.t_ms + (e.duration_ms ?? 0)));
  return (
    <div data-testid="trace">
      {metrics && (
        <p className="mono muted" style={{ fontSize: "var(--fs-xs)" }}>
          {metrics.llm_calls} LLM calls / {metrics.tool_calls} tool calls / {metrics.tokens.total} tokens / LLM {fmt(metrics.llm_ms)} ms /
          tools {fmt(metrics.tool_ms)} ms / total {fmt(metrics.elapsed_ms)} ms
        </p>
      )}
      <ol className="timeline">
        {events.map((e) => (
          <li key={e.seq}>
            <span title={e.timestamp}>{fmtTime(e.timestamp)}</span>
            <span className="hide-m" style={{ color: e.status === "ok" ? "var(--ok)" : e.status === "error" || e.status === "rejected" ? "var(--block)" : "var(--caution)" }}>{e.status}</span>
            <span className="hide-m">{e.agent}{e.tool ? ` / ${e.tool}` : ""}</span>
            <span style={{ fontFamily: "var(--font-sans)", fontSize: "var(--fs-s)" }}>{e.action}: {e.summary}
              <span className="bar" style={{ display: "block", marginTop: 4, marginLeft: `${(e.t_ms / total) * 100}%`,
                width: `${Math.max(0.5, ((e.duration_ms ?? 0) / total) * 100)}%` }} aria-hidden /></span>
            <span style={{ textAlign: "right" }}>{e.duration_ms !== null ? `${fmt(e.duration_ms, 1)} ms` : ""}</span>
          </li>
        ))}
      </ol>
    </div>
  );
}

export function CompareTable({ summary, names }: { summary: Summary; names: string[] }) {
  return (
    <div style={{ overflowX: "auto" }} data-testid="compare">
      <table>
        <thead><tr><th>Metric</th><th className="num">Baseline P50</th>{names.map((n) => <th key={n} className="num">{n}: change P50 [P10 to P90]</th>)}</tr></thead>
        <tbody>{METRICS.map((m) => (
          <tr key={m.key}>
            <td>{m.label} <span className="muted">({m.unit})</span></td>
            <td className="num mono">{fmt(summary.baseline?.[m.key]?.level.median * m.scale, m.dec)}</td>
            {names.map((n) => {
              const p = summary[n]?.[m.key]?.pct_delta;
              return <td key={n} className="num mono">{p ? `${fmtSigned(p.median)}% [${fmtSigned(p.p10)} to ${fmtSigned(p.p90)}]` : "DATA UNAVAILABLE"}</td>;
            })}
          </tr>
        ))}</tbody>
      </table>
    </div>
  );
}
