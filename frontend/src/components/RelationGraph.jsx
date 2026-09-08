import { useEffect, useRef, useState } from 'react';
import cytoscape from 'cytoscape';
import { fetchCriminalNetwork } from '../api/criminals';

const stylesheet = [
  { selector: 'node', style: {
    label: 'data(displayLabel)', width: 30, height: 30,
    'background-color': '#a99acb', 'border-width': 2, 'border-color': '#d2c2f2',
    color: '#d9e1ed', 'font-family': 'IBM Plex Sans, sans-serif', 'font-size': 11,
    'text-valign': 'bottom', 'text-margin-y': 10, 'text-wrap': 'wrap', 'text-max-width': 120,
    'text-outline-color': '#0b1018', 'text-outline-width': 3,
    'overlay-opacity': 0, 'transition-property': 'opacity, border-color, background-color', 'transition-duration': '160ms',
  } },
  { selector: 'node[kind = "Person"]', style: { width: 42, height: 42, 'background-color': '#c6a368', 'border-color': '#f5dba9' } },
  { selector: 'node[kind = "Case"]', style: { shape: 'round-rectangle', 'background-color': '#538ab4', 'border-color': '#8ac5ee' } },
  { selector: 'node[kind = "Location"]', style: { shape: 'diamond', width: 36, height: 36, 'background-color': '#469e91', 'border-color': '#8be0c9' } },
  { selector: 'node[kind = "CrimeType"]', style: { shape: 'hexagon', 'background-color': '#8c75ae', 'border-color': '#c8afe9' } },
  { selector: 'node[depth = 0]', style: {
    width: 60, height: 60, 'background-color': '#df6c64', 'border-color': '#ffb8a5', 'border-width': 3,
    'font-size': 13, 'font-weight': 600, color: '#fff0dc', 'text-margin-y': 18, 'z-index': 10,
  } },
  { selector: 'edge', style: {
    'curve-style': 'bezier', 'control-point-step-size': 45, width: 1.6,
    'line-color': '#73839a', 'target-arrow-shape': 'triangle', 'target-arrow-color': '#73839a',
    'arrow-scale': 0.7, opacity: 0.82, label: '', 'font-size': 9, color: '#f0d9b2',
    'text-rotation': 'autorotate', 'text-background-color': '#111923', 'text-background-opacity': 0.95,
    'text-background-padding': 5, 'text-background-shape': 'roundrectangle', 'overlay-opacity': 0,
  } },
  { selector: 'edge.focused, edge:selected, edge.hovered', style: { width: 2.5, 'line-color': '#d9b67a', 'target-arrow-color': '#d9b67a', opacity: 1, 'z-index': 5 } },
  { selector: 'node:selected, node.hovered', style: { 'border-color': '#ffffff', 'border-width': 3 } },
  { selector: '.muted', style: { opacity: 0.13 } },
];

// Scatter starting positions so the force simulation can form natural clusters.
// Keep the selected person fixed at the origin.
function networkElements(network) {
  const spread = Math.max(300, Math.sqrt(network.nodes.length) * 140);
  return [
    ...network.nodes.map((node) => {
      const root = node.depth === 0;
      return {
        data: node,
        position: root ? { x: 0, y: 0 } : { x: (Math.random() - 0.5) * spread, y: (Math.random() - 0.5) * spread },
        locked: root,
      };
    }),
    ...network.edges.map((edge) => ({ data: edge })),
  ];
}

function fitAroundPerson(cy) {
  const root = cy.nodes('[depth = 0]').first();
  if (root.empty()) { cy.fit(undefined, 60); return; }
  const center = root.position();
  const bounds = cy.elements().boundingBox();
  // Use symmetric bounds so fitting an uneven network still centers the person.
  const halfWidth = Math.max(60, center.x - bounds.x1, bounds.x2 - center.x);
  const halfHeight = Math.max(60, center.y - bounds.y1, bounds.y2 - center.y);
  const zoom = Math.max(cy.minZoom(), Math.min(cy.maxZoom(),
    Math.max(1, cy.width() - 100) / (2 * halfWidth),
    Math.max(1, cy.height() - 100) / (2 * halfHeight)));
  cy.viewport({ zoom, pan: { x: cy.width() / 2 - center.x * zoom, y: cy.height() / 2 - center.y * zoom } });
}

export default function RelationGraph({ mainCriminal, onNodeClick, height = 480 }) {
  const [result, setResult] = useState(null);
  const [retry, setRetry] = useState(0);
  const [selected, setSelected] = useState(null);
  const container = useRef(null);
  const cyRef = useRef(null);
  const network = result?.id === mainCriminal.id ? result.data : null;
  const error = result?.id === mainCriminal.id ? result.error : '';

  useEffect(() => {
    const controller = new AbortController();
    fetchCriminalNetwork(mainCriminal.id, { signal: controller.signal })
      .then((data) => { if (!controller.signal.aborted) setResult({ id: mainCriminal.id, data }); })
      .catch((err) => { if (!controller.signal.aborted) setResult({ id: mainCriminal.id, error: err.message }); });
    return () => controller.abort();
  }, [mainCriminal.id, retry]);

  useEffect(() => {
    if (!network || !container.current) return;
    const cy = cytoscape({
      container: container.current, elements: networkElements(network),
      style: stylesheet, layout: { name: 'preset', fit: false },
      minZoom: 0.05, maxZoom: 4, wheelSensitivity: 0.2, selectionType: 'single',
    });
    cyRef.current = cy;
    fitAroundPerson(cy);
    const forceLayout = cy.layout({
      name: 'cose', randomize: false, fit: false,
      animate: !window.matchMedia('(prefers-reduced-motion: reduce)').matches && network.nodes.length < 150,
      nodeRepulsion: () => 24000, idealEdgeLength: () => 180, componentSpacing: 180,
      nodeDimensionsIncludeLabels: true, nodeOverlap: 20, gravity: 0.4,
      stop: () => fitAroundPerson(cy),
    });
    forceLayout.run();
    cy.on('select', 'node, edge', ({ target }) => {
      setSelected(target.data());
      cy.elements().removeClass('muted focused');
      const focus = target.isNode() ? target.closedNeighborhood() : target.union(target.connectedNodes());
      focus.addClass('focused');
      cy.elements().difference(focus).addClass('muted');
    });
    cy.on('tap', (event) => {
      if (event.target === cy) {
        cy.elements().unselect().removeClass('muted focused');
        setSelected(null);
      }
    });
    cy.on('mouseover', 'node, edge', ({ target }) => { target.addClass('hovered'); cy.container().style.cursor = 'pointer'; });
    cy.on('mouseout', 'node, edge', ({ target }) => { target.removeClass('hovered'); cy.container().style.cursor = 'grab'; });
    const observer = new ResizeObserver(() => { cy.resize(); fitAroundPerson(cy); });
    observer.observe(container.current);
    return () => { observer.disconnect(); forceLayout.stop(); cy.destroy(); cyRef.current = null; };
  }, [network]);

  function inspect(id) {
    const cy = cyRef.current;
    if (!cy) return;
    cy.elements().unselect().removeClass('muted focused');
    setSelected(null);
    if (id) cy.getElementById(id).select();
  }
  function zoom(factor) {
    const cy = cyRef.current;
    if (cy) cy.zoom({ level: Math.max(cy.minZoom(), Math.min(cy.maxZoom(), cy.zoom() * factor)), renderedPosition: { x: cy.width() / 2, y: cy.height() / 2 } });
  }
  const activeSelection = network && selected && [...network.nodes, ...network.edges].find((item) => item.id === selected.id);

  return <div className="relation-graph" style={{ width: '100%', minWidth: 0, position: 'relative', padding: 12, color: '#f2f2f2' }}>
    <div role="group" aria-label="Graph controls" style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
      <button className="stamp-btn small" type="button" aria-label="Zoom in" disabled={!network} onClick={() => zoom(1.3)}>+</button>
      <button className="stamp-btn small" type="button" aria-label="Zoom out" disabled={!network} onClick={() => zoom(1 / 1.3)}>−</button>
      <button className="stamp-btn small" type="button" disabled={!network} onClick={() => { if (cyRef.current) fitAroundPerson(cyRef.current); }}>Fit</button>
    </div>
    {error ? <p role="alert" style={{ padding: '20px 0' }}>{error} <button className="stamp-btn small" type="button" onClick={() => { setResult(null); setSelected(null); setRetry((value) => value + 1); }}>Retry</button></p>
      : !network ? <p role="status" style={{ padding: '20px 0' }}>Loading relationships…</p>
      : <>
        <div ref={container} style={{ height, width: '100%' }} role="img" aria-label={`Relationship graph centered on ${mainCriminal.name}. Use the selector below to inspect nodes and links.`} />
        {network.edges.length === 0 && <p>No relationships are recorded for this person.</p>}
        {network.truncated && <p role="status">Showing the first {network.pathLimit.toLocaleString()} paths; some connections are omitted.</p>}
        
        <div aria-live="polite">{activeSelection && <div style={{ display: 'grid', gap: 8, marginTop: 12, borderTop: '1px solid #262626', paddingTop: 12, overflowWrap: 'anywhere' }}>
          <strong>{activeSelection.label}</strong>
          <span>{activeSelection.kind ? `${activeSelection.kind} · ${activeSelection.depth === 0 ? 'Selected person' : `${activeSelection.depth} graph steps away`}` : 'Recorded relationship'}</span>
          {activeSelection.personId && <span>{activeSelection.alias ? `“${activeSelection.alias}” · ` : ''}{activeSelection.personId} · {activeSelection.city || 'City unavailable'}</span>}
          {activeSelection.reason && <span>{activeSelection.reason}</span>}
          {activeSelection.provenance && <span>Source: {activeSelection.provenance}</span>}
          {activeSelection.personId && activeSelection.personId !== String(mainCriminal.id) && onNodeClick && <button className="stamp-btn small" type="button" onClick={() => onNodeClick(activeSelection.personId)}>Open profile</button>}
          <button className="stamp-btn small" type="button" onClick={() => inspect('')}>Clear selection</button>
        </div>}</div>
      </>}
  </div>;
}
