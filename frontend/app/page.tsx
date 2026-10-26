import Image from "next/image";
import Link from "next/link";
import { CausalGraph } from "@/components/CausalGraph";
import { ModelEvidence } from "@/components/ModelEvidence";

const STEPS = [
  ["01", "Describe a change", "Type a question or build a scenario: gasoline, electricity, real income or unemployment, with a start month and duration."],
  ["02", "Reality Guard", "Every scenario is scored against the training data distribution before it runs. Out-of-distribution runs are refused unless labelled exploratory."],
  ["03", "Monte Carlo engine", "A Ridge transition model plus accounting identities and household agents simulate up to 36 months over hundreds of seeded paths."],
  ["04", "Agents explain", "A supervisor routes tools, a critic checks the result, an explainer writes the analysis, and every number must cite an evidence id."],
];
const STACK = [
  ["Frontend", "Next.js 16, React 19, TypeScript, hand-built SVG charts"],
  ["API", "FastAPI, Pydantic, NDJSON streaming of real trace events"],
  ["Engine", "NumPy, pandas, scikit-learn Ridge, Isolation Forest, Mahalanobis guard"],
  ["Agents", "OpenAI Agents SDK, tool calls into the engine, deterministic critic rules"],
  ["Data", "Public FRED monthly series, versioned by content hash"],
  ["TensorFlow", "Evaluated as a 5-member ensemble. Not selected for runtime: it did not beat the baselines."],
];

export default function Home() {
  return (
    <div className="wrap">
      <section className="hero" aria-labelledby="hero-title">
        <div>
          <p className="label">Counterfactual lab / US energy and mobility</p>
          <h1 id="hero-title">Simulate tomorrow before you build it.</h1>
          <p className="lede">
            NEXUS // WORLD asks what would happen if gasoline, electricity, income or jobs moved, and answers with modeled
            ranges, not single guesses. Each run states how far it strays from the data it learned from.
          </p>
          <div className="row" style={{ marginTop: 26 }}>
            <Link href="/console" className="btn primary">Launch simulation</Link>
            <Link href="#method" className="btn">How it works</Link>
          </div>
          <p className="muted" style={{ marginTop: 18, fontSize: "var(--fs-s)" }}>
            Demo mode: rate limited, capped at 1000 paths and 36 months. Results are modeled, not forecasts or advice.
          </p>
        </div>
        <CausalGraph />
      </section>

      <section className="section" id="method" aria-labelledby="method-title">
        <span className="label">How it works</span>
        <h2 id="method-title">From a question to an audited counterfactual</h2>
        <div className="steps">
          {STEPS.map(([i, t, d]) => (
            <div key={i}><span className="idx">{i}</span><h3>{t}</h3><p>{d}</p></div>
          ))}
        </div>
      </section>

      <section className="section" aria-labelledby="arch-title">
        <span className="label">Architecture</span>
        <h2 id="arch-title">One request path, every step recorded</h2>
        <div className="panel">
          <div className="panel-b mono" style={{ fontSize: "var(--fs-s)", lineHeight: 1.9, overflowX: "auto", whiteSpace: "pre" }}>
{`browser ── Next.js console ── /api/* ── FastAPI
                                         ├─ input guardrail ─ supervisor agent (or deterministic parser)
                                         ├─ validate ─ Reality Guard (Mahalanobis + Isolation Forest)
                                         ├─ Monte Carlo engine (Ridge + identities + household agents)
                                         ├─ deterministic critic rules ─ critic agent
                                         ├─ explainer agent (or template) ─ grounding check
                                         └─ run record: trace, evidence sheet, versions, seed`}
          </div>
        </div>
      </section>

      <section className="section" aria-labelledby="eval-title">
        <span className="label">Model evidence, live from the API</span>
        <h2 id="eval-title">How well does it hold up?</h2>
        <ModelEvidence />
      </section>

      <section className="section" aria-labelledby="stack-title">
        <span className="label">Tech stack</span>
        <h2 id="stack-title">What actually runs</h2>
        <dl className="stack">
          {STACK.map(([k, v]) => <div key={k}><dt>{k}</dt><dd>{v}</dd></div>)}
        </dl>
      </section>

      <section className="section" id="limits" aria-labelledby="limits-title">
        <span className="label">Limitations</span>
        <h2 id="limits-title">What this is not</h2>
        <div className="grid" style={{ gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))" }}>
          <ul className="muted" style={{ margin: 0, paddingLeft: 18 }}>
            <li>US national monthly aggregates only. No regions, no daily dynamics.</li>
            <li>Modeled drivers are associations learned from history, not proven causes.</li>
            <li>In historical backtests the engine did not beat a seasonal naive baseline on level accuracy. Use it for relative what-if comparisons.</li>
            <li>Percentile spreads reflect model residual noise, not every real-world uncertainty.</li>
          </ul>
          <div className="alert info">
            <strong className="mono" style={{ fontSize: "var(--fs-xs)", letterSpacing: "0.1em" }}>DEMO MODE</strong>
            <p style={{ margin: "6px 0 0" }}>
              Requests are rate limited. When the AI layer is unavailable the console falls back to the engine-only path and labels
              it. Runs are stored in server memory per instance and in your browser, so shared links may expire.
            </p>
          </div>
        </div>
      </section>

      <footer className="footer row" style={{ justifyContent: "space-between" }}>
        <span className="row"><Image src="/logo-96.png" alt="" width={20} height={20} /> NEXUS // WORLD</span>
        <span className="mono" style={{ fontSize: "var(--fs-xs)" }}>Not a forecast. Not financial or policy advice.</span>
      </footer>
    </div>
  );
}
