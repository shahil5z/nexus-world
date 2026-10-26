"use client";
import Image from "next/image";
import Link from "next/link";
import { usePathname } from "next/navigation";

export function Header() {
  const p = usePathname();
  const cur = (h: string) => (p === h || (h !== "/" && p.startsWith(h)) ? "page" : undefined);
  return (
    <header className="topbar">
      <div className="wrap">
        <Link href="/" className="brand" aria-label="NEXUS WORLD home">
          <Image src="/logo-96.png" alt="" width={26} height={26} priority />
          <span>NEXUS WORLD</span>
        </Link>
        <nav className="nav" aria-label="Primary">
          <Link href="/" aria-current={cur("/")}>Overview</Link>
          <Link href="/#method" className="hide-s">Method</Link>
          <Link href="/#limits" className="hide-s">Limits</Link>
          <Link href="/console" aria-current={cur("/console")}>Console</Link>
        </nav>
      </div>
    </header>
  );
}
