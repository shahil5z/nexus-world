import type { Metadata } from "next";
import { RunView } from "@/components/RunView";

export async function generateMetadata({ params }: { params: Promise<{ id: string }> }): Promise<Metadata> {
  const { id } = await params;
  return { title: `Run ${id}`, robots: { index: false } };
}

export default async function Page({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  return <div className="wrap" style={{ padding: "18px 24px 40px" }}><RunView id={id} /></div>;
}
