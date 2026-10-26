// Copies the versioned causal graph from the Python knowledge layer so the landing visual uses the real file.
import { copyFileSync, existsSync, mkdirSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));
const src = resolve(here, "../../nexus/agentic/knowledge/causal_graph.json");
const dst = resolve(here, "../lib/generated/causal_graph.json");
mkdirSync(dirname(dst), { recursive: true });
if (existsSync(src)) {
  copyFileSync(src, dst);
  console.log("synced causal_graph.json");
} else if (!existsSync(dst)) {
  console.error("causal_graph.json not found");
  process.exit(1);
}
