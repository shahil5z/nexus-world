import type { Metadata, Viewport } from "next";
import { IBM_Plex_Mono, IBM_Plex_Sans } from "next/font/google";
import "./globals.css";
import { Header } from "@/components/Header";

const sans = IBM_Plex_Sans({ subsets: ["latin"], weight: ["400", "500"], variable: "--plex-sans", display: "swap" });
const mono = IBM_Plex_Mono({ subsets: ["latin"], weight: ["400", "500"], variable: "--plex-mono", display: "swap" });

const SITE = process.env.NEXT_PUBLIC_SITE_URL ?? "http://localhost:3000";
const DESC =
  "NEXUS // WORLD is a counterfactual simulation lab for US energy and mobility. Change gasoline, electricity, income or " +
  "unemployment and see modeled travel, emissions, fuel spending and household energy burden with uncertainty, an " +
  "out-of-distribution guard, and evidence-grounded AI analysis.";

export const metadata: Metadata = {
  metadataBase: new URL(SITE),
  title: { default: "NEXUS // WORLD: Simulate tomorrow before you build it", template: "%s | NEXUS // WORLD" },
  description: DESC,
  applicationName: "NEXUS // WORLD",
  openGraph: { type: "website", siteName: "NEXUS // WORLD", title: "NEXUS // WORLD", description: DESC, url: "/" },
  twitter: { card: "summary_large_image", title: "NEXUS // WORLD", description: DESC },
  robots: { index: true, follow: true },
};
export const viewport: Viewport = { themeColor: "#06080b", width: "device-width", initialScale: 1 };

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={`${sans.variable} ${mono.variable}`}>
      <body>
        <a href="#main" className="skip">Skip to content</a>
        <Header />
        <main id="main">{children}</main>
      </body>
    </html>
  );
}
