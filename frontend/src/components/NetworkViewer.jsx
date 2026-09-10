import { lazy, Suspense, useId, useState } from "react";
import NetworkGraph from "./NetworkGraph";
import "./NetworkViewer.css";

const RelationGraph = lazy(() => import("./RelationGraph"));

export default function NetworkViewer({ mainCriminal, relations, onNodeClick, height, mini = false }) {
  const [mode, setMode] = useState("map");
  const panelId = useId();

  return <div className="network-viewer">
    <div role="group" aria-label="Network view" style={{ display: "flex", flexWrap: "wrap", gap: 8, padding: "12px 0" }}>
      {[['map', 'Map'], ['relationships', 'Relationship chart']].map(([value, label]) => (
        <button key={value} type="button"
          className={`stamp-btn small ${mode === value ? "stamp-btn-active" : ""}`}
          aria-pressed={mode === value} aria-controls={panelId}
          onClick={() => setMode(value)}>{label}</button>
      ))}
    </div>
    <div id={panelId} className={`graph-frame${mini ? " mini" : ""}`}>
      <div hidden={mode !== "map"} style={{ width: "100%" }}>
        <NetworkGraph mainCriminal={mainCriminal} relations={relations} onNodeClick={onNodeClick} height={height} />
      </div>
      {mode === "relationships" && <Suspense fallback={<p role="status" style={{ padding: 12 }}>Loading relationship chart…</p>}>
        <RelationGraph key={mainCriminal.id}
          mainCriminal={mainCriminal} onNodeClick={onNodeClick} height={height} />
      </Suspense>}
    </div>
  </div>;
}
