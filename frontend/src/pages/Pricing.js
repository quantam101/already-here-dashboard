import { useQuery, useMutation } from "@tanstack/react-query";
import { useSearchParams } from "react-router-dom";
import { useState } from "react";
import { CheckCircle2, Zap, Rocket, Share2, Copy } from "lucide-react";
import { paymentsAPI, api } from "../lib/api";
import { copyToClipboard } from "../lib/clipboard";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogTrigger,
} from "@/components/ui/dialog";
import { toast } from "sonner";

const ICONS = { starter: Zap, pro: Rocket, enterprise: CheckCircle2 };
const ACCENTS = {
  starter: "border-green-500/30 text-green-300 hover:bg-green-500/10",
  pro: "border-blue-500/30 text-blue-300 hover:bg-blue-500/10",
  enterprise: "border-purple-500/30 text-purple-300 hover:bg-purple-500/10",
};

function PriceCard({ id, pkg, onCheckout, isPending, highlighted = false }) {
  const Icon = ICONS[id] || Zap;
  const accent = ACCENTS[id] || ACCENTS.starter;
  return (
    <div
      className={`enterprise-card transition-colors flex flex-col ${
        highlighted ? "border-green-500/50 shadow-[0_0_24px_rgba(34,197,94,0.15)]" : "hover:border-green-500/30"
      }`}
      data-testid={`price-card-${id}`}
    >
      <div className="flex items-center gap-3 mb-3">
        <Icon className="w-6 h-6 text-green-400" />
        <h3 className="text-lg font-semibold text-white">{pkg.name}</h3>
      </div>
      <div className="mb-3">
        <span className="text-4xl font-bold text-white">${pkg.amount}</span>
        <span className="text-gray-400 text-sm ml-1">
          {pkg.kind === "one_time" ? "one-time" : "/ month"}
        </span>
      </div>
      <p className="text-sm text-gray-400 mb-6 flex-1">{pkg.description}</p>
      <Button
        onClick={() => onCheckout(id)}
        disabled={isPending}
        variant="outline"
        className={accent}
        data-testid={`checkout-${id}`}
      >
        {isPending ? "Redirecting..." : "Subscribe / Buy"}
      </Button>
    </div>
  );
}

export default function Pricing() {
  const [params] = useSearchParams();
  const utm = {
    utm_source: params.get("utm_source") || null,
    utm_medium: params.get("utm_medium") || null,
    utm_campaign: params.get("utm_campaign") || null,
    referrer: typeof document !== "undefined" ? document.referrer || null : null,
  };
  const presetPkg = params.get("pkg");

  const { data: packages = {} } = useQuery({
    queryKey: ["paymentPackages"],
    queryFn: () => paymentsAPI.packages().then((r) => r.data),
  });

  const checkout = useMutation({
    mutationFn: (packageId) =>
      paymentsAPI.checkout({
        package_id: packageId,
        origin_url: window.location.origin,
        ...utm,
      }),
    onSuccess: (res) => {
      const url = res.data?.url;
      if (url) window.location.href = url;
      else toast.error("No checkout URL returned");
    },
    onError: (err) => toast.error(err?.response?.data?.detail || err.message),
  });

  return (
    <div data-testid="pricing-page" className="p-6 dark-themed-page space-y-6">
      <div className="page-header flex items-center justify-between gap-4">
        <div>
          <h1>Pricing — Pay In</h1>
          <p>Every paid checkout drops into the immutable revenue ledger. Real cash, real proof of work.</p>
          {utm.utm_source && (
            <p className="text-xs text-green-400 mt-2" data-testid="utm-active">
              · UTM tracking active: source={utm.utm_source}
              {utm.utm_medium && ` · medium=${utm.utm_medium}`}
              {utm.utm_campaign && ` · campaign=${utm.utm_campaign}`}
            </p>
          )}
        </div>
        <ShareLinkDialog />
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {Object.entries(packages).map(([id, pkg]) => (
          <PriceCard
            key={id}
            id={id}
            pkg={pkg}
            highlighted={presetPkg === id}
            onCheckout={checkout.mutate}
            isPending={checkout.isPending}
          />
        ))}
      </div>

      <div className="enterprise-card">
        <h3 className="text-base font-semibold text-white mb-2">Stripe Test Mode Notice</h3>
        <p className="text-sm text-gray-400 leading-relaxed">
          The dashboard is currently using Stripe <span className="text-yellow-400">test keys</span>{" "}
          (configured by Emergent). To accept real money, replace{" "}
          <code className="text-green-400 bg-black/40 px-1.5 py-0.5 rounded">STRIPE_API_KEY</code> in
          backend <code className="text-green-400 bg-black/40 px-1.5 py-0.5 rounded">.env</code>{" "}
          with your live Stripe secret key from{" "}
          <a href="https://dashboard.stripe.com/apikeys" target="_blank" rel="noopener noreferrer"
            className="text-blue-400 hover:underline">dashboard.stripe.com/apikeys</a>.
          Test cards: <code className="text-blue-300">4242 4242 4242 4242</code> · any future expiry · any CVC.
        </p>
      </div>
    </div>
  );
}

function ShareLinkDialog() {
  const [open, setOpen] = useState(false);
  const [form, setForm] = useState({
    package_id: "starter",
    utm_source: "reddit",
    utm_medium: "post",
    utm_campaign: "launch",
  });
  const [generated, setGenerated] = useState(null);

  const generate = async () => {
    try {
      const params = new URLSearchParams({ ...form, origin_url: window.location.origin });
      const res = await api.get(`/payments/share-link?${params}`);
      setGenerated(res.data.share_url);
    } catch (err) {
      toast.error(err?.response?.data?.detail || err.message);
    }
  };

  const copy = async () => {
    const ok = await copyToClipboard(generated);
    if (ok) toast.success("Share link copied");
    else toast.error("Couldn't auto-copy — select the link and copy manually");
  };

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button variant="outline" className="border-purple-500/30 text-purple-300 hover:bg-purple-500/10"
          data-testid="share-link-trigger">
          <Share2 className="w-4 h-4 mr-1.5" /> Generate Share Link
        </Button>
      </DialogTrigger>
      <DialogContent className="bg-[#0f1419] border-white/10 text-white max-w-md">
        <DialogHeader>
          <DialogTitle>Share Link with UTM Tracking</DialogTitle>
          <DialogDescription className="text-gray-400 text-sm">
            Drop this link into Reddit / LinkedIn / DMs. Every paid sale credits the channel in Analytics → Payments.
          </DialogDescription>
        </DialogHeader>
        <div className="space-y-3">
          <div>
            <Label>Package</Label>
            <select value={form.package_id}
              onChange={(e) => setForm({ ...form, package_id: e.target.value })}
              className="mt-1 w-full bg-[#171b28] border border-white/10 text-white text-sm rounded-md px-3 py-2"
              data-testid="share-package">
              <option value="starter">starter — $49</option>
              <option value="pro">pro — $99/mo</option>
              <option value="enterprise">enterprise — $499/mo</option>
            </select>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <Label>Source</Label>
              <Input value={form.utm_source} onChange={(e) => setForm({ ...form, utm_source: e.target.value })}
                className="bg-[#171b28] border-white/10 text-white" data-testid="share-source" />
            </div>
            <div>
              <Label>Medium</Label>
              <Input value={form.utm_medium} onChange={(e) => setForm({ ...form, utm_medium: e.target.value })}
                className="bg-[#171b28] border-white/10 text-white" />
            </div>
          </div>
          <div>
            <Label>Campaign</Label>
            <Input value={form.utm_campaign} onChange={(e) => setForm({ ...form, utm_campaign: e.target.value })}
              className="bg-[#171b28] border-white/10 text-white" />
          </div>
          <Button onClick={generate} className="w-full bg-green-600 hover:bg-green-700 text-white"
            data-testid="share-generate">
            Generate Link
          </Button>
          {generated && (
            <div className="bg-black/40 border border-white/10 rounded-lg p-3 flex items-center gap-2"
              data-testid="generated-link">
              <code className="text-xs text-green-400 flex-1 truncate">{generated}</code>
              <Button size="icon" variant="ghost" onClick={copy} className="text-gray-400 hover:text-white">
                <Copy className="w-4 h-4" />
              </Button>
            </div>
          )}
        </div>
      </DialogContent>
    </Dialog>
  );
}
