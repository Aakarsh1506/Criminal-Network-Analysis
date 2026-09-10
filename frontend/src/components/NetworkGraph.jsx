import indiaMap from "/images/India.svg";
import { mapPoint } from "../utils/mapPoint";
import "./NetworkGraph.css";
import { useEffect, useRef, useState } from "react";

function NetworkGraph({ mainCriminal, relations = [], onNodeClick, height = 480 }) {
  const [view, setView] = useState({ x: 0, y: 0, zoom: 1 });
  // Labels grow with the square root of zoom instead of scaling with the map.
  const labelScale = 1 / Math.sqrt(view.zoom);
  const drag = useRef(null);
  const moved = useRef(false);
  const svgRef = useRef(null);
  useEffect(() => {
    const svg = svgRef.current;
    const preventScroll = (event) => event.preventDefault();
    svg.addEventListener("wheel", preventScroll, { passive: false });
    return () => svg.removeEventListener("wheel", preventScroll);
  }, []);
  const zoomBy = (factor) => setView((current) => {
    const zoom = Math.min(8, Math.max(1, current.zoom * factor));
    return {
      x: current.x + 611.85999 / current.zoom / 2 - 611.85999 / zoom / 2,
      y: current.y + 695.70178 / current.zoom / 2 - 695.70178 / zoom / 2,
      zoom,
    };
  });
  const people = [...new Map([mainCriminal, ...relations.map((r) => r.criminal)]
    .map((person) => [String(person.id), person])).values()];
  const groups = new Map();
  const unplaced = [];
  for (const person of people) {
    const city = person.location?.city;
    const point = mapPoint(city);
    if (!point) {
      unplaced.push(person.name);
      continue;
    }
    if (!groups.has(city)) groups.set(city, { point, people: [] });
    groups.get(city).people.push(person);
  }
  const origin = mapPoint(mainCriminal.location?.city);

  return (
    <div className="geographic-network" style={{ width: "100%" }}>
      <div className="map-controls" aria-label="Map controls">
        <button type="button" aria-label="Zoom in" onClick={() => zoomBy(1.4)} disabled={view.zoom >= 8}>+</button>
        <button type="button" aria-label="Zoom out" onClick={() => zoomBy(1 / 1.4)} disabled={view.zoom <= 1}>−</button>
        <button type="button" onClick={() => setView({ x: 0, y: 0, zoom: 1 })}>Reset</button>
      </div>
      <svg ref={svgRef} viewBox={`${view.x} ${view.y} ${611.85999 / view.zoom} ${695.70178 / view.zoom}`} preserveAspectRatio="xMidYMid meet" style={{ width: "100%", height, touchAction: "none", cursor: "grab" }}
        onWheel={(event) => { zoomBy(event.deltaY < 0 ? 1.15 : 1 / 1.15); }}
        onPointerDown={(event) => {
          if (event.button !== 0) return;
          moved.current = false;
          drag.current = { x: event.clientX, y: event.clientY };
        }}
        onPointerMove={(event) => {
          if (!drag.current) return;
          const dx = event.clientX - drag.current.x;
          const dy = event.clientY - drag.current.y;
          if (!moved.current && Math.hypot(dx, dy) < 4) return;
          moved.current = true;
          event.currentTarget.setPointerCapture(event.pointerId);
          const matrix = event.currentTarget.getScreenCTM();
          if (!matrix) return;
          setView((current) => ({ ...current, x: current.x - dx / matrix.a, y: current.y - dy / matrix.d }));
          drag.current = { x: event.clientX, y: event.clientY };
        }}
        onPointerUp={() => { drag.current = null; }}
        onPointerCancel={() => { drag.current = null; }}
        onLostPointerCapture={() => { drag.current = null; }}
        onClickCapture={(event) => { if (moved.current) { event.stopPropagation(); moved.current = false; } }}
        role="img" aria-label={`People located by city on India map for ${mainCriminal.name}`}>
        <image href={indiaMap} width="611.85999" height="695.70178" className="geographic-map" />
        {origin && [...groups].filter(([city]) => city !== mainCriminal.location?.city).map(([city, { point }]) => (
          <line key={city} x1={origin.x} y1={origin.y} x2={point.x} y2={point.y}
            stroke="#d93636" strokeWidth="1.5" opacity="0.55" />
        ))}
        {[...groups].map(([city, { point, people: residents }]) => (
          <g key={city} transform={`translate(${point.x} ${point.y})`}>
            <title>{city}: {residents.map((p) => p.name).join(", ")}</title>
            <circle r="4" fill={residents.some((p) => p.id === mainCriminal.id) ? "#d93636" : "#c9a463"} />
            <g transform={`scale(${labelScale})`}>
            <text x="8" y="-7" className="map-city">{city}</text>
            {residents.map((person, index) => {
              const clickable = String(person.id) !== String(mainCriminal.id) && Boolean(onNodeClick);
              const activate = () => clickable && onNodeClick(person.id);
              return <text key={person.id} x="8" y={9 + index * 15} className="map-person"
                role={clickable ? "link" : undefined} tabIndex={clickable ? 0 : undefined}
                onClick={activate} onKeyDown={(event) => {
                  if (clickable && (event.key === "Enter" || event.key === " ")) {
                    event.preventDefault();
                    activate();
                  }
                }} style={{ cursor: clickable ? "pointer" : "default" }}>
                {person.name}
              </text>;
            })}
            </g>
          </g>
        ))}
      </svg>
      {unplaced.length > 0 && <p className="map-unplaced">Location unavailable: {unplaced.join(", ")}</p>}
    </div>
  );
}

export default NetworkGraph;
