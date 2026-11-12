import { useRef, useState } from "react";
import { Link } from "react-router-dom";
import { ArrowLeft, ArrowRight, AudioLines, Check, ChevronRight, CircleHelp, Database, Eye, GitBranch, Layers3, Network, RotateCcw, ShieldCheck, X } from "lucide-react";
import { cases, edges, nodes } from "./data";
import "./style.css";

const types = ["Product", "Symptom", "Diagnostic", "Component", "Action", "Outcome"];
const nodeById = Object.fromEntries(nodes.map((node) => [node.id, node]));
const caseById = Object.fromEntries(cases.map((item) => [item.id, item]));

function Graph({ selection, onSelect, statuses, hiddenTypes }) {
  const visibleNodes = nodes.filter((node) => !hiddenTypes.includes(node.type));
  const visibleIds = new Set(visibleNodes.map((node) => node.id));
  const visibleEdges = edges.filter((edge) => visibleIds.has(edge.from) && visibleIds.has(edge.to) && statuses[edge.id] !== "rejected");

  return (
    <div className="kg-graph-scroll">
      <svg className="kg-graph" viewBox="0 0 820 570" role="group" aria-label="Interactive knowledge graph. Select an entity or relationship to inspect evidence.">
        <defs>
          <pattern id="kg-grid" width="25" height="25" patternUnits="userSpaceOnUse"><circle cx="1" cy="1" r="1" fill="#42566d" opacity=".55" /></pattern>
        </defs>
        <rect width="820" height="570" fill="url(#kg-grid)" />
        {visibleEdges.map((edge) => {
          const from = nodeById[edge.from];
          const to = nodeById[edge.to];
          const selected = selection.kind === "edge" && selection.id === edge.id;
          return (
            <g key={edge.id} className={`kg-edge ${selected ? "is-selected" : ""} ${statuses[edge.id] === "proposed" ? "is-proposed" : ""}`}
              role="button" tabIndex="0" aria-label={`${from.label} ${edge.label} ${to.label}, ${statuses[edge.id]}`}
              onClick={() => onSelect({ kind: "edge", id: edge.id })} onKeyDown={(event) => {
                if (event.key === "Enter" || event.key === " ") { event.preventDefault(); onSelect({ kind: "edge", id: edge.id }); }
              }}>
              <line className="kg-edge-hit" x1={from.x} y1={from.y} x2={to.x} y2={to.y} />
              <line className="kg-edge-line" x1={from.x} y1={from.y} x2={to.x} y2={to.y} />
              <circle cx={(from.x + to.x) / 2} cy={(from.y + to.y) / 2} r="9" className="kg-edge-dot" />
              <text x={(from.x + to.x) / 2} y={(from.y + to.y) / 2 + 3} textAnchor="middle" className="kg-edge-plus">+</text>
            </g>
          );
        })}
        {visibleNodes.map((node) => (
          <g key={node.id} className={`kg-node kg-node-${node.type.toLowerCase()} ${selection.kind === "node" && selection.id === node.id ? "is-selected" : ""}`}
            transform={`translate(${node.x},${node.y})`} role="button" tabIndex="0" aria-label={`${node.type}: ${node.label}`}
            onClick={() => onSelect({ kind: "node", id: node.id })} onKeyDown={(event) => {
              if (event.key === "Enter" || event.key === " ") { event.preventDefault(); onSelect({ kind: "node", id: node.id }); }
            }}>
            <circle className="kg-node-halo" r="53" />
            <circle className="kg-node-disc" r="32" />
            <circle className="kg-node-core" r="7" />
            <rect x="-85" y="44" width="170" height="42" rx="8" className="kg-node-label-bg" />
            <text textAnchor="middle" y="61" className="kg-node-name">{node.label}</text>
            <text textAnchor="middle" y="75" className="kg-node-type">{node.type.toUpperCase()}</text>
          </g>
        ))}
      </svg>
    </div>
  );
}

function App() {
  const [selection, setSelection] = useState({ kind: "node", id: "warning" });
  const [statuses, setStatuses] = useState(() => Object.fromEntries(edges.map((edge) => [edge.id, edge.status])));
  const [hiddenTypes, setHiddenTypes] = useState([]);
  const [caseId, setCaseId] = useState("CS-1042");
  const transcriptRef = useRef(null);
  const selectedNode = selection.kind === "node" ? nodeById[selection.id] : null;
  const selectedEdge = selection.kind === "edge" ? edges.find((edge) => edge.id === selection.id) : null;
  const source = selectedEdge ? caseById[selectedEdge.caseId] : caseById[caseId];
  const proposedCount = Object.values(statuses).filter((status) => status === "proposed").length;
  const visibleEdgeCount = edges.filter((edge) => statuses[edge.id] !== "rejected" && !hiddenTypes.includes(nodeById[edge.from].type) && !hiddenTypes.includes(nodeById[edge.to].type)).length;

  function select(item) {
    setSelection(item);
    if (item.kind === "edge") {
      setCaseId(edges.find((edge) => edge.id === item.id).caseId);
    }
  }

  function toggleType(type) {
    setHiddenTypes((current) => current.includes(type) ? current.filter((value) => value !== type) : [...current, type]);
  }

  function review(status) {
    setStatuses((current) => ({ ...current, [selectedEdge.id]: status }));
    if (status === "rejected") setSelection({ kind: "node", id: selectedEdge.from });
  }

  function reset() {
    setStatuses(Object.fromEntries(edges.map((edge) => [edge.id, edge.status])));
    setHiddenTypes([]);
    setSelection({ kind: "node", id: "warning" });
    setCaseId("CS-1042");
  }

  return (
    <div className="kgbi">
      <header className="kg-header">
        <div className="kg-header-inner">
          <Link to="/" className="kg-back"><ArrowLeft size={15} /> <span>Portfolio</span></Link>
          <div className="kg-brand"><span className="kg-brand-icon"><Network size={20} /></span><span>kg-bi<small>GRAPH WORKSPACE</small></span></div>
          <div className="kg-header-right"><span className="kg-live-dot" /> SYNTHETIC DATA <span className="kg-header-divider" /> <span>AUTOMOTIVE SUPPORT</span></div>
        </div>
      </header>

      <main className="kg-main">
        <section className="kg-hero">
          <div className="kg-eyebrow"><span /> KNOWLEDGE GRAPH / AUTOMOTIVE SUPPORT</div>
          <h1>Conversation intelligence</h1>
          <p>Explore a sample graph of support conversations, diagnostic findings, attempted repairs and outcomes. Select a node or relationship to inspect its evidence.</p>
          <div className="kg-hero-note"><ShieldCheck size={15} /> Fictional examples <span /> Curated graph · no live extraction</div>
        </section>

        <section className="kg-flow" aria-label="Illustrative workflow">
          {[
            { icon: AudioLines, n: "01", name: "Conversations", detail: "Transcripts & outcomes" },
            { icon: Layers3, n: "02", name: "Identify", detail: "Entities & patterns" },
            { icon: Eye, n: "03", name: "Review", detail: "Human in the loop" },
            { icon: Network, n: "04", name: "Connect", detail: "Evidence-backed graph" },
            { icon: Database, n: "05", name: "Remember", detail: "Context for agents" },
          ].map(({ icon: Icon, n, name, detail }, index) => (
            <div className="kg-flow-step" key={n}><div className="kg-flow-icon"><Icon size={17} /></div><div><span className="kg-flow-number">{n} /</span><strong>{name}</strong><small>{detail}</small></div>{index < 4 && <ChevronRight className="kg-flow-arrow" size={15} />}</div>
          ))}
        </section>

        <div className="kg-section-title">
          <div><div className="kg-eyebrow"><span /> WORKSPACE</div><h2>Support knowledge graph</h2><p>Filter entities, inspect source evidence and review proposed links.</p></div>
          <div className="kg-sample-badge"><span /> INTERACTIVE SAMPLE</div>
        </div>

        <section className="kg-workspace" aria-label="Knowledge graph workspace">
          <div className="kg-workspace-bar">
            <div><span className="kg-workspace-icon"><GitBranch size={16} /></span><strong>Support knowledge graph</strong><span className="kg-separator" /><span>Automotive / Sample workspace</span></div>
            <button type="button" onClick={reset} className="kg-reset"><RotateCcw size={14} /> Reset sample</button>
          </div>
          <div className="kg-workspace-layout">
            <aside className="kg-sidebar">
              <div className="kg-side-label">YOUR LENS <CircleHelp size={13} /></div>
              <h3>Entity types</h3><p>Choose what appears in the graph.</p>
              <div className="kg-type-list">
                {types.map((type) => <button key={type} className="kg-type-toggle" type="button" aria-pressed={!hiddenTypes.includes(type)} onClick={() => toggleType(type)}><span className={`kg-type-dot kg-type-${type.toLowerCase()}`} /><span>{type}</span><span className={`kg-checkbox ${hiddenTypes.includes(type) ? "" : "checked"}`}>{!hiddenTypes.includes(type) && <Check size={11} />}</span></button>)}
              </div>
              <div className="kg-sidebar-bottom"><ShieldCheck size={16} /><div><strong>Privacy by design</strong><p>Sample data is fictional. No conversations are uploaded or processed.</p></div></div>
            </aside>
            <div className="kg-canvas">
              <div className="kg-canvas-top"><div><span>GRAPH VIEW</span><strong>Connections, in context</strong></div><div className="kg-canvas-count">{nodes.length - nodes.filter((node) => hiddenTypes.includes(node.type)).length} ENTITIES <i /> {visibleEdgeCount} LINKS</div></div>
              <Graph selection={selection} onSelect={select} statuses={statuses} hiddenTypes={hiddenTypes} />
              <div className="kg-canvas-bottom"><span><span className="kg-legend-line" /> Confirmed example</span><span><span className="kg-legend-line proposed" /> Proposed relationship</span><span className="kg-canvas-tip">Select a node or link to explore <ArrowRight size={13} /></span></div>
            </div>
            <aside className="kg-inspector" aria-live="polite">
              <div className="kg-side-label">INSPECTOR <span>01</span></div>
              {selectedNode ? <>
                <span className={`kg-inspector-tag kg-tag-${selectedNode.type.toLowerCase()}`}>{selectedNode.type}</span>
                <h3>{selectedNode.label}</h3>
                <p className="kg-inspector-copy">{selectedNode.description}</p>
                <div className="kg-inspector-rule" />
                <div className="kg-inspector-heading"><span>MENTIONED IN</span><span>{selectedNode.cases.length} CASES</span></div>
                {selectedNode.cases.map((id) => <button className={`kg-case-link ${caseId === id ? "active" : ""}`} type="button" key={id} onClick={() => setCaseId(id)}><span><strong>{caseById[id].title}</strong><small>{id} · {caseById[id].outcome}</small></span><ChevronRight size={15} /></button>)}
                <div className="kg-inspector-hint">Select a connection in the graph to review its supporting evidence.</div>
              </> : <>
                <span className={`kg-status kg-status-${statuses[selectedEdge.id]}`}>{statuses[selectedEdge.id]}</span>
                <h3>{nodeById[selectedEdge.from].label} <ArrowRight size={16} /> {nodeById[selectedEdge.to].label}</h3>
                <p className="kg-relation-name">{selectedEdge.label}</p>
                <div className="kg-inspector-rule" />
                <div className="kg-inspector-heading"><span>SUPPORTING EVIDENCE</span><span>{source.id}</span></div>
                <blockquote>“{selectedEdge.quote}”</blockquote>
                <button className="kg-source-link" type="button" onClick={() => transcriptRef.current?.scrollIntoView({ behavior: "smooth", block: "start" })}>View source conversation <ArrowRight size={14} /></button>
                {statuses[selectedEdge.id] === "proposed" && <div className="kg-review"><p>Review this suggested connection</p><div><button type="button" onClick={() => review("confirmed")}><Check size={14} /> Confirm</button><button type="button" onClick={() => review("rejected")}><X size={14} /> Reject</button></div></div>}
                <div className="kg-inspector-hint">This relationship is an illustrative, case-specific claim—not proof of a general cause.</div>
              </>}
            </aside>
          </div>
          <div className="kg-workspace-footer"><span><span className="kg-live-dot" /> {proposedCount} CONNECTION{proposedCount === 1 ? "" : "S"} AWAITING REVIEW</span><span>CHANGES ARE TEMPORARY · RESET ANY TIME</span></div>
        </section>

        <section className="kg-bottom-grid">
          <div className="kg-transcript" ref={transcriptRef}>
            <div className="kg-card-heading"><div><span className="kg-mini-icon"><AudioLines size={17} /></span><div><span className="kg-overline">THE SOURCE MATERIAL</span><h3>Conversation evidence</h3></div></div><span className="kg-synthetic">SYNTHETIC</span></div>
            <div className="kg-case-tabs">{cases.map((item) => <button key={item.id} type="button" className={source.id === item.id ? "active" : ""} onClick={() => { setCaseId(item.id); setSelection({ kind: "node", id: "warning" }); }}>{item.id}</button>)}</div>
            <div className="kg-conversation"><div className="kg-conversation-head"><div><strong>{source.title}</strong><span>{source.category} · {source.outcome}</span></div><span>TRANSCRIPT EXCERPT</span></div>{source.excerpt.split("\n").map((line) => { const [speaker, ...words] = line.split(": "); return <p key={speaker}><b>{speaker}</b>{words.join(": ")}</p>; })}</div>
          </div>
          <div className="kg-memory">
            <div className="kg-memory-icon"><Database size={19} /></div><span className="kg-overline">FUTURE CAPABILITY</span>
            <h3>Agent working memory</h3>
            <p>A future agent could retrieve relevant cases and relationships with their supporting evidence. This demo does not provide an agent or memory API.</p>
            <div className="kg-memory-footer">CONCEPT ONLY <ArrowRight size={16} /></div>
          </div>
        </section>
        <footer className="kg-footer"><span><Network size={15} /> kg-bi <span> / </span> CONCEPT DEMO</span><span>ILLUSTRATIVE GRAPH · SYNTHETIC DATA · NO LIVE AI PROCESSING</span></footer>
      </main>
    </div>
  );
}

export default App;
