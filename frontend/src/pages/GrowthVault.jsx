import React, { useState, useEffect } from 'react';

const CATEGORIES = ['all', 'tool', 'product_idea', 'opportunity', 'prompt', 'template', 'resource'];
const CATEGORY_COLORS = {
  tool: 'bg-blue-100 text-blue-800',
  product_idea: 'bg-purple-100 text-purple-800',
  opportunity: 'bg-green-100 text-green-800',
  prompt: 'bg-yellow-100 text-yellow-800',
  template: 'bg-orange-100 text-orange-800',
  resource: 'bg-gray-100 text-gray-800',
};

const BACKEND = process.env.REACT_APP_BACKEND_URL || '';

export default function GrowthVault() {
  const [entries, setEntries] = useState([]);
  const [filter, setFilter] = useState('all');
  const [loading, setLoading] = useState(true);
  const [showModal, setShowModal] = useState(false);
  const [distilling, setDistilling] = useState(false);
  const [form, setForm] = useState({ title: '', description: '', category: 'tool', source_url: '', tags: '' });

  useEffect(() => { fetchEntries(); }, [filter]);

  async function fetchEntries() {
    setLoading(true);
    try {
      const q = filter !== 'all' ? `?category=${filter}` : '';
      const r = await fetch(`${BACKEND}/api/growth-vault${q}`);
      const d = await r.json();
      setEntries(d.entries || d || []);
    } catch { setEntries([]); }
    setLoading(false);
  }

  async function handleCapture(e) {
    e.preventDefault();
    await fetch(`${BACKEND}/api/growth-vault/capture`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(form),
    });
    setShowModal(false);
    setForm({ title: '', description: '', category: 'tool', source_url: '', tags: '' });
    fetchEntries();
  }

  async function handleDistill() {
    if (!form.source_url && !form.description) return;
    setDistilling(true);
    try {
      const r = await fetch(`${BACKEND}/api/growth-vault/distill`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ url: form.source_url, text: form.description }),
      });
      const d = await r.json();
      if (d.title) setForm(f => ({ ...f, title: d.title, description: d.summary || f.description, tags: d.tags || f.tags }));
    } catch {}
    setDistilling(false);
  }

  const stars = (n) => '★'.repeat(Math.min(5, Math.max(0, n))) + '☆'.repeat(5 - Math.min(5, Math.max(0, n)));

  return (
    <div className="p-4 max-w-5xl mx-auto">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Growth Vault</h1>
          <p className="text-sm text-gray-500">Capture tools, ideas, and opportunities before they slip away</p>
        </div>
        <button onClick={() => setShowModal(true)}
          className="bg-indigo-600 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-indigo-700">
          + Capture Idea
        </button>
      </div>

      {/* Category filter */}
      <div className="flex gap-2 mb-4 flex-wrap">
        {CATEGORIES.map(c => (
          <button key={c} onClick={() => setFilter(c)}
            className={`px-3 py-1 rounded-full text-sm font-medium capitalize ${filter === c ? 'bg-indigo-600 text-white' : 'bg-gray-100 text-gray-600 hover:bg-gray-200'}`}>
            {c.replace('_', ' ')}
          </button>
        ))}
      </div>

      {/* Entries grid */}
      {loading ? (
        <div className="text-center py-12 text-gray-400">Loading vault...</div>
      ) : entries.length === 0 ? (
        <div className="text-center py-12 text-gray-400">
          <p className="text-lg">Vault is empty</p>
          <p className="text-sm mt-1">Capture your first idea to get started</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {entries.map(e => (
            <div key={e.id} className="bg-white rounded-xl border border-gray-200 p-4 shadow-sm hover:shadow-md transition">
              <div className="flex items-start justify-between mb-2">
                <span className={`text-xs px-2 py-0.5 rounded-full font-medium capitalize ${CATEGORY_COLORS[e.category] || 'bg-gray-100 text-gray-600'}`}>
                  {(e.category || '').replace('_', ' ')}
                </span>
                <span className="text-yellow-500 text-xs">{stars(e.value_score || 0)}</span>
              </div>
              <h3 className="font-semibold text-gray-900 text-sm mb-1">{e.title}</h3>
              {e.description && <p className="text-xs text-gray-500 line-clamp-2 mb-2">{e.description}</p>}
              {e.monetization_angle && (
                <p className="text-xs text-green-700 bg-green-50 px-2 py-1 rounded mt-2">💰 {e.monetization_angle}</p>
              )}
              {e.source_url && (
                <a href={e.source_url} target="_blank" rel="noreferrer"
                  className="text-xs text-indigo-500 hover:underline mt-1 block truncate">{e.source_url}</a>
              )}
            </div>
          ))}
        </div>
      )}

      {/* Capture modal */}
      {showModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-2xl p-6 w-full max-w-md shadow-xl">
            <h2 className="text-lg font-bold mb-4">Capture to Growth Vault</h2>
            <form onSubmit={handleCapture} className="space-y-3">
              <input required placeholder="Title" value={form.title}
                onChange={e => setForm(f => ({ ...f, title: e.target.value }))}
                className="w-full border rounded-lg px-3 py-2 text-sm" />
              <textarea placeholder="Description" rows={3} value={form.description}
                onChange={e => setForm(f => ({ ...f, description: e.target.value }))}
                className="w-full border rounded-lg px-3 py-2 text-sm" />
              <select value={form.category} onChange={e => setForm(f => ({ ...f, category: e.target.value }))}
                className="w-full border rounded-lg px-3 py-2 text-sm">
                {CATEGORIES.filter(c => c !== 'all').map(c => (
                  <option key={c} value={c}>{c.replace('_', ' ')}</option>
                ))}
              </select>
              <div className="flex gap-2">
                <input placeholder="Source URL (optional)" value={form.source_url}
                  onChange={e => setForm(f => ({ ...f, source_url: e.target.value }))}
                  className="flex-1 border rounded-lg px-3 py-2 text-sm" />
                <button type="button" onClick={handleDistill} disabled={distilling}
                  className="bg-purple-100 text-purple-700 px-3 py-2 rounded-lg text-sm font-medium hover:bg-purple-200 disabled:opacity-50">
                  {distilling ? '...' : 'AI Distill'}
                </button>
              </div>
              <input placeholder="Tags (comma-separated)" value={form.tags}
                onChange={e => setForm(f => ({ ...f, tags: e.target.value }))}
                className="w-full border rounded-lg px-3 py-2 text-sm" />
              <div className="flex gap-2 pt-2">
                <button type="submit" className="flex-1 bg-indigo-600 text-white py-2 rounded-lg text-sm font-medium hover:bg-indigo-700">
                  Save to Vault
                </button>
                <button type="button" onClick={() => setShowModal(false)}
                  className="flex-1 bg-gray-100 text-gray-700 py-2 rounded-lg text-sm font-medium hover:bg-gray-200">
                  Cancel
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
