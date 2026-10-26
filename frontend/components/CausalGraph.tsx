import graphJson from "@/lib/generated/causal_graph.json";
import { layout, NODE_LABEL } from "@/lib/graph";
import type { CausalGraph as G } from "@/lib/types";

const W = 900, H = 400, BW = 96;
const STROKE: Record<string, string> = { learned: "var(--accent)", identity: "var(--base)", assumption: "var(--caution)" };

/** Rendered from knowledge/causal_graph.json, the same file the agents read. Not a decorative illustration. */
export function CausalGraph() {
  const g = graphJson as unknown as G;
  const nodes = layout(g, W, H);
  const at = Object.fromEntries(nodes.map((n) => [n.id, n]));
  const label = `Causal graph version ${g.version}: ${g.nodes.length} variables and ${g.edges.length} edges. ` +
    g.edges.map((e) => `${e.from} to ${e.to} (${e.type}${e.lag_months ? `, lag ${e.lag_months} month` : ""})`).join("; ");
  return (
    <figure className="panel" style={{ margin: 0 }}>
      <div className="panel-h"><h2>Causal graph v{g.version}</h2><span className="label">{g.nodes.length} nodes / {g.edges.length} edges</span></div>
      <div className="panel-b">
        <svg viewBox={`0 0 ${W} ${H}`} role="img" aria-label={label}>
          <defs>
            {Object.entries(STROKE).map(([k, c]) => (
              <marker key={k} id={`arr-${k}`} viewBox="0 0 8 8" refX="7" refY="4" markerWidth="6" markerHeight="6" orient="auto">
                <path d="M0,0 L8,4 L0,8 z" fill={c} />
              </marker>
            ))}
          </defs>
          {g.edges.map((e, i) => {
            const a = at[e.from], b = at[e.to];
            if (!a || !b) return null;
            if (a === b) {
              return (
                <g key={i}>
                  <path d={`M${a.x - 12},${a.y - 12} C${a.x - 30},${a.y - 46} ${a.x + 30},${a.y - 46} ${a.x + 12},${a.y - 13}`}
                    fill="none" stroke={STROKE[e.type]} strokeWidth="1" markerEnd={`url(#arr-${e.type})`} />
                  <text x={a.x} y={a.y - 40} textAnchor="middle" fill="var(--muted)" style={{ fontFamily: "var(--font-mono)", fontSize: 9 }}>lag {e.lag_months}</text>
                </g>
              );
            }
            const twin = g.edges.findIndex((o) => o.from === e.from && o.to === e.to) !== i;
            const off = twin ? 7 : 0;
            const x1 = a.x + BW / 2, x2 = b.x - BW / 2 - 4, mx = (x1 + x2) / 2;
            return (
              <g key={i}>
                <path d={`M${x1},${a.y + off} C${mx},${a.y + off} ${mx},${b.y + off} ${x2},${b.y + off}`} fill="none"
                  stroke={STROKE[e.type]} strokeOpacity="0.8" strokeWidth="1" strokeDasharray={e.type === "assumption" ? "3 3" : undefined}
                  markerEnd={`url(#arr-${e.type})`} />
                {e.lag_months ? <text x={mx} y={(a.y + b.y) / 2 + off - 4} textAnchor="middle" fill="var(--muted)"
                  style={{ fontFamily: "var(--font-mono)", fontSize: 9 }}>lag {e.lag_months}</text> : null}
              </g>
            );
          })}
          {nodes.map((n) => (
            <g key={n.id}>
              <rect x={n.x - BW / 2} y={n.y - 12} width={BW} height="24" rx="1" fill="var(--bg-2)"
                stroke={n.kind === "driver" ? "var(--accent)" : "var(--line-2)"} />
              <text x={n.x} y={n.y + 4} textAnchor="middle" fill={n.kind === "driver" ? "var(--text)" : "var(--text-2)"}
                style={{ fontFamily: "var(--font-mono)", fontSize: 10, letterSpacing: "0.06em" }}>{NODE_LABEL[n.id] ?? n.id}</text>
            </g>
          ))}
        </svg>
        <div className="legend" style={{ marginTop: 8 }}>
          {Object.entries(STROKE).map(([k, c]) => (
            <span key={k}><i style={{ background: c, height: 2 }} />{k}: {g.edge_types[k]}</span>
          ))}
        </div>
      </div>
    </figure>
  );
}
