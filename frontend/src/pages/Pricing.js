import { useQuery, useMutation } from "@tanstack/react-query";
import { CheckCircle2, Zap, Rocket } from "lucide-react";
import { paymentsAPI } from "../lib/api";
import { Button } from "@/components/ui/button";
import { toast } from "sonner";

const ICONS = { starter: Zap, pro: Rocket, enterprise: CheckCircle2 };
const ACCENTS = {
  starter: "border-green-500/30 text-green-300 hover:bg-green-500/10",
  pro: "border-blue-500/30 text-blue-300 hover:bg-blue-500/10",
  enterprise: "border-purple-500/30 text-purple-300 hover:bg-purple-500/10",
};

function PriceCard({ id, pkg, onCheckout, isPending }) {
  const Icon = ICONS[id] || Zap;
  const accent = ACCENTS[id] || ACCENTS.starter;
  return (
    <div
      className="enterprise-card hover:border-green-500/30 transition-colors flex flex-col"
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
  const { data: packages = {} } = useQuery({
    queryKey: ["paymentPackages"],
    queryFn: () => paymentsAPI.packages().then((r) => r.data),
  });

  const checkout = useMutation({
    mutationFn: (packageId) =>
      paymentsAPI.checkout({ package_id: packageId, origin_url: window.location.origin }),
    onSuccess: (res) => {
      const url = res.data?.url;
      if (url) window.location.href = url;
      else toast.error("No checkout URL returned");
    },
    onError: (err) => toast.error(err?.response?.data?.detail || err.message),
  });

  return (
    <div data-testid="pricing-page" className="p-6 dark-themed-page space-y-6">
      <div className="page-header">
        <h1>Pricing — Pay In</h1>
        <p>
          Every paid checkout drops into the immutable revenue ledger. Real cash, real proof of work.
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {Object.entries(packages).map(([id, pkg]) => (
          <PriceCard
            key={id}
            id={id}
            pkg={pkg}
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
          <a
            href="https://dashboard.stripe.com/apikeys"
            target="_blank"
            rel="noopener noreferrer"
            className="text-blue-400 hover:underline"
          >
            dashboard.stripe.com/apikeys
          </a>
          . Test cards:{" "}
          <code className="text-blue-300">4242 4242 4242 4242</code> · any future expiry · any CVC.
        </p>
      </div>
    </div>
  );
}
