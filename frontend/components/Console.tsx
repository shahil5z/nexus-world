"use client";
import Link from "next/link";
import { useCallback, useEffect, useMemo, useRef, useState, useSyncExternalStore } from "react";
import { analyzeStream, api, ApiError } from "@/lib/api";
import { describeIntervention, METRICS, metricInfo } from "@/lib/format";
import { historyServerSnapshot, historySnapshot, parseHistory, saveRun, subscribeHistory, type HistoryItem } from "@/lib/history";
import type { AgentStatus, AnalyzeRecord, ArenaRecord, CompareResponse, Metric, MonteCarloResponse, Scenario, TraceEvent } from "@/lib/types";
import { Arena } from "./Arena";
import { Builder } from "./Builder";
import { FanChart } from "./FanChart";
import { Analysis, CompareTable, Critic, Evidence, GuardPanel, MetricCards, Panel, StageList, Trace } from "./Results";
import { StatusBar } from "./StatusBar";

type Tab = "analysis" | "evidence" | "critic" | "trace";
type Source = "agent" | "engine";

const SEED = 42;

export function Console() {
  const [question, setQuestion] = useState("");
  const [suggestions, setSuggestions] = useState<string[] | null>(null);
  const [nPaths, setNPaths] = useState(500);
  const [running, setRunning] = useState(false);
  const [events, setEvents] = useState<TraceEvent[]>([]);
  const [record, setRecord] = useState<AnalyzeRecord | null>(null);
  const [mc, setMc] = useState<MonteCarloResponse | null>(null);
  const [mcErr, setMcErr] = useState<string | null>(null);
  const [source, setSource] = useState<Source | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [metric, setMetric] = useState<Metric>("vmt");
  const [tab, setTab] = useState<Tab>("analysis");
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [pool, setPool] = useState<Scenario[]>([]);
  const [cmp, setCmp] = useState<CompareResponse | null>(null);
  const [cmpBusy, setCmpBusy] = useState(false);
  const [cmpErr, setCmpErr] = useState<string | null>(null);
  const rawHistory = useSyncExternalStore(subscribeHistory, historySnapshot, historyServerSnapshot);
  const history = useMemo(() => parseHistory(rawHistory), [rawHistory]);
  const [ai, setAi] = useState<AgentStatus | null>(null);
  const resultsRef = useRef<HTMLDivElement>(null);
  const abortRef = useRef<AbortController | null>(null);

  useEffect(() => {
    api.suggestions().then((s) => setSuggestions(s.suggestions)).catch(() => setSuggestions([]));
  }, []);
  const onStatus = useCallback((s: AgentStatus | null) => setAi(s), []);

  const addToPool = (s: Scenario) => setPool((p) => {
    const same = p.find((x) => x.name === s.name);
    if (same && JSON.stringify(same) !== JSON.stringify(s)) {
      let k = 2;
      while (p.some((x) => x.name === `${s.name.slice(0, 55)} v${k}`)) k++;
      s = { ...s, name: `${s.name.slice(0, 55)} v${k}` };
    }
    return [...p.filter((x) => x.name !== s.name), s].slice(-6);
  });
  const remember = (item: HistoryItem, rec?: AnalyzeRecord | ArenaRecord) => { saveRun(item, rec); };

  const loadBands = async (s: Scenario, horizon: number, paths: number) => {
    setMcErr(null);
    try { setMc(await api.monteCarlo(s, horizon, Math.max(10, Math.min(1000, paths)), SEED)); }
    catch (e) { setMc(null); setMcErr((e as Error).message); }
  };

  const ask = async (q: string) => {
    if (!q.trim() || running) return;
    abortRef.current?.abort();
    const ctl = new AbortController(); abortRef.current = ctl;
    setRunning(true); setError(null); setEvents([]); setRecord(null); setMc(null); setMcErr(null); setSource("agent"); setTab("analysis");
    try {
      const r = await analyzeStream({ question: q.trim(), session_id: sessionId, n_paths: nPaths, seed: SEED },
        (m) => { if (m.type === "trace") setEvents((ev) => [...ev, m.event]); }, ctl.signal);
      setRecord(r); setEvents(r.trace); setSessionId(r.session_id);
      remember({ run_id: r.run_id, kind: "analyze", title: q.trim().slice(0, 80), status: `${r.status} / ${r.mode}`, created_utc: r.created_utc }, r);
      for (const slot of Object.values(r.session?.slots ?? {})) addToPool(slot.scenario);
      if (r.scenario && r.horizon_months && (r.status === "ok" || r.status === "partial")) void loadBands(r.scenario, r.horizon_months, r.n_paths);
    } catch (e) {
      setError(e instanceof ApiError ? `${e.code}: ${e.message}` : (e as Error).message);
    } finally {
      setRunning(false);
      resultsRef.current?.focus();
    }
  };

  const runEngine = async (s: Scenario, horizon: number, paths: number) => {
    setRunning(true); setError(null); setEvents([]); setRecord(null); setSource("engine"); setMc(null); setMcErr(null);
    try {
      const r = await api.monteCarlo(s, horizon, paths, SEED);
      setMc(r); addToPool(s);
      remember({ run_id: r.meta.run_id, kind: "engine", title: `${s.name} (engine only)`, status: r.reality_guard.tier, created_utc: new Date().toISOString() });
    } catch (e) { setError((e as Error).message); } finally { setRunning(false); resultsRef.current?.focus(); }
  };

  const compare = async () => {
    setCmpBusy(true); setCmpErr(null);
    try { setCmp(await api.compare(pool.slice(-3), 24, 300, SEED)); }
    catch (e) { setCmpErr((e as Error).message); } finally { setCmpBusy(false); }
  };

  const scenName = record?.scenario?.name ?? (mc ? Object.keys(mc.summary).find((k) => k !== "baseline") : undefined) ?? "";
  const summary = mc?.summary ?? record?.outputs?.summary ?? null;
  const guard = record?.guard ?? mc?.reality_guard ?? null;
  const mi = metricInfo(metric);
  const fallback = record && record.mode !== "agentic";
  const exploratory = record?.exploratory || guard?.tier === "OOD";

  return (
    <div className="console">
      <aside aria-label="Controls">
        <Panel title="System status" id="status"><StatusBar onStatus={onStatus} /></Panel>
        <Panel title="Command" id="cmd">
          <form onSubmit={(e) => { e.preventDefault(); ask(question); }} className="grid" style={{ gap: 10 }}>
            <label className="field"><span>Ask a what-if question</span>
              <textarea value={question} onChange={(e) => setQuestion(e.target.value)} maxLength={1000} rows={3}
                placeholder="What if gasoline rises 20% for 12 months?" data-testid="question"
                onKeyDown={(e) => { if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) ask(question); }} /></label>
            <label className="field"><span>Monte Carlo paths (50 to 1000)</span>
              <input type="number" min={50} max={1000} step={50} value={nPaths} onChange={(e) => setNPaths(Math.max(50, Math.min(1000, Number(e.target.value))))} /></label>
            <button className="btn primary" type="submit" disabled={running || !question.trim()} data-testid="ask">{running ? "Running" : "Launch simulation"}</button>
            {ai && !ai.llm_configured && <p className="alert" style={{ margin: 0 }}>AI agents are not configured on this server. Runs use the deterministic parser, engine and template, labelled ENGINE-ONLY.</p>}
          </form>
          <div style={{ marginTop: 12 }}>
            <p className="label" style={{ marginBottom: 6 }}>Supported prompts</p>
            {suggestions === null ? <p className="unavailable">LOADING</p> : suggestions.length === 0 ? <p className="unavailable">DATA UNAVAILABLE</p> : (
              <div className="grid" style={{ gap: 4 }}>
                {suggestions.map((s) => <button key={s} type="button" className="chip" onClick={() => { setQuestion(s); ask(s); }} disabled={running}>{s}</button>)}
              </div>
            )}
          </div>
        </Panel>
        <Panel title="Scenario builder" id="builder"><Builder onRun={runEngine} busy={running} /></Panel>
        <Panel title="Run history" id="history" right={<span className="label">this browser</span>}>
          {history.length === 0 ? <div className="empty">NO RUNS YET</div> : (
            <ul style={{ listStyle: "none", margin: 0, padding: 0, display: "grid", gap: 6 }}>
              {history.map((h) => (
                <li key={h.run_id} style={{ fontSize: "var(--fs-s)" }}>
                  {h.kind === "engine" ? <span className="mono">{h.run_id}</span> : <Link href={`/run/${h.run_id}`} className="mono">{h.run_id}</Link>}
                  <div className="muted">{h.title} / {h.status}</div>
                </li>
              ))}
            </ul>
          )}
        </Panel>
      </aside>

      <div className="main-col" ref={resultsRef} tabIndex={-1} aria-live="polite" aria-busy={running} style={{ outline: "none" }}>
        {(running || events.length > 0) && source === "agent" && (
          <Panel title="Pipeline" id="pipeline" right={<span className="label">{running ? "live trace stream" : "complete"}</span>}>
            <StageList events={events} running={running} />
          </Panel>
        )}
        {error && <p className="alert error" role="alert">Run failed: {error}</p>}
        {!source && !error && (
          <div className="panel"><div className="panel-b">
            <p className="label">Ready</p>
            <h1 style={{ fontSize: "var(--fs-xl)", fontWeight: 400, margin: "6px 0 10px" }}>Mission console</h1>
            <p className="muted">Ask a question or build a scenario. Results show the baseline against your counterfactual with P10 to P90 percentile spreads,
              the Reality Guard tier, and, for questions, the AI analysis with cited evidence and a full agent trace.</p>
          </div></div>
        )}
        {record && (
          <div className="row" data-testid="run-header">
            <span className="tag accent">run {record.run_id}</span>
            <span className={`tag ${record.status === "ok" ? "ok" : "caution"}`}>status {record.status}</span>
            <span className={`tag ${fallback ? "caution" : "ok"}`} data-testid="run-mode">{record.mode === "agentic" ? `AI agents / ${record.model}` : record.mode === "partial_fallback" ? "partial AI fallback" : "ENGINE-ONLY (AI unavailable)"}</span>
            {exploratory && <span className="tag block">exploratory</span>}
            <span className="tag">seed {record.seed} / {record.n_paths} paths</span>
            <Link href={`/run/${record.run_id}`} className="btn small">Open run view</Link>
          </div>
        )}
        {source === "engine" && mc && (
          <div className="row"><span className="tag accent">run {mc.meta.run_id}</span><span className="tag caution">ENGINE ONLY: no AI analysis</span>
            <span className="tag">seed {mc.meta.seed} / {mc.n_paths} paths</span>{exploratory && <span className="tag block">exploratory</span>}</div>
        )}
        {record && record.status !== "ok" && record.status !== "partial" && record.explanation && (
          <p className="alert" role="status">{record.explanation.executive_result}</p>
        )}
        {record?.warnings?.length ? <details className="alert"><summary>Warnings ({record.warnings.length})</summary><ul>{record.warnings.map((w) => <li key={w}>{w}</li>)}</ul></details> : null}

        {(record?.scenario || mc) && (
          <Panel title="Scenario and Reality Guard" id="guard">
            {record?.scenario && <ul style={{ margin: "0 0 10px", paddingLeft: 18 }}>{record.scenario.interventions.map((i, k) => <li key={k}>{describeIntervention(i)}</li>)}</ul>}
            <GuardPanel guard={guard} />
          </Panel>
        )}

        {summary && scenName && (
          <>
            <MetricCards summary={summary} name={scenName} active={metric} onSelect={setMetric} />
            <Panel title={`${mi.label} (${mi.unit})`} id="fan" right={
              <label className="row" style={{ gap: 6 }}><span className="label">Metric</span>
                <select value={metric} onChange={(e) => setMetric(e.target.value as Metric)} style={{ width: "auto", padding: "3px 6px" }}>
                  {METRICS.map((m) => <option key={m.key} value={m.key}>{m.short}</option>)}
                </select></label>}>
              {mc ? <FanChart months={mc.months} baseline={mc.bands[metric]?.baseline} scenario={mc.bands[metric]?.[scenName]} scenarioName={scenName}
                label={mi.label} unit={mi.unit} scale={mi.scale} dec={mi.dec} /> : <div className="empty">FAN CHART: DATA UNAVAILABLE{mcErr ? ` (${mcErr})` : ""}</div>}
              <p className="muted" style={{ fontSize: "var(--fs-xs)", marginTop: 6 }}>Percentile spread across seeded Monte Carlo paths, not a confidence interval. Hover or focus the chart and use arrow keys.</p>
            </Panel>
          </>
        )}

        {record && (
          <section className="panel" aria-label="Analysis">
            <div className="tabs" role="tablist" aria-label="Run details">
              {(["analysis", "evidence", "critic", "trace"] as Tab[]).map((t) => (
                <button key={t} role="tab" id={`tab-${t}`} aria-selected={tab === t} aria-controls={`tp-${t}`} onClick={() => setTab(t)} data-testid={`tab-${t}`}
                  onKeyDown={(e) => {
                    const order: Tab[] = ["analysis", "evidence", "critic", "trace"];
                    const i = order.indexOf(t);
                    if (e.key === "ArrowRight") { const n = order[(i + 1) % 4]; setTab(n); document.getElementById(`tab-${n}`)?.focus(); }
                    if (e.key === "ArrowLeft") { const n = order[(i + 3) % 4]; setTab(n); document.getElementById(`tab-${n}`)?.focus(); }
                  }} tabIndex={tab === t ? 0 : -1}>{t === "analysis" ? "AI analysis" : t === "trace" ? "Agent trace" : t}</button>
              ))}
            </div>
            <div className="panel-b" role="tabpanel" id={`tp-${tab}`} aria-labelledby={`tab-${tab}`}>
              {tab === "analysis" && <Analysis r={record} />}
              {tab === "evidence" && <Evidence r={record} />}
              {tab === "critic" && <Critic r={record} />}
              {tab === "trace" && <Trace events={record.trace} metrics={record.metrics} />}
            </div>
          </section>
        )}

        <Panel title="Compare: baseline + A / B / C" id="compare" right={<span className="label">{pool.length} scenario(s) in session</span>}>
          {pool.length === 0 ? <div className="empty">RUN A SCENARIO TO ADD IT HERE</div> : (
            <div className="grid" style={{ gap: 10 }}>
              <div className="slots">
                <div><p className="label">Baseline</p>No interventions (immutable)</div>
                {pool.slice(-3).map((s, i) => (
                  <div key={s.name}><p className="label">{"ABC"[i]} / {s.name}</p>{s.interventions.map((x, k) => <div key={k} className="muted">{describeIntervention(x)}</div>)}</div>
                ))}
              </div>
              <div className="row"><button className="btn" onClick={compare} disabled={cmpBusy} data-testid="compare-run">{cmpBusy ? "Comparing" : "Compare (24 mo, 300 paths, shared seed)"}</button></div>
              {cmpErr && <p className="alert error">{cmpErr}</p>}
              {cmp && <CompareTable summary={cmp.summary} names={cmp.scenarios.filter((n) => n !== "baseline")} />}
            </div>
          )}
        </Panel>

        <Panel title="Policy arena" id="arena">
          <Arena candidates={pool} onDone={(r) => remember({ run_id: r.run_id, kind: "policy_arena", title: `Arena: ${r.ranking.map((x) => x.candidate).join(", ")}`, status: "ok", created_utc: r.created_utc }, r)} />
        </Panel>
      </div>
    </div>
  );
}
