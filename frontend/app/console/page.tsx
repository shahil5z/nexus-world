import type { Metadata } from "next";
import { Console } from "@/components/Console";

export const metadata: Metadata = { title: "Console", description: "Run counterfactual scenarios with uncertainty, Reality Guard and AI analysis." };

export default function Page() {
  return <div className="wrap"><Console /></div>;
}
