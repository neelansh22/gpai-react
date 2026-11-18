import React, { useCallback, useEffect, useState } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { ReactFlow, Background, Controls, MiniMap, useNodesState, useEdgesState } from '@xyflow/react';
import '@xyflow/react/dist/style.css';
import './style.css';
import CloudPreview from './CloudPreview';

const API = import.meta.env.VITE_CLASSI_API || (import.meta.env.DEV ? 'http://127.0.0.1:8000' : '');

async function request(path, options = {}) {
  if (!API) throw new Error('API endpoint is not configured for this deployment');
  const response = await fetch(API + path, {
    ...options,
    headers: { 'Content-Type': 'application/json', ...options.headers },
  });
  if (!response.ok) {
    const body = await response.json().catch(() => null);
    const details = Array.isArray(body?.detail) ? body.detail.map(item => {
      if (typeof item?.msg !== 'string') return '';
      const location = Array.isArray(item.loc) ? item.loc.filter(part => part !== 'body').map((part, index, parts) =>
        typeof part === 'number' && parts[index - 1] === 'classes' ? `class ${part + 1}` : part
      ).filter(part => part !== 'classes').join(' ') : '';
      return location ? `${location}: ${item.msg}` : item.msg;
    }).filter(Boolean).join('; ') : '';
    throw new Error(typeof body?.detail === 'string' ? body.detail : details || `Request failed (${response.status})`);
  }
  return response.json();
}

export default function App() {
  return import.meta.env.PROD || import.meta.env.VITE_CLASSI_PREVIEW === 'cloud'
    ? <CloudPreview /> : <LocalApp />;
}

function LocalApp() {
  const { pathname } = useLocation();
  const page = pathname.split('/')[2] || 'overview';
  const [telemetry, setTelemetry] = useState(null);
  const [telemetryError, setTelemetryError] = useState('');
  const [graphText, setGraphText] = useState('');
  const [graphConsent, setGraphConsent] = useState(false);
  const [text, setText] = useState('The parcel arrived at the depot this morning.');
  const [classes, setClasses] = useState([
    { id: 'arrival', label: 'shipment arrival', description: 'A shipment arrives at a location.' },
    { id: 'delay', label: 'shipment delay', description: 'A shipment is running late.' },
    { id: 'refund', label: 'refund request', description: 'A customer asks for a refund.' },
  ]);
  const [consent, setConsent] = useState(false);
  const [result, setResult] = useState(null);
  const [job, setJob] = useState(null);
  const [jobError, setJobError] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [token, setToken] = useState('');
  const [credentials, setCredentials] = useState({ username: '', password: '' });
  const [submissions, setSubmissions] = useState([]);
  const [submission, setSubmission] = useState(null);
  const [graph, setGraph] = useState({ nodes: [], edges: [] });
  const [nodes, setNodes, onNodesChange] = useNodesState([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState([]);
  const [selected, setSelected] = useState(null);
  const [search, setSearch] = useState('');
  const [nodeForm, setNodeForm] = useState({ label: '', type: '', description: '' });
  const [edgeForm, setEdgeForm] = useState({ source: '', target: '', label: '', description: '' });
  const auth = { Authorization: `Bearer ${token}` };

  useEffect(() => {
    if (page !== 'performance') return undefined;
    let active = true;
    async function refresh() {
      try {
        const data = await request('/v1/metrics');
        if (active) { setTelemetry(data); setTelemetryError(''); }
      } catch (e) { if (active) setTelemetryError(e.message); }
    }
    refresh();
    const timer = setInterval(refresh, 5000);
    return () => { active = false; clearInterval(timer); };
  }, [page]);

  const refreshGraph = useCallback(async () => {
    try {
      const data = await request('/v1/graph');
      setGraph(data);
      setNodes(data.nodes.map((n, i) => ({
        id: n.id, data: { label: `${n.label} · ${n.type}` },
        position: { x: (i % 4) * 230, y: Math.floor(i / 4) * 140 },
      })));
      setEdges(data.edges.map(e => ({ id: e.id, source: e.source, target: e.target, label: e.label })));
    }
    catch (e) { setError(e.message); }
  }, [setNodes, setEdges]);

  useEffect(() => { refreshGraph(); }, [refreshGraph]);
  const visibleNodes = nodes.filter(n => n.data.label.toLowerCase().includes(search.toLowerCase()));
  const visibleIds = new Set(visibleNodes.map(n => n.id));
  const visibleEdges = edges.filter(e => visibleIds.has(e.source) && visibleIds.has(e.target));

  const jobId = job?.id;
  const jobState = job?.state;
  const jobToken = job?.status_token;
  useEffect(() => {
    if (!jobId || !['queued', 'running'].includes(jobState)) return undefined;
    const timer = setInterval(async () => {
      try {
        const status = await request(`/v1/graph/jobs/${jobId}`, { headers: { 'X-Job-Token': jobToken } });
        setJob(previous => ({ ...previous, ...status }));
      } catch (e) { setJobError(e.message); clearInterval(timer); }
    }, 2000);
    return () => clearInterval(timer);
  }, [jobId, jobState, jobToken]);

  async function classify(event) {
    event.preventDefault();
    const invalidId = classes.findIndex(c => !/^[A-Za-z0-9_-]{1,50}$/.test(c.id));
    if (invalidId !== -1) {
      setError(`Class ${invalidId + 1} ID must be 1–50 letters, numbers, underscores or hyphens, with no spaces.`);
      setResult(null);
      return;
    }
    setBusy(true); setError(''); setJobError(''); setResult(null); setJob(null);
    try {
      const start = performance.now();
      const answer = await request('/v1/classify', { method: 'POST', body: JSON.stringify({ text, classes }) });
      setResult({ ...answer, browser_ms: Math.round(performance.now() - start) });
      setBusy(false);
      if (consent) {
        try {
          setJob(await request('/v1/graph/submissions', {
            method: 'POST', body: JSON.stringify({ text, consent: true }),
          }));
        } catch (e) { setJobError(`Graph submission failed: ${e.message}`); }
      }
    } catch (e) { setError(e.message); setBusy(false); }
  }

  async function submitGraph(event) {
    event.preventDefault(); setJobError(''); setJob(null);
    try {
      setJob(await request('/v1/graph/submissions', {
        method: 'POST', body: JSON.stringify({ text: graphText, consent: graphConsent }),
      }));
      setGraphText(''); setGraphConsent(false);
    } catch (e) { setJobError(`Graph submission failed: ${e.message}`); }
  }

  async function loadSubmissions(currentToken = token) {
    setSubmissions(await request('/v1/admin/submissions', { headers: { Authorization: `Bearer ${currentToken}` } }));
  }
  async function login(event) {
    event.preventDefault(); setError('');
    try {
      const answer = await request('/v1/admin/login', { method: 'POST', body: JSON.stringify(credentials) });
      setToken(answer.token); setCredentials({ username: '', password: '' });
      await loadSubmissions(answer.token);
    } catch (e) { setError(e.message); }
  }
  async function inspectSubmission(id) {
    try { setSubmission(await request(`/v1/admin/submissions/${id}`, { headers: auth })); }
    catch (e) { setError(e.message); }
  }
  async function review(decision) {
    try {
      await request(`/v1/admin/submissions/${submission.id}/review?decision=${decision}`, { method: 'POST', headers: auth });
      await loadSubmissions(); await inspectSubmission(submission.id);
    } catch (e) { setError(e.message); }
  }
  async function saveNode(event) {
    event.preventDefault();
    try {
      const editing = selected?.kind === 'node';
      await request(editing ? `/v1/admin/nodes/${selected.item.id}` : '/v1/admin/nodes', {
        method: editing ? 'PUT' : 'POST', headers: auth,
        body: JSON.stringify({ ...nodeForm, job_id: editing ? null : submission?.id || null }),
      });
      setNodeForm({ label: '', type: '', description: '' }); setSelected(null); await refreshGraph();
    } catch (e) { setError(e.message); }
  }
  async function saveEdge(event) {
    event.preventDefault();
    try {
      const editing = selected?.kind === 'edge';
      await request(editing ? `/v1/admin/edges/${selected.item.id}` : '/v1/admin/edges', {
        method: editing ? 'PUT' : 'POST', headers: auth,
        body: JSON.stringify({ ...edgeForm, job_id: editing ? null : submission?.id || null }),
      });
      setEdgeForm({ source: '', target: '', label: '', description: '' }); setSelected(null); await refreshGraph();
    } catch (e) { setError(e.message); }
  }
  function select(kind, item) {
    setSelected({ kind, item });
    if (kind === 'node') setNodeForm({ label: item.label, type: item.type, description: item.description });
    else setEdgeForm({ source: item.source, target: item.target, label: item.label, description: item.description });
  }
  async function removeSelected() {
    if (!selected || !window.confirm(`Delete this ${selected.kind}? Deleting a node also deletes its links.`)) return;
    try {
      await request(`/v1/admin/${selected.kind === 'node' ? 'nodes' : 'edges'}/${selected.item.id}`, { method: 'DELETE', headers: auth });
      setSelected(null); await refreshGraph();
    } catch (e) { setError(e.message); }
  }
  async function inspectProvenance() {
    try {
      const path = selected.kind === 'node' ? 'nodes' : 'edges';
      const provenance = await request(`/v1/admin/provenance/${path}/${selected.item.id}`, { headers: auth });
      if (provenance.submission) setSubmission(provenance.submission);
      else setError('This graph item was created manually without a linked submission.');
    } catch (e) { setError(e.message); }
  }
  const field = (value, update, placeholder, required = true) => (
    <input required={required} aria-label={placeholder} placeholder={placeholder} value={value}
      onChange={event => update(event.target.value)} />
  );

  return <main className="classi-service">
    <header><Link className="back-link" to="/">← Portfolio</Link><span className="brand">◈ &nbsp; classi-service</span><nav aria-label="Main navigation">
      {[['overview', 'Overview'], ['performance', 'Performance'], ['graph', 'Knowledge graph'], ['admin', 'Admin']].map(([id, label]) =>
        <Link key={id} to={`/classi/${id}`} aria-current={page === id ? 'page' : undefined}>{label}</Link>)}</nav><span className="badge">LOCAL DEMO · ENGLISH</span></header>
    {page === 'overview' && <><section className="hero"><p className="eyebrow">DYNAMIC INTELLIGENCE / 01</p>
      <h1>Give language<br /><em>somewhere to go.</em></h1>
      <p>Define your own classes. Explore the connections. Keep a human in the loop.</p>
    </section></>}
    {error && <div role="alert" className="notice error">{error}</div>}
    {page === 'overview' && <section className="card"><div className="section-title"><div><p className="eyebrow">THE CLASSIFIER</p><h2>Classify a conversation</h2></div><span className="badge">GLiNER2 · ZERO SHOT</span></div>
      <form onSubmit={classify}>
        <label>Transcript<textarea required maxLength={1000} value={text} onChange={e => setText(e.target.value)} /></label>
        <div className="section-title"><h3>Runtime classes</h3><button type="button" className="secondary" disabled={classes.length >= 10} onClick={() => setClasses([...classes, { id: '', label: '', description: '' }])}>+ Add class</button></div>
        <p>Use 2–10 classes. IDs are unique short keys without spaces (e.g. refund); labels can contain spaces. Descriptions are optional: update or clear them when changing a label. Do not add ndw as a class.</p>
        {classes.map((c, i) => <div className="class-row" key={i}>
          {['id', 'label', 'description'].map(name => <React.Fragment key={name}>{field(c[name], value => setClasses(classes.map((item, index) => index === i ? { ...item, [name]: value } : item)), name, name !== 'description')}</React.Fragment>)}
          <button type="button" className="secondary" disabled={classes.length <= 2} onClick={() => setClasses(classes.filter((_, index) => index !== i))} aria-label={`Remove class ${i + 1}`}>×</button>
        </div>)}
        <label className="check"><input type="checkbox" checked={consent} onChange={e => setConsent(e.target.checked)} /> Also submit this transcript for graph extraction and admin review. The full transcript is stored locally until deleted; do not submit sensitive information.</label>
        <button disabled={busy}>{busy ? 'Classifying…' : 'Classify transcript →'}</button>
      </form>
      {result && <div className="result" aria-live="polite"><p className="eyebrow">RESULT</p><h3>{result.label === 'ndw' ? 'ndw · no confident match' : classes.find(c => c.id === result.label)?.label || result.label}</h3>
        <p>Model call {result.model_call_ms} ms · browser round trip {result.browser_ms} ms · threshold {result.threshold}</p>
        <p>Scores are not calibrated probabilities. The default threshold is provisional and may misclassify unrelated text.</p>
        <ul>{result.scores.map(s => <li key={s.id}>{s.id}: {s.score.toFixed(3)}</li>)}</ul></div>}
      {job && <p className="notice" role="status">Graph job: <strong>{job.state}</strong>{job.error ? ` · ${job.error}` : ''}. Classification is independent of graph processing.</p>}
      {jobError && <p role="alert" className="notice error">{jobError}</p>}
    </section>}
    {page === 'performance' && <section className="page-section"><p className="eyebrow">SERVICE / LIVE MONITOR</p><h1>Performance &amp; health.</h1><p>Measurements from this local API process. No transcripts are collected for metrics.</p>
      {telemetryError && <p className="notice error" role="alert">API unavailable: {telemetryError}</p>}
      {telemetry ? <><div className="metric-grid">
        <div className="card metric"><p className="eyebrow">MODEL READINESS</p><strong>{telemetry.model_ready ? 'Ready' : 'Loading / unavailable'}</strong><p>API process uptime {telemetry.uptime_seconds}s</p></div>
        <div className="card metric"><p className="eyebrow">SERVICE P50</p><strong>{telemetry.service_p50_ms == null ? '—' : `${telemetry.service_p50_ms} ms`}</strong><p>Handler time · {telemetry.latency_samples} samples</p></div>
        <div className="card metric"><p className="eyebrow">SERVICE P95</p><strong>{telemetry.service_p95_ms == null ? '—' : `${telemetry.service_p95_ms} ms`}</strong><p>Excludes network round trip</p></div>
        <div className="card metric"><p className="eyebrow">CLASSIFICATIONS</p><strong>{telemetry.classifications_succeeded}</strong><p>{telemetry.classifications_failed} handler failures since start</p></div>
      </div><div className="card"><h2>Graph processing</h2><p>Queued: {telemetry.graph_jobs.queued} · Running: {telemetry.graph_jobs.running} · Completed: {telemetry.graph_jobs.completed} · Failed: {telemetry.graph_jobs.failed}</p><p>{telemetry.scope}. Counters reset on API restart; validation failures before the handler are not included. Graph jobs persist in SQLite. Separate worker liveness is not currently measured.</p><Link className="text-link" to="/classi/admin">Submit a transcript for graph review →</Link></div></> : !telemetryError && <p>Loading metrics…</p>}
    </section>}
    {page === 'graph' && <section className="card graph-section page-section"><div className="section-title"><div><p className="eyebrow">KNOWLEDGE / 02</p><h2>Connections, in context.</h2><p>Only explicitly published graph items appear here. Model suggestions need human review.</p></div><span className="badge">REVIEWED GRAPH</span></div>
      <div className="graph-grid"><aside><label>Filter graph<input value={search} onChange={e => setSearch(e.target.value)} placeholder="Search nodes" /></label>
        <p className="eyebrow">NODES · {graph.nodes.length}</p>
        {graph.nodes.filter(n => `${n.label} ${n.type}`.toLowerCase().includes(search.toLowerCase())).map(n => <button className="list-item" key={n.id} onClick={() => select('node', n)}>{n.label} <small>{n.type}</small></button>)}
        <p className="eyebrow">LINKS · {graph.edges.length}</p>
        {graph.edges.map(e => <button className="list-item" key={e.id} onClick={() => select('edge', e)}>{e.label}</button>)}
      </aside>
      <div className="canvas" aria-label="Interactive knowledge graph. Use the node and link lists for keyboard access.">
        <ReactFlow nodes={visibleNodes} edges={visibleEdges} onNodesChange={onNodesChange} onEdgesChange={onEdgesChange}
          onNodeClick={(_, n) => select('node', graph.nodes.find(item => item.id === n.id))}
          onEdgeClick={(_, e) => select('edge', graph.edges.find(item => item.id === e.id))}
          nodesConnectable={false} fitView><Background /><Controls /><MiniMap pannable zoomable /></ReactFlow>
        {!graph.nodes.length && <div className="empty">No published graph items yet.<br />Sign in to review submissions and create nodes.</div>}
      </div>
      <aside><p className="eyebrow">INSPECTOR</p>{selected ? <><h3>{selected.item.label}</h3><p>{selected.item.type || 'Relationship'}</p><p>{selected.item.description || 'No description.'}</p>{token && <><button className="secondary" onClick={inspectProvenance}>Open private evidence</button><button className="secondary" onClick={removeSelected}>Delete selected</button></>}</> : <p>Select a node or link to inspect its metadata.</p>}</aside></div>
    </section>}
    {page === 'admin' && <section className="card page-section"><div className="section-title"><div><p className="eyebrow">CURATION / 03</p><h2>Admin workspace</h2></div><span className="badge">{token ? 'SIGNED IN' : 'PRIVATE'}</span></div>
      {!token ? <form onSubmit={login} className="inline">{field(credentials.username, value => setCredentials({ ...credentials, username: value }), 'Username')}{<input aria-label="Password" placeholder="Password" type="password" required value={credentials.password} onChange={e => setCredentials({ ...credentials, password: e.target.value })} />}<button>Sign in</button></form>
        : <><div className="inline"><button className="secondary" onClick={async () => { try { await request('/v1/admin/logout', { method: 'POST', headers: auth }); setToken(''); setSubmission(null); setSubmissions([]); } catch (e) { setError(e.message); } }}>Sign out</button><button className="secondary" onClick={() => loadSubmissions().catch(e => setError(e.message))}>Refresh queue</button></div>
          <p className="notice">Review carefully before publishing: graph labels and descriptions are public and may contain sensitive information. Model output is a suggestion, not a fact.</p>
          <form onSubmit={submitGraph}><h3>Turn a transcript into graph candidates</h3><label>Transcript<textarea required maxLength={1000} value={graphText} onChange={e => setGraphText(e.target.value)} /></label>
            <label className="check"><input type="checkbox" required checked={graphConsent} onChange={e => setGraphConsent(e.target.checked)} /> I consent to retaining this transcript locally for extraction and admin review.</label>
            <button>Queue graph extraction →</button></form>
          {job && <p className="notice" role="status">Graph job: {job.state}{job.error ? ` · ${job.error}` : ''}. Refresh the review queue when completed.</p>}
          {jobError && <p className="notice error" role="alert">{jobError}</p>}
          <div className="admin-grid"><div><h3>Submissions</h3>{submissions.map(s => <button className="list-item" key={s.id} onClick={() => inspectSubmission(s.id)}>{s.id.slice(0, 8)} · {s.state} · {s.review_state || 'awaiting extraction'}</button>)}</div>
            <div>{submission ? <><h3>Private evidence</h3><p>{submission.transcript}</p><p>Status: {submission.state} · {submission.review_state}</p>
              {submission.result && <><p className="eyebrow">ENTITY SUGGESTIONS · SELECT TO EDIT BEFORE PUBLISHING</p>
                {Object.entries(submission.result.entities.entities).flatMap(([type, items]) => items.map((item, index) =>
                  <button type="button" className="list-item" key={`${type}-${index}`} onClick={() => {
                    setSelected(null); setNodeForm({ label: item.text, type, description: '' });
                  }}>{item.text} <small>{type} · score {item.confidence.toFixed(2)} · characters {item.start}–{item.end}</small></button>))}
                <details><summary>Inspect raw model output</summary><pre>{JSON.stringify(submission.result, null, 2)}</pre></details>
              </>}
              {submission.result && <div className="inline"><button className="secondary" onClick={() => review('reviewed')}>Mark reviewed</button><button className="secondary" onClick={() => review('rejected')}>Reject</button></div>}
              <button className="secondary" onClick={async () => { if (!window.confirm('Delete transcript, job and associated published graph items?')) return; try { await request(`/v1/admin/submissions/${submission.id}`, { method: 'DELETE', headers: auth }); setSubmission(null); await loadSubmissions(); await refreshGraph(); } catch (e) { setError(e.message); } }}>Delete submission</button>
            </> : <p>Select a submission to review its evidence and suggestions.</p>}</div></div>
          <div className="admin-grid"><form onSubmit={saveNode}><h3>{selected?.kind === 'node' ? 'Edit node' : 'Publish a node'}</h3>{field(nodeForm.label, value => setNodeForm({ ...nodeForm, label: value }), 'Node label')}{field(nodeForm.type, value => setNodeForm({ ...nodeForm, type: value }), 'Node type')}{field(nodeForm.description, value => setNodeForm({ ...nodeForm, description: value }), 'Description', false)}<button>Save node</button></form>
            <form onSubmit={saveEdge}><h3>{selected?.kind === 'edge' ? 'Edit link' : 'Publish a link'}</h3>
              {['source', 'target'].map(name => <select required aria-label={name} key={name} value={edgeForm[name]} onChange={e => setEdgeForm({ ...edgeForm, [name]: e.target.value })}><option value="">Select {name}</option>{graph.nodes.map(n => <option key={n.id} value={n.id}>{n.label}</option>)}</select>)}
              {field(edgeForm.label, value => setEdgeForm({ ...edgeForm, label: value }), 'Relationship')}{field(edgeForm.description, value => setEdgeForm({ ...edgeForm, description: value }), 'Description', false)}<button>Save link</button></form></div>
          {selected && <button className="secondary" onClick={() => { setSelected(null); setNodeForm({ label: '', type: '', description: '' }); setEdgeForm({ source: '', target: '', label: '', description: '' }); }}>Cancel editing</button>}
        </>}
    </section>}
    <footer>classi-service · local proof of concept · not a compliance tool</footer>
  </main>;
}
