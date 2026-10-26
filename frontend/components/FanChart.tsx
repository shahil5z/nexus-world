"use client";
import { useId, useMemo, useState } from "react";
import type { Band } from "@/lib/types";
import { fmt } from "@/lib/format";

interface Props { months: string[]; baseline?: Band; scenario?: Band; scenarioName: string; label: string; unit: string;
  scale: number; dec: number }

const W = 820, H = 300, L = 64, R = 16, T = 16, B = 34;

/** Percentile fan chart: P10 to P90 and P25 to P75 bands, median line, dashed baseline median. Keyboard: arrow keys. */
export function FanChart({ months, baseline, scenario, scenarioName, label, unit, scale, dec }: Props) {
  const [hi, setHi] = useState<number | null>(null);
  const id = useId();
  const n = months.length;
  const s = (a?: number[]) => (a ? a.map((v) => v * scale) : undefined);
  const sc = useMemo(() => scenario && { p10: s(scenario.p10)!, p25: s(scenario.p25)!, med: s(scenario.median)!, p75: s(scenario.p75)!, p90: s(scenario.p90)! },
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [scenario, scale]);
  const bl = useMemo(() => baseline && { med: s(baseline.median)!, p10: s(baseline.p10)!, p90: s(baseline.p90)! },
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [baseline, scale]);
  if (!sc || n === 0) return <div className="empty">FAN CHART: DATA UNAVAILABLE</div>;
  const all = [...sc.p10, ...sc.p90, ...(bl ? [...bl.p10, ...bl.p90] : [])];
  let lo = Math.min(...all), hiV = Math.max(...all);
  const pad = (hiV - lo) * 0.08 || Math.abs(hiV) * 0.01 || 1;
  lo -= pad; hiV += pad;
  const x = (i: number) => L + (n === 1 ? 0 : (i / (n - 1)) * (W - L - R));
  const y = (v: number) => T + (1 - (v - lo) / (hiV - lo)) * (H - T - B);
  const line = (a: number[]) => a.map((v, i) => `${i ? "L" : "M"}${x(i).toFixed(1)},${y(v).toFixed(1)}`).join("");
  const area = (top: number[], bot: number[]) =>
    line(top) + bot.map((_, k) => { const i = n - 1 - k; return `L${x(i).toFixed(1)},${y(bot[i]).toFixed(1)}`; }).join("") + "Z";
  const ticks = Array.from({ length: 5 }, (_, k) => lo + ((k + 0.5) / 5) * (hiV - lo));
  const xt = months.map((m, i) => ({ m, i })).filter(({ i }) => i % Math.max(1, Math.ceil(n / 8)) === 0);
  const move = (clientX: number, rect: DOMRect) => {
    const px = ((clientX - rect.left) / rect.width) * W;
    setHi(Math.max(0, Math.min(n - 1, Math.round(((px - L) / (W - L - R)) * (n - 1)))));
  };
  const h = hi ?? null;
  return (
    <div className="chart-wrap">
      <svg viewBox={`0 0 ${W} ${H}`} role="img" aria-labelledby={`${id}-t`} aria-describedby={`${id}-tbl`} tabIndex={0}
        onMouseMove={(e) => move(e.clientX, e.currentTarget.getBoundingClientRect())} onMouseLeave={() => setHi(null)}
        onKeyDown={(e) => {
          if (e.key === "ArrowRight") { setHi((v) => Math.min(n - 1, (v ?? -1) + 1)); e.preventDefault(); }
          if (e.key === "ArrowLeft") { setHi((v) => Math.max(0, (v ?? n) - 1)); e.preventDefault(); }
          if (e.key === "Escape") setHi(null);
        }} onBlur={() => setHi(null)}>
        <title id={`${id}-t`}>{`${label} (${unit}), ${scenarioName} vs baseline, P10 to P90 percentile spread over ${n} months`}</title>
        {ticks.map((t) => (
          <g key={t}>
            <line x1={L} x2={W - R} y1={y(t)} y2={y(t)} stroke="var(--line)" />
            <text x={L - 8} y={y(t) + 3} textAnchor="end" fill="var(--muted)" style={{ fontFamily: "var(--font-mono)", fontSize: 10 }}>{fmt(t, dec)}</text>
          </g>
        ))}
        {xt.map(({ m, i }) => (
          <text key={m} x={x(i)} y={H - 12} textAnchor="middle" fill="var(--muted)" style={{ fontFamily: "var(--font-mono)", fontSize: 10 }}>{m.slice(0, 7)}</text>
        ))}
        {bl && <path d={area(bl.p90, bl.p10)} fill="var(--base-band)" />}
        <path d={area(sc.p90, sc.p10)} fill="var(--accent-band-2)" />
        <path d={area(sc.p75, sc.p25)} fill="var(--accent-band)" />
        {bl && <path d={line(bl.med)} fill="none" stroke="var(--base)" strokeDasharray="4 4" strokeWidth="1.2" />}
        <path d={line(sc.med)} fill="none" stroke="var(--accent)" strokeWidth="1.6" />
        {h !== null && (
          <g>
            <line x1={x(h)} x2={x(h)} y1={T} y2={H - B} stroke="var(--line-2)" />
            <circle cx={x(h)} cy={y(sc.med[h])} r="3" fill="var(--accent)" />
            {bl && <circle cx={x(h)} cy={y(bl.med[h])} r="3" fill="var(--base)" />}
          </g>
        )}
      </svg>
      {h !== null && (
        <div className="tooltip" role="status" style={{ left: `${Math.min(72, (x(h) / W) * 100)}%`, top: 8 }}>
          <div>{months[h]}</div>
          <div style={{ color: "var(--accent)" }}>{scenarioName} P50 {fmt(sc.med[h], dec)}</div>
          <div>P10 to P90 {fmt(sc.p10[h], dec)} to {fmt(sc.p90[h], dec)}</div>
          {bl && <div style={{ color: "var(--base)" }}>Baseline P50 {fmt(bl.med[h], dec)}</div>}
        </div>
      )}
      <div className="legend" style={{ marginTop: 6 }}>
        <span><i style={{ background: "var(--accent)", height: 2 }} />{scenarioName} median</span>
        <span><i style={{ background: "var(--accent-band)" }} />P25 to P75</span>
        <span><i style={{ background: "var(--accent-band-2)" }} />P10 to P90 percentile spread</span>
        {bl && <span><i style={{ borderTop: "1px dashed var(--base)", height: 0 }} />Baseline median</span>}
      </div>
      <table id={`${id}-tbl`} className="sr-only">
        <caption>{label} by month, {unit}</caption>
        <thead><tr><th>Month</th><th>P10</th><th>Median</th><th>P90</th><th>Baseline median</th></tr></thead>
        <tbody>{months.map((m, i) => (
          <tr key={m}><td>{m}</td><td>{fmt(sc.p10[i], dec)}</td><td>{fmt(sc.med[i], dec)}</td><td>{fmt(sc.p90[i], dec)}</td><td>{bl ? fmt(bl.med[i], dec) : "n/a"}</td></tr>
        ))}</tbody>
      </table>
    </div>
  );
}
