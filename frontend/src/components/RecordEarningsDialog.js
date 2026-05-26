import { useState } from "react";
import { useMutation, useQueryClient, useQuery } from "@tanstack/react-query";
import { Plus } from "lucide-react";
import { ledgerAPI, revenueAPI } from "../lib/api";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

const TODAY = () => new Date().toISOString().slice(0, 10);

const INITIAL = (defaultStreamId) => ({
  stream_id: defaultStreamId || "",
  occurred_on: TODAY(),
  gross_amount: "",
  net_amount: "",
  source: "manual",
  proof_url: "",
  notes: "",
});

export default function RecordEarningsDialog({ defaultStreamId, triggerLabel = "Record Earnings", triggerVariant = "default" }) {
  const queryClient = useQueryClient();
  const [open, setOpen] = useState(false);
  const [form, setForm] = useState(INITIAL(defaultStreamId));

  const { data: streams = [] } = useQuery({
    queryKey: ["revenueStreams"],
    queryFn: () => revenueAPI.getAll().then((r) => r.data),
    enabled: open && !defaultStreamId,
  });

  const create = useMutation({
    mutationFn: (payload) => ledgerAPI.create(payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["ledger"] });
      queryClient.invalidateQueries({ queryKey: ["ledgerProgress"] });
      queryClient.invalidateQueries({ queryKey: ["revenueStreams"] });
      queryClient.invalidateQueries({ queryKey: ["revenueStats"] });
      toast.success("Earnings recorded to ledger");
      setOpen(false);
      setForm(INITIAL(defaultStreamId));
    },
    onError: (err) => {
      const detail = err?.response?.data?.detail || err.message;
      toast.error(`Failed to record: ${detail}`);
    },
  });

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!form.stream_id) return toast.error("Pick a stream");
    const gross = parseFloat(form.gross_amount);
    const net = parseFloat(form.net_amount);
    if (Number.isNaN(gross) || Number.isNaN(net)) return toast.error("Enter valid amounts");
    if (net > gross) return toast.error("Net cannot exceed gross");
    create.mutate({
      stream_id: form.stream_id,
      occurred_on: form.occurred_on,
      gross_amount: gross,
      net_amount: net,
      source: form.source,
      proof_url: form.proof_url || null,
      notes: form.notes || null,
    });
  };

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button
          variant={triggerVariant}
          size="sm"
          className={triggerVariant === "default" ? "bg-green-600 hover:bg-green-700 text-white" : ""}
          data-testid="record-earnings-trigger"
        >
          <Plus className="w-4 h-4 mr-1.5" />
          {triggerLabel}
        </Button>
      </DialogTrigger>
      <DialogContent className="bg-[#0f1419] border-white/10 text-white max-w-md">
        <DialogHeader>
          <DialogTitle>Record Real Earnings</DialogTitle>
        </DialogHeader>
        <form onSubmit={handleSubmit} className="space-y-4" data-testid="record-earnings-form">
          {!defaultStreamId && (
            <div>
              <Label htmlFor="stream_id">Revenue Stream</Label>
              <select
                id="stream_id"
                name="stream_id"
                value={form.stream_id}
                onChange={(e) => setForm({ ...form, stream_id: e.target.value })}
                className="mt-1 w-full bg-[#171b28] border border-white/10 text-white text-sm rounded-md px-3 py-2"
                data-testid="record-earnings-stream"
                required
              >
                <option value="">Select a stream...</option>
                {streams.map((s) => (
                  <option key={s.id} value={s.id}>
                    {s.name}
                  </option>
                ))}
              </select>
            </div>
          )}
          <div className="grid grid-cols-2 gap-3">
            <div>
              <Label htmlFor="occurred_on">Date</Label>
              <Input
                id="occurred_on"
                type="date"
                value={form.occurred_on}
                onChange={(e) => setForm({ ...form, occurred_on: e.target.value })}
                className="bg-[#171b28] border-white/10 text-white"
                data-testid="record-earnings-date"
                required
              />
            </div>
            <div>
              <Label htmlFor="source">Source</Label>
              <select
                id="source"
                value={form.source}
                onChange={(e) => setForm({ ...form, source: e.target.value })}
                className="mt-1 w-full bg-[#171b28] border border-white/10 text-white text-sm rounded-md px-3 py-2"
                data-testid="record-earnings-source"
              >
                <option value="manual">manual</option>
                <option value="csv">csv import</option>
                <option value="webhook">webhook</option>
                <option value="api">api</option>
              </select>
            </div>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <Label htmlFor="gross_amount">Gross $</Label>
              <Input
                id="gross_amount"
                type="number"
                step="0.01"
                min="0"
                placeholder="0.00"
                value={form.gross_amount}
                onChange={(e) => setForm({ ...form, gross_amount: e.target.value })}
                className="bg-[#171b28] border-white/10 text-white"
                data-testid="record-earnings-gross"
                required
              />
            </div>
            <div>
              <Label htmlFor="net_amount">Net $</Label>
              <Input
                id="net_amount"
                type="number"
                step="0.01"
                min="0"
                placeholder="0.00"
                value={form.net_amount}
                onChange={(e) => setForm({ ...form, net_amount: e.target.value })}
                className="bg-[#171b28] border-white/10 text-white"
                data-testid="record-earnings-net"
                required
              />
            </div>
          </div>
          <div>
            <Label htmlFor="proof_url">Proof URL (dashboard, screenshot, csv link)</Label>
            <Input
              id="proof_url"
              type="url"
              placeholder="https://..."
              value={form.proof_url}
              onChange={(e) => setForm({ ...form, proof_url: e.target.value })}
              className="bg-[#171b28] border-white/10 text-white"
              data-testid="record-earnings-proof"
            />
          </div>
          <div>
            <Label htmlFor="notes">Notes</Label>
            <Input
              id="notes"
              placeholder="optional context"
              value={form.notes}
              onChange={(e) => setForm({ ...form, notes: e.target.value })}
              className="bg-[#171b28] border-white/10 text-white"
              data-testid="record-earnings-notes"
            />
          </div>
          <div className="flex justify-end gap-2 pt-2">
            <Button type="button" variant="ghost" onClick={() => setOpen(false)}>
              Cancel
            </Button>
            <Button
              type="submit"
              disabled={create.isPending}
              className="bg-green-600 hover:bg-green-700 text-white"
              data-testid="record-earnings-submit"
            >
              {create.isPending ? "Recording..." : "Record"}
            </Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  );
}
