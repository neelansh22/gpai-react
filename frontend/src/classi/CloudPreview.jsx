import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import './style.css';

const API = 'https://classi-glinear-a8b5axb8cph3bbc9.westus3-01.azurewebsites.net';
const examples = {
  insurance: {
    text: 'I would like to submit an insurance claim for vehicle damage.',
    classes: [
      { id: 'claim', label: 'insurance claim', description: '' },
      { id: 'quote', label: 'insurance quote', description: '' },
      { id: 'policy', label: 'policy change', description: '' },
    ],
  },
  travel: {
    text: 'My flight was cancelled and I need to book another one.',
    classes: [
      { id: 'cancel', label: 'flight cancellation', description: '' },
      { id: 'baggage', label: 'lost baggage', description: '' },
      { id: 'refund', label: 'refund request', description: '' },
    ],
  },
  unrelated: {
    text: 'We sanded the birch shelf and glazed three mugs.',
    classes: [
      { id: 'refund', label: 'refund request', description: '' },
      { id: 'meeting', label: 'meeting reschedule', description: '' },
    ],
  },
};

function message(detail, status) {
  if (typeof detail === 'string') return detail;
  if (Array.isArray(detail)) return detail.map(item => item.msg).filter(Boolean).join('; ') || `Request failed (${status})`;
  return `Request failed (${status})`;
}

export default function CloudPreview() {
  const [key, setKey] = useState('');
  const [text, setText] = useState(examples.insurance.text);
  const [classes, setClasses] = useState(examples.insurance.classes);
  const [result, setResult] = useState(null);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);

  function loadExample(name) {
    setText(examples[name].text);
    setClasses(examples[name].classes.map(item => ({ ...item })));
    setResult(null);
    setError('');
  }

  async function submit(event) {
    event.preventDefault();
    const invalid = classes.findIndex(item => !/^[A-Za-z0-9_-]{1,50}$/.test(item.id));
    if (invalid !== -1) {
      setError(`Class ${invalid + 1} ID must contain only letters, numbers, underscores or hyphens.`);
      setResult(null);
      return;
    }
    setBusy(true);
    setError('');
    setResult(null);
    try {
      const start = performance.now();
      const response = await fetch(`${API}/v1/classify`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-Classi-Key': key },
        body: JSON.stringify({ text, classes }),
      });
      const body = await response.json().catch(() => null);
      if (!response.ok) throw new Error(message(body?.detail, response.status));
      setResult({ ...body, browser_ms: Math.round(performance.now() - start) });
    } catch (e) {
      setError(e.message === 'Failed to fetch'
        ? 'Could not reach the API. It may be starting; wait and try again.'
        : e.message);
    } finally {
      setBusy(false);
    }
  }

  return <main className="classi-service">
    <header><Link className="back-link" to="/">← Portfolio</Link><span className="brand">◈ &nbsp; classi-service</span>
      <span className="badge">RESTRICTED PREVIEW · ENGLISH</span></header>
    <section className="hero"><p className="eyebrow">DYNAMIC INTELLIGENCE / LIVE API</p>
      <h1>Give language<br /><em>somewhere to go.</em></h1>
      <p>One classifier, new labels on every request. Explore insurance, travel, or your own use case.</p>
    </section>
    <section className="card">
      <div className="section-title"><div><p className="eyebrow">THE CLASSIFIER</p><h2>Try a conversation</h2></div>
        <span className="badge">GLiNER2 · ZERO SHOT</span></div>
      <p>Restricted demo: use fictional data only. Enter the preview key privately; it stays in this page's memory until you leave or refresh. Do not share it or use a shared screen.</p>
      <div className="inline" aria-label="Example scenarios">
        <button type="button" className="secondary" disabled={busy} onClick={() => loadExample('insurance')}>Insurance</button>
        <button type="button" className="secondary" disabled={busy} onClick={() => loadExample('travel')}>Travel</button>
        <button type="button" className="secondary" disabled={busy} onClick={() => loadExample('unrelated')}>No match</button>
      </div>
      <form onSubmit={submit}>
        <label>Preview key<input type="password" value={key} required disabled={busy} autoComplete="off" onChange={e => setKey(e.target.value)} /></label>
        <label>Transcript<textarea required disabled={busy} maxLength={1000} value={text} onChange={e => setText(e.target.value)} /></label>
        <div className="section-title"><h3>Runtime classes</h3>
          <button type="button" className="secondary" disabled={busy || classes.length >= 10}
            onClick={() => setClasses([...classes, { id: '', label: '', description: '' }])}>+ Add class</button></div>
        <p>Use 2–10 unique IDs without spaces. Labels may contain spaces; descriptions are optional. Do not add ndw as a class.</p>
        {classes.map((item, index) => <div className="class-row" key={index}>
          {['id', 'label', 'description'].map(name => <input key={name}
            aria-label={`Class ${index + 1} ${name}`} placeholder={name} required={name !== 'description'} disabled={busy}
            maxLength={{ id: 50, label: 80, description: 160 }[name]} value={item[name]}
            onChange={e => setClasses(classes.map((c, i) => i === index ? { ...c, [name]: e.target.value } : c))} />)}
          <button type="button" className="secondary" aria-label={`Remove class ${index + 1}`}
            disabled={busy || classes.length <= 2} onClick={() => setClasses(classes.filter((_, i) => i !== index))}>×</button>
        </div>)}
        <button disabled={busy}>{busy ? 'Classifying…' : 'Classify transcript →'}</button>
      </form>
      {error && <p className="notice error" role="alert">{error}</p>}
      {result && <div className="result" aria-live="polite"><p className="eyebrow">RESULT</p>
        <h3>{result.label === 'ndw' ? 'ndw · no confident match' : classes.find(c => c.id === result.label)?.label || result.label}</h3>
        <p>Model call {result.model_call_ms} ms · browser round trip {result.browser_ms} ms · threshold {result.threshold}</p>
        <p>Scores are not calibrated probabilities; no-match decisions are not guaranteed.</p>
        <ul>{result.scores.map(score => <li key={score.id}>{score.id}: {score.score.toFixed(3)}</li>)}</ul>
      </div>}
    </section>
    <section className="card"><p className="eyebrow">WHAT'S NEXT</p><h2>From signals to knowledge.</h2>
      <p>The canvas, graph extraction and admin review run locally today. They are not connected to this Azure preview.</p>
      <Link to="/kg-bi" className="text-link">Explore the separate knowledge graph concept →</Link>
    </section>
    <footer>classi-service · restricted demonstration · not a compliance tool</footer>
  </main>;
}
