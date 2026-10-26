import type { Metadata } from "next";
import Link from "next/link";

export const metadata: Metadata = { title: "Page not found" };

export default function NotFound() {
  return (
    <div className="wrap" style={{ padding: "80px 24px" }}>
      <p className="label">404</p>
      <h1 style={{ fontSize: "var(--fs-xl)", fontWeight: 400, margin: "8px 0 16px" }}>Coordinates not found</h1>
      <Link href="/" className="btn">Return to overview</Link>
    </div>
  );
}
