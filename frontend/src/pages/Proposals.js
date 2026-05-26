import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { ScrollText, Plus, FileText, ExternalLink } from "lucide-react";
import { proposalsAPI } from "../lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogTrigger,
} from "@/components/ui/dialog";
import { toast } from "sonner";

const DOC_TYPES = [
  { value: "grant_proposal", label: "Grant Proposal" },
  { value: "contract_proposal", label: "Contract Proposal" },
  { value: "rfp_response", label: "RFP Response" },
  { value: "capability_statement", label: "Capability Statement" },
  { value: "cover_letter", label: "Cover Letter" },
];

function DraftDialog() {
  const queryClient = useQueryClient();
  const [open, setOpen] = useState(false);
  const [form, setForm] = useState({
    doc_type: "grant_proposal",
    title: "",
    target_org: "",
    opportunity_url: "",
    deadline: "",
    budget_usd: "",
    requirements: "",
    evidence: "",
  });

  const draft = useMutation({
    mutationFn: (payload) => proposalsAPI.draft(payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["proposals"] });
      queryClient.invalidateQueries({ queryKey: ["proposalStats"] });
      toast.success("Draft generated via Gemini 3 Flash ($0 cost)");
      setOpen(false);
    },
    onError: (err) => {
      const detail = err?.response?.data?.detail || err.message;
      toast.error(`Draft failed: ${detail}`);
    },
  });

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!form.title.trim()) return toast.error("Title required");
    draft.mutate({
      doc_type: form.doc_type,
      title: form.title.trim(),
      target_org: form.target_org || null,
      opportunity_url: form.opportunity_url || null,
      deadline: form.deadline || null,
      budget_usd: form.budget_usd ? parseFloat(form.budget_usd) : null,
      requirements: form.requirements.split("\n").map((s) => s.trim()).filter(Boolean),
      evidence: form.evidence.split("\n").map((s) => s.trim()).filter(Boolean),
    });
  };

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button className="bg-green-600 hover:bg-green-700 text-white" data-testid="proposal-draft-trigger">
          <Plus className="w-4 h-4 mr-1.5" /> New Draft
        </Button>
      </DialogTrigger>
      <DialogContent className="bg-[#0f1419] border-white/10 text-white max-w-lg">
        <DialogHeader>
          <DialogTitle>Draft Proposal / Grant / RFP</DialogTitle>
          <DialogDescription className="text-gray-400 text-sm">
            AI-generated via Gemini 3 Flash (Cost Guard: $0). Edit before submitting.
          </DialogDescription>
        </DialogHeader>
        <form onSubmit={handleSubmit} className="space-y-3" data-testid="proposal-draft-form">
          <div>
            <Label>Document Type</Label>
            <select
              value={form.doc_type}
              onChange={(e) => setForm({ ...form, doc_type: e.target.value })}
              className="mt-1 w-full bg-[#171b28] border border-white/10 text-white text-sm rounded-md px-3 py-2"
              data-testid="proposal-doc-type"
            >
              {DOC_TYPES.map((t) => (
                <option key={t.value} value={t.value}>{t.label}</option>
              ))}
            </select>
          </div>
          <div>
            <Label>Title</Label>
            <Input value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })}
              className="bg-[#171b28] border-white/10 text-white" data-testid="proposal-title" required />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <Label>Target Org</Label>
              <Input value={form.target_org} onChange={(e) => setForm({ ...form, target_org: e.target.value })}
                className="bg-[#171b28] border-white/10 text-white" placeholder="agency / client" />
            </div>
            <div>
              <Label>Budget ($)</Label>
              <Input type="number" step="0.01" value={form.budget_usd}
                onChange={(e) => setForm({ ...form, budget_usd: e.target.value })}
                className="bg-[#171b28] border-white/10 text-white" placeholder="0" />
            </div>
          </div>
          <div>
            <Label>Opportunity URL</Label>
            <Input type="url" value={form.opportunity_url}
              onChange={(e) => setForm({ ...form, opportunity_url: e.target.value })}
              className="bg-[#171b28] border-white/10 text-white" placeholder="https://grants.gov/..." />
          </div>
          <div>
            <Label>Requirements (one per line)</Label>
            <textarea value={form.requirements}
              onChange={(e) => setForm({ ...form, requirements: e.target.value })}
              rows="3"
              className="w-full bg-[#171b28] border border-white/10 text-white text-sm rounded-md px-3 py-2"
              placeholder="- 5+ years past performance&#10;- NAICS 541512" />
          </div>
          <div>
            <Label>Evidence / past performance (one per line)</Label>
            <textarea value={form.evidence}
              onChange={(e) => setForm({ ...form, evidence: e.target.value })}
              rows="3"
              className="w-full bg-[#171b28] border border-white/10 text-white text-sm rounded-md px-3 py-2"
              placeholder="H&M RFID US0275 - 55 readers..." />
          </div>
          <div className="flex justify-end gap-2 pt-2">
            <Button type="button" variant="ghost" onClick={() => setOpen(false)}>Cancel</Button>
            <Button type="submit" disabled={draft.isPending}
              className="bg-green-600 hover:bg-green-700 text-white" data-testid="proposal-draft-submit">
              {draft.isPending ? "Drafting..." : "Generate Draft"}
            </Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  );
}

function InvoiceDialog() {
  const queryClient = useQueryClient();
  const [open, setOpen] = useState(false);
  const [form, setForm] = useState({
    client_name: "",
    client_email: "",
    description: "",
    quantity: "1",
    unit_price: "",
  });

  const create = useMutation({
    mutationFn: (payload) => proposalsAPI.invoice(payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["proposals"] });
      queryClient.invalidateQueries({ queryKey: ["proposalStats"] });
      toast.success("Invoice generated");
      setOpen(false);
    },
    onError: (err) => toast.error(err?.response?.data?.detail || err.message),
  });

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!form.client_name.trim() || !form.description.trim() || !form.unit_price) {
      return toast.error("Fill all required fields");
    }
    create.mutate({
      client_name: form.client_name,
      client_email: form.client_email || null,
      line_items: [{
        description: form.description,
        quantity: parseFloat(form.quantity) || 1,
        unit_price: parseFloat(form.unit_price),
      }],
    });
  };

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button variant="outline" className="border-blue-500/30 text-blue-300 hover:bg-blue-500/10"
          data-testid="invoice-trigger">
          <FileText className="w-4 h-4 mr-1.5" /> New Invoice
        </Button>
      </DialogTrigger>
      <DialogContent className="bg-[#0f1419] border-white/10 text-white max-w-md">
        <DialogHeader>
          <DialogTitle>Create Invoice</DialogTitle>
          <DialogDescription className="text-gray-400 text-sm">
            Deterministic markdown invoice - no LLM needed.
          </DialogDescription>
        </DialogHeader>
        <form onSubmit={handleSubmit} className="space-y-3" data-testid="invoice-form">
          <div>
            <Label>Client Name</Label>
            <Input value={form.client_name}
              onChange={(e) => setForm({ ...form, client_name: e.target.value })}
              className="bg-[#171b28] border-white/10 text-white" data-testid="invoice-client" required />
          </div>
          <div>
            <Label>Client Email</Label>
            <Input type="email" value={form.client_email}
              onChange={(e) => setForm({ ...form, client_email: e.target.value })}
              className="bg-[#171b28] border-white/10 text-white" />
          </div>
          <div>
            <Label>Description</Label>
            <Input value={form.description}
              onChange={(e) => setForm({ ...form, description: e.target.value })}
              className="bg-[#171b28] border-white/10 text-white" data-testid="invoice-desc" required />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <Label>Quantity</Label>
              <Input type="number" step="0.01" min="0" value={form.quantity}
                onChange={(e) => setForm({ ...form, quantity: e.target.value })}
                className="bg-[#171b28] border-white/10 text-white" />
            </div>
            <div>
              <Label>Unit Price ($)</Label>
              <Input type="number" step="0.01" min="0" value={form.unit_price}
                onChange={(e) => setForm({ ...form, unit_price: e.target.value })}
                className="bg-[#171b28] border-white/10 text-white" data-testid="invoice-price" required />
            </div>
          </div>
          <div className="flex justify-end gap-2 pt-2">
            <Button type="button" variant="ghost" onClick={() => setOpen(false)}>Cancel</Button>
            <Button type="submit" disabled={create.isPending}
              className="bg-blue-600 hover:bg-blue-700 text-white" data-testid="invoice-submit">
              {create.isPending ? "Creating..." : "Create"}
            </Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  );
}

function ProposalCard({ doc }) {
  return (
    <div
      className="bg-[rgba(23,27,40,0.5)] border border-white/5 rounded-xl p-4 hover:border-green-500/30 transition-colors"
      data-testid={`proposal-${doc.id}`}
    >
      <div className="flex items-start justify-between gap-3 mb-2">
        <div className="flex-1 min-w-0">
          <h4 className="text-sm font-semibold text-white mb-1 truncate">{doc.title}</h4>
          <div className="flex flex-wrap items-center gap-2">
            <span className="content-badge bg-purple-500/15 text-purple-300 border border-purple-500/20">
              {doc.doc_type.replace(/_/g, " ")}
            </span>
            <span className={`content-badge status-badge-${doc.status === "submitted" ? "active" : doc.status === "finalized" ? "pending" : "draft"}`}>
              {doc.status}
            </span>
            {doc.target_org && (
              <span className="text-xs text-gray-500">→ {doc.target_org}</span>
            )}
          </div>
        </div>
        {doc.metadata?.opportunity_url && (
          <a href={doc.metadata.opportunity_url} target="_blank" rel="noopener noreferrer"
            className="text-blue-400 hover:text-blue-300 text-xs inline-flex items-center gap-1">
            source <ExternalLink className="w-3 h-3" />
          </a>
        )}
      </div>
      <pre className="text-xs text-gray-400 line-clamp-3 whitespace-pre-wrap font-mono mt-2">
        {doc.content.slice(0, 320)}...
      </pre>
      <div className="text-xs text-gray-500 mt-2 pt-2 border-t border-white/5">
        {new Date(doc.created_at).toLocaleString()}
      </div>
    </div>
  );
}

export default function Proposals() {
  const { data: proposals = [] } = useQuery({
    queryKey: ["proposals"],
    queryFn: () => proposalsAPI.getAll().then((r) => r.data),
  });
  const { data: stats } = useQuery({
    queryKey: ["proposalStats"],
    queryFn: () => proposalsAPI.stats().then((r) => r.data),
  });

  const tiles = [
    { label: "Total", value: stats?.total || 0, accent: "text-blue-400" },
    { label: "Grants", value: stats?.by_type?.grant_proposal || 0, accent: "text-green-400" },
    { label: "Contracts", value: stats?.by_type?.contract_proposal || 0, accent: "text-purple-400" },
    { label: "Invoices $", value: `$${(stats?.invoice_total_usd || 0).toLocaleString()}`, accent: "text-yellow-400" },
  ];

  return (
    <div data-testid="proposals-page" className="p-6 dark-themed-page space-y-6">
      <div className="page-header flex items-center justify-between gap-4">
        <div>
          <h1>Proposals & Procurement</h1>
          <p>AI-drafted grants, contract bids, RFP responses, capability statements, and invoices.</p>
        </div>
        <div className="flex gap-2">
          <InvoiceDialog />
          <DraftDialog />
        </div>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {tiles.map((t) => (
          <div key={t.label} className="stat-card">
            <p className="text-xs text-gray-400 uppercase tracking-wider mb-2">{t.label}</p>
            <p className={`text-3xl font-bold ${t.accent}`}>{t.value}</p>
          </div>
        ))}
      </div>

      <div className="metric-card">
        <div className="flex items-center justify-between mb-6">
          <h3 className="text-lg font-semibold text-white">All Documents</h3>
          <span className="px-3 py-1 bg-green-500/20 text-green-400 rounded-full text-xs font-medium">
            {proposals.length} DOCS
          </span>
        </div>
        {proposals.length === 0 ? (
          <div className="text-center py-12">
            <ScrollText className="w-12 h-12 text-gray-500 mx-auto mb-4" />
            <p className="text-gray-300 mb-2">No documents yet</p>
            <p className="text-sm text-gray-500">
              Click <span className="text-green-400 font-medium">New Draft</span> to generate one,
              or visit <span className="text-blue-400 font-medium">Scout</span> and click Draft on a grant/contract.
            </p>
          </div>
        ) : (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-3">
            {proposals.map((doc) => (
              <ProposalCard key={doc.id} doc={doc} />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
