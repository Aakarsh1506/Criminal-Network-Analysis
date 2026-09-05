import { useEffect, useMemo, useRef } from "react";
import CytoscapeComponent from "react-cytoscapejs";

function buildElements(mainCriminal, relations) {
  const nodes = [
    {
      data: { id: String(mainCriminal.id), label: mainCriminal.name, photo: mainCriminal.photo },
      classes: "main-node",
    },
    ...relations.map((r) => ({
      data: { id: String(r.criminal.id), label: r.criminal.name, photo: r.criminal.photo },
    })),
  ];

  const edges = relations.map((r) => ({
    data: {
      id: `e-${mainCriminal.id}-${r.criminal.id}`,
      source: String(mainCriminal.id),
      target: String(r.criminal.id),
      label: r.type,
    },
  }));

  return [...nodes, ...edges];
}

const stylesheet = [
  {
    selector: "node",
    style: {
      "background-color": "#101010",
      "background-image": "data(photo)",
      "background-fit": "cover cover",
      "border-width": 3,
      "border-color": "#c9a463",
      width: 52,
      height: 52,
      label: "data(label)",
      color: "#f2f2f2",
      "font-size": 10,
      "font-family": "IBM Plex Sans, sans-serif",
      "text-valign": "bottom",
      "text-margin-y": 8,
      "text-background-color": "#000000",
      "text-background-opacity": 0.85,
      "text-background-padding": "3px",
      "text-wrap": "none",
    },
  },
  {
    selector: ".main-node",
    style: {
      "border-color": "#d93636",
      width: 72,
      height: 72,
      "border-width": 4,
    },
  },
  {
    selector: "edge",
    style: {
      width: 2,
      "line-color": "#d93636",
      "curve-style": "bezier",
      "target-arrow-shape": "none",
      label: "data(label)",
      "font-size": 8,
      color: "#c9a463",
      "text-rotation": "autorotate",
      "text-background-color": "#000000",
      "text-background-opacity": 0.85,
      "text-background-padding": "2px",
    },
  },
];

const layout = {
  name: "cose",
  animate: false,
  padding: 40,
  nodeRepulsion: 8000,
  idealEdgeLength: 100,
};

function NetworkGraph({ mainCriminal, relations, onNodeClick, height = 480 }) {
  const cyRef = useRef(null);
  const containerRef = useRef(null);
  const elements = useMemo(() => buildElements(mainCriminal, relations), [mainCriminal, relations]);

  const registerEvents = (cy) => {
    if (cyRef.current === cy) return;
    cyRef.current = cy;
    window.cy = cy; // TEMP — remove once debugged
    cy.on("tap", "node", (evt) => {
      const id = evt.target.id();
      if (onNodeClick && id !== String(mainCriminal.id)) onNodeClick(id);
    });
  };

  useEffect(() => {
    const cy = cyRef.current;
    const container = containerRef.current;
    if (!cy || !container) return;

    const drawIfSized = () => {
      const { width, height: h } = container.getBoundingClientRect();
      if (width < 10 || h < 10) return;
      cy.resize();
      cy.layout(layout).run();
      cy.fit(undefined, 30);
    };

    const observer = new ResizeObserver(drawIfSized);
    observer.observe(container);
    drawIfSized();

    return () => observer.disconnect();
  }, [elements]);

  return (
    <div ref={containerRef} style={{ width: "100%", height: `${height}px` }}>
      <CytoscapeComponent
        elements={elements}
        layout={layout}
        stylesheet={stylesheet}
        style={{ width: "100%", height: "100%" }}
        className="network-graph"
        cy={registerEvents}
      />
    </div>
  );
}

export default NetworkGraph;