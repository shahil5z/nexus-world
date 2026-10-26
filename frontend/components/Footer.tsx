import Image from "next/image";

/** Site-wide footer, rendered once from the root layout. */
export function Footer() {
  return (
    <footer className="wrap">
      <div className="footer row" style={{ justifyContent: "space-between" }}>
        <span className="row"><Image src="/logo-96.png" alt="" width={20} height={20} /> NEXUS WORLD</span>
        <span>A Data Science portfolio project by Shahil</span>
        <span className="mono" style={{ fontSize: "var(--fs-xs)" }}>Not a forecast. Not financial or policy advice.</span>
      </div>
    </footer>
  );
}
