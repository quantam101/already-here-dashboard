import { useMutation } from "@tanstack/react-query";
import { useSearchParams } from "react-router-dom";
import { useMemo, useState } from "react";
import { ArrowUpRight, CheckCircle2, Clock3, Handshake, Mail, Store } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { waitlistAPI } from "../lib/api";

const PROOF_THRESHOLD = "$25,000";

const INTEREST_OPTIONS = [
  { value: "trial", label: "Trial after proof" },
  { value: "build_for_percentage", label: "Build for percentage" },
  { value: "affiliate", label: "Affiliate offer" },
  { value: "pod_store", label: "POD or Etsy store" },
  { value: "service_opportunity", label: "Service opportunity" },
  { value: "other", label: "Something else" },
];

const IMMEDIATE_PATHS = [
  {
    title: "Etsy and POD",
    description: "Route buyers to Already Here LLC products while the Command OS proof ledger grows.",
    href: "https://www.etsy.com/shop/AlreadyHereLLC",
    icon: Store,
  },
  {
    title: "Fly Culture Shop",
    description: "Send traffic to the live Printify storefront while Etsy channel publishing is being connected.",
    href: "https://fly-culture-shop.printify.me",
    icon: Store,
  },
  {
    title: "Fly Design Vault",
    description: "Use the Shopify storefront as an immediate buyer destination for design-led products.",
    href: "https://flydesignvault.com",
    icon: Store,
  },
  {
    title: "Affiliate and service leads",
    description: "Capture warm demand for setup work, store builds, content systems, and approved affiliate offers.",
    href: "/growth-vault",
    icon: Handshake,
  },
  {
    title: "Proof ledger",
    description: "Use verified revenue as the unlock condition before selling Command OS trials or installs.",
    href: "/proof-of-work",
    icon: CheckCircle2,
  },
];

export default function Pricing() {
  const [params] = useSearchParams();
  const [form, setForm] = useState({
    email: "",
    name: "",
    company: "",
    role: "",
    interest: params.get("interest") || "trial",
    message: "",
  });

  const tracking = useMemo(() => ({
    source: "pricing_waitlist",
    utm_source: params.get("utm_source") || "",
    utm_medium: params.get("utm_medium") || "",
    utm_campaign: params.get("utm_campaign") || "proof_first",
    referrer: typeof document !== "undefined" ? document.referrer || "" : "",
  }), [params]);

  const signup = useMutation({
    mutationFn: () => waitlistAPI.create({ ...form, ...tracking }),
    onSuccess: (res) => {
      toast.success(res.data?.message || "You're on the waitlist");
      setForm((current) => ({ ...current, email: "", message: "" }));
    },
    onError: (err) => toast.error(err?.response?.data?.detail || err.message),
  });

  const update = (field) => (event) => {
    setForm((current) => ({ ...current, [field]: event.target.value }));
  };

  const submit = (event) => {
    event.preventDefault();
    signup.mutate();
  };

  return (
    <div data-testid="pricing-page" className="p-6 dark-themed-page space-y-6">
      <div className="page-header flex flex-col gap-3 md:flex-row md:items-end md:justify-between">
        <div>
          <div className="flex items-center gap-2 text-amber-300 text-sm font-semibold mb-2">
            <Clock3 className="w-4 h-4" />
            Proof-first launch
          </div>
          <h1>Waitlist Before Pricing</h1>
          <p>
            Command OS is not for sale until verified proof of work passes {PROOF_THRESHOLD}. Join the list for
            future trials, build-for-percentage work, affiliate paths, or store-building opportunities.
          </p>
        </div>
        <a
          href="/proof-of-work"
          className="inline-flex items-center gap-2 text-sm text-green-300 hover:text-green-200"
        >
          View proof ledger <ArrowUpRight className="w-4 h-4" />
        </a>
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-[1.15fr_0.85fr] gap-6">
        <form onSubmit={submit} className="enterprise-card space-y-5" data-testid="waitlist-form">
          <div>
            <h2 className="text-xl font-semibold text-white mb-1">Raise your hand</h2>
            <p className="text-sm text-gray-400">
              This records demand only. It does not charge a card or promise a paid offer before proof is earned.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <Label>Email</Label>
              <Input
                type="email"
                required
                value={form.email}
                onChange={update("email")}
                placeholder="you@example.com"
                className="bg-[#171b28] border-white/10 text-white"
                data-testid="waitlist-email"
              />
            </div>
            <div>
              <Label>Name</Label>
              <Input
                value={form.name}
                onChange={update("name")}
                placeholder="Your name"
                className="bg-[#171b28] border-white/10 text-white"
              />
            </div>
            <div>
              <Label>Company</Label>
              <Input
                value={form.company}
                onChange={update("company")}
                placeholder="Optional"
                className="bg-[#171b28] border-white/10 text-white"
              />
            </div>
            <div>
              <Label>Role</Label>
              <Input
                value={form.role}
                onChange={update("role")}
                placeholder="Founder, operator, creator..."
                className="bg-[#171b28] border-white/10 text-white"
              />
            </div>
          </div>

          <div>
            <Label>What do you want to explore?</Label>
            <select
              value={form.interest}
              onChange={update("interest")}
              className="mt-1 w-full bg-[#171b28] border border-white/10 text-white text-sm rounded-md px-3 py-2"
              data-testid="waitlist-interest"
            >
              {INTEREST_OPTIONS.map((option) => (
                <option key={option.value} value={option.value}>{option.label}</option>
              ))}
            </select>
          </div>

          <div>
            <Label>Context</Label>
            <textarea
              value={form.message}
              onChange={update("message")}
              placeholder="Tell us what you want built, promoted, automated, or monetized."
              className="mt-1 min-h-[120px] w-full rounded-md bg-[#171b28] border border-white/10 text-white text-sm px-3 py-2 outline-none focus:border-emerald-500"
              data-testid="waitlist-message"
            />
          </div>

          <Button
            type="submit"
            disabled={signup.isPending}
            className="bg-green-600 hover:bg-green-700 text-white"
            data-testid="waitlist-submit"
          >
            <Mail className="w-4 h-4 mr-2" />
            {signup.isPending ? "Joining..." : "Join waitlist"}
          </Button>
        </form>

        <div className="space-y-4">
          <div className="enterprise-card border-amber-500/30">
            <h2 className="text-lg font-semibold text-white mb-2">Sales rule</h2>
            <p className="text-sm text-gray-400 leading-relaxed">
              No Command OS checkout, install package, or paid trial is offered here until verified revenue crosses
              {` ${PROOF_THRESHOLD}`}. The Stripe pipe stays available for approved offers, but this page is a lead
              capture funnel until proof exists.
            </p>
          </div>

          {IMMEDIATE_PATHS.map((path) => {
            const Icon = path.icon;
            return (
              <a
                key={path.title}
                href={path.href}
                className="enterprise-card block hover:border-green-500/40 transition-colors"
              >
                <div className="flex items-start gap-3">
                  <Icon className="w-5 h-5 text-green-400 mt-0.5" />
                  <div>
                    <h3 className="text-base font-semibold text-white">{path.title}</h3>
                    <p className="text-sm text-gray-400 mt-1">{path.description}</p>
                  </div>
                </div>
              </a>
            );
          })}
        </div>
      </div>
    </div>
  );
}
