import React, { useState, useEffect } from 'react';

const STATUS_COLORS = {
  draft: 'bg-gray-100 text-gray-600',
  ready: 'bg-blue-100 text-blue-700',
  live: 'bg-green-100 text-green-700',
  archived: 'bg-red-100 text-red-600',
};

const TYPE_ICONS = {
  checklist: '✅',
  kit: '🧰',
  guide: '📖',
  template: '📄',
  audit: '🔍',
  ebook: '📚',
};

const BACKEND = process.env.REACT_APP_BACKEND_URL || '';

export default function ProductFactory() {
  const [products, setProducts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showModal, setShowModal] = useState(false);
  const [selected, setSelected] = useState(null);
  const [form, setForm] = useState({ title: '', product_type: 'checklist', description: '', audience: 'small business owners', price_usd: '' });

  useEffect(() => { fetchProducts(); }, []);

  async function fetchProducts() {
    setLoading(true);
    try {
      const r = await fetch(`${BACKEND}/api/products`);
      const d = await r.json();
      setProducts(d.products || d || []);
    } catch { setProducts([]); }
    setLoading(false);
  }

  async function handleCreate(e) {
    e.preventDefault();
    const r = await fetch(`${BACKEND}/api/products/create`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ ...form, price_usd: parseFloat(form.price_usd) || 0 }),
    });
    const d = await r.json();
    if (d.approval_required) {
      alert('Product saved as draft. Pricing and publishing require Stephen\'s approval.');
    }
    setShowModal(false);
    setForm({ title: '', product_type: 'checklist', description: '', audience: 'small business owners', price_usd: '' });
    fetchProducts();
  }

  return (
    <div className="p-4 max-w-5xl mx-auto">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Product Factory</h1>
          <p className="text-sm text-gray-500">Build reusable digital products — kits, checklists, guides, audits</p>
        </div>
        <button onClick={() => setShowModal(true)}
          className="bg-indigo-600 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-indigo-700">
          + New Product
        </button>
      </div>

      {/* Approval notice */}
      <div className="bg-amber-50 border border-amber-200 rounded-lg p-3 mb-4 text-sm text-amber-800">
        🔒 All products require Stephen's approval before pricing or publishing. Drafts save automatically.
      </div>

      {loading ? (
        <div className="text-center py-12 text-gray-400">Loading products...</div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {products.map(p => (
            <div key={p.id} className="bg-white rounded-xl border border-gray-200 p-4 shadow-sm hover:shadow-md transition cursor-pointer"
              onClick={() => setSelected(p)}>
              <div className="flex items-start justify-between mb-2">
                <div className="flex items-center gap-2">
                  <span className="text-xl">{TYPE_ICONS[p.product_type] || '📦'}</span>
                  <span className={`text-xs px-2 py-0.5 rounded-full font-medium capitalize ${STATUS_COLORS[p.status] || 'bg-gray-100 text-gray-600'}`}>
                    {p.status}
                  </span>
                </div>
                {p.price_usd > 0 && (
                  <span className="text-green-700 font-semibold text-sm">${p.price_usd}</span>
                )}
              </div>
              <h3 className="font-semibold text-gray-900 text-sm mb-1">{p.title}</h3>
              {p.description && <p className="text-xs text-gray-500 line-clamp-2">{p.description}</p>}
              <div className="flex items-center justify-between mt-3">
                <span className="text-xs text-gray-400 capitalize">{(p.product_type || '').replace('_', ' ')}</span>
                {p.approval_required ? (
                  <span className="text-xs text-amber-600">⚠ Needs approval</span>
                ) : (
                  <span className="text-xs text-green-600">✓ Approved</span>
                )}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Product detail modal */}
      {selected && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4" onClick={() => setSelected(null)}>
          <div className="bg-white rounded-2xl p-6 w-full max-w-lg shadow-xl" onClick={e => e.stopPropagation()}>
            <div className="flex items-center gap-2 mb-1">
              <span className="text-2xl">{TYPE_ICONS[selected.product_type] || '📦'}</span>
              <h2 className="text-lg font-bold">{selected.title}</h2>
            </div>
            <span className={`text-xs px-2 py-0.5 rounded-full font-medium capitalize ${STATUS_COLORS[selected.status]}`}>
              {selected.status}
            </span>
            {selected.description && <p className="text-sm text-gray-600 mt-3">{selected.description}</p>}
            {selected.content && <pre className="text-xs bg-gray-50 rounded p-3 mt-3 overflow-auto max-h-48">{selected.content}</pre>}
            <div className="mt-4 pt-4 border-t flex justify-between items-center">
              <span className="text-sm text-gray-500">Audience: {selected.audience}</span>
              {selected.price_usd > 0 && <span className="text-green-700 font-semibold">${selected.price_usd}</span>}
            </div>
            <button onClick={() => setSelected(null)}
              className="mt-4 w-full bg-gray-100 text-gray-700 py-2 rounded-lg text-sm hover:bg-gray-200">Close</button>
          </div>
        </div>
      )}

      {/* Create modal */}
      {showModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-2xl p-6 w-full max-w-md shadow-xl">
            <h2 className="text-lg font-bold mb-4">Create New Product</h2>
            <form onSubmit={handleCreate} className="space-y-3">
              <input required placeholder="Product title" value={form.title}
                onChange={e => setForm(f => ({ ...f, title: e.target.value }))}
                className="w-full border rounded-lg px-3 py-2 text-sm" />
              <select value={form.product_type} onChange={e => setForm(f => ({ ...f, product_type: e.target.value }))}
                className="w-full border rounded-lg px-3 py-2 text-sm">
                {Object.keys(TYPE_ICONS).map(t => <option key={t} value={t}>{t}</option>)}
              </select>
              <textarea placeholder="Description" rows={3} value={form.description}
                onChange={e => setForm(f => ({ ...f, description: e.target.value }))}
                className="w-full border rounded-lg px-3 py-2 text-sm" />
              <input placeholder="Target audience" value={form.audience}
                onChange={e => setForm(f => ({ ...f, audience: e.target.value }))}
                className="w-full border rounded-lg px-3 py-2 text-sm" />
              <input placeholder="Price (leave blank — requires approval to set)" value={form.price_usd}
                onChange={e => setForm(f => ({ ...f, price_usd: e.target.value }))} type="number" step="0.01"
                className="w-full border rounded-lg px-3 py-2 text-sm" />
              <p className="text-xs text-amber-600">⚠ Pricing requires Stephen's approval before going live.</p>
              <div className="flex gap-2 pt-1">
                <button type="submit" className="flex-1 bg-indigo-600 text-white py-2 rounded-lg text-sm font-medium hover:bg-indigo-700">
                  Save as Draft
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
