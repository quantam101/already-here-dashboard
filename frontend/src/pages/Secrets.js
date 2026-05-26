import { useQuery } from "@tanstack/react-query";
import { Shield, Lock, Key, AlertCircle, CheckCircle2, ExternalLink, RefreshCw } from "lucide-react";
import { Button } from "@/components/ui/button";
import { secretsAPI } from "../lib/api";

function StatusBanner({ status }) {
  if (!status) return null;
  if (status.unlocked) {
    return (
      <div className="enterprise-card border-green-500/30">
        <div className="flex items-start gap-3">
          <CheckCircle2 className="w-5 h-5 text-green-400 mt-0.5" />
          <div className="flex-1">
            <p className="text-green-300 font-medium">Bitwarden vault unlocked</p>
            <p className="text-sm text-gray-400 mt-1">
              Server: <code className="text-cyan-300 bg-black/40 px-1.5 py-0.5 rounded text-xs">{status.server}</code>
              {status.user && (
                <> · User: <code className="text-cyan-300 bg-black/40 px-1.5 py-0.5 rounded text-xs">{status.user}</code></>
              )}
            </p>
          </div>
        </div>
      </div>
    );
  }
  return (
    <div className="enterprise-card border-yellow-500/30">
      <div className="flex items-start gap-3">
        <AlertCircle className="w-5 h-5 text-yellow-400 mt-0.5" />
        <div className="flex-1">
          <p className="text-yellow-300 font-medium">
            {status.installed ? "Bitwarden CLI installed but locked" : "Bitwarden CLI not installed"}
          </p>
          <p className="text-sm text-gray-400 mt-1">
            Reason: <code className="text-gray-300">{status.reason || "unknown"}</code>
          </p>
          <SetupInstructions installed={status.installed} />
        </div>
      </div>
    </div>
  );
}

function SetupInstructions({ installed }) {
  return (
    <details className="mt-3 text-sm">
      <summary className="cursor-pointer text-cyan-300 hover:text-cyan-200">
        {installed ? "How to unlock" : "How to install + unlock"}
      </summary>
      <div className="mt-2 bg-black/40 border border-white/10 rounded-lg p-3 text-xs space-y-2 text-gray-300">
        {!installed && (
          <>
            <p className="text-white font-medium">1. Install the bw CLI on the OCI host ($0):</p>
            <pre className="text-green-400 font-mono bg-black/60 p-2 rounded overflow-x-auto">{`# Official Bitwarden CLI - free, single binary
curl -L https://vault.bitwarden.com/download/?app=cli&platform=linux -o bw.zip
unzip bw.zip && sudo mv bw /usr/local/bin/bw && sudo chmod +x /usr/local/bin/bw
bw --version`}</pre>
          </>
        )}
        <p className="text-white font-medium">{installed ? "1." : "2."} Point at your vault server:</p>
        <pre className="text-green-400 font-mono bg-black/60 p-2 rounded overflow-x-auto">{`# Bitwarden cloud (free tier):
bw config server https://vault.bitwarden.com

# OR your self-hosted Vaultwarden ($0 Docker):
bw config server https://vault.alreadyherellc.com`}</pre>
        <p className="text-white font-medium">{installed ? "2." : "3."} Login + unlock + persist session:</p>
        <pre className="text-green-400 font-mono bg-black/60 p-2 rounded overflow-x-auto">{`bw login your@email.com
echo "BW_SESSION=$(bw unlock --raw)" | sudo tee -a /opt/command-os/backend/.env
sudo docker compose -f /opt/command-os/docker-compose.yml restart backend`}</pre>
        <p className="text-gray-400 italic">
          The session token is locally scoped — does not leave your OCI host. Passwords are never sent over the wire from the backend to this page.
        </p>
      </div>
    </details>
  );
}

function ItemRow({ item }) {
  return (
    <div className="bg-[rgba(23,27,40,0.5)] border border-white/5 rounded-lg p-3 hover:border-cyan-500/30 transition-colors" data-testid={`secret-${item.id}`}>
      <div className="flex items-start justify-between gap-3">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <Key className="w-3.5 h-3.5 text-cyan-400 shrink-0" />
            <p className="text-white font-medium truncate">{item.name}</p>
          </div>
          {item.username && (
            <p className="text-xs text-gray-400 truncate">user: {item.username}</p>
          )}
          {item.uris?.length > 0 && (
            <a
              href={item.uris[0]}
              target="_blank"
              rel="noopener noreferrer"
              className="text-xs text-blue-400 hover:underline inline-flex items-center gap-1 mt-0.5 truncate"
            >
              <ExternalLink className="w-3 h-3 shrink-0" />
              <span className="truncate">{item.uris[0]}</span>
            </a>
          )}
        </div>
        <div className="flex flex-col items-end gap-1 shrink-0">
          {item.has_password && (
            <span className="content-badge bg-green-500/15 text-green-300 border border-green-500/20 text-xs">
              <Lock className="w-3 h-3 mr-1" /> pw
            </span>
          )}
          {item.has_totp && (
            <span className="content-badge bg-purple-500/15 text-purple-300 border border-purple-500/20 text-xs">
              totp
            </span>
          )}
        </div>
      </div>
    </div>
  );
}

export default function Secrets() {
  const { data: status, refetch: refetchStatus, isFetching: statusFetching } = useQuery({
    queryKey: ["secretsStatus"],
    queryFn: () => secretsAPI.status().then((r) => r.data),
  });
  const { data: itemsResp, refetch: refetchItems, isFetching: itemsFetching } = useQuery({
    queryKey: ["secretsItems"],
    queryFn: () => secretsAPI.items().then((r) => r.data),
    enabled: !!status?.unlocked,
  });
  const items = itemsResp?.items || [];

  const refresh = () => {
    refetchStatus();
    refetchItems();
  };

  return (
    <div data-testid="secrets-page" className="p-6 dark-themed-page space-y-6">
      <div className="page-header flex items-center justify-between gap-4">
        <div>
          <h1 className="flex items-center gap-2"><Shield className="w-6 h-6 text-cyan-400" />Secrets Vault</h1>
          <p>Bitwarden / Vaultwarden read-only browser · passwords stay on the host, only metadata reaches this page</p>
        </div>
        <Button
          onClick={refresh}
          disabled={statusFetching || itemsFetching}
          variant="outline"
          className="border-cyan-500/30 text-cyan-300 hover:bg-cyan-500/10"
          data-testid="secrets-refresh"
        >
          <RefreshCw className={`w-4 h-4 mr-1.5 ${(statusFetching || itemsFetching) ? "animate-spin" : ""}`} />
          Refresh
        </Button>
      </div>

      <StatusBanner status={status} />

      {status?.unlocked && (
        <div className="enterprise-card">
          <div className="flex items-center justify-between mb-3">
            <h3 className="text-base font-semibold text-white">Vault Items ({items.length})</h3>
            <span className="text-xs text-gray-500">Read-only · click to open URL</span>
          </div>
          {items.length === 0 ? (
            <p className="text-sm text-gray-400 py-6 text-center">Vault is empty.</p>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-2" data-testid="secrets-items">
              {items.map((it) => <ItemRow key={it.id} item={it} />)}
            </div>
          )}
        </div>
      )}

      <div className="enterprise-card">
        <h3 className="text-base font-semibold text-white mb-2 flex items-center gap-2">
          <Lock className="w-4 h-4 text-yellow-400" /> Why use Bitwarden here?
        </h3>
        <ul className="text-sm text-gray-300 space-y-1.5 list-disc list-inside">
          <li>Stop putting raw <code className="text-green-400 bg-black/40 px-1 rounded text-xs">STRIPE_API_KEY=sk_live_…</code> into <code className="text-green-400 bg-black/40 px-1 rounded text-xs">backend/.env</code> in plaintext</li>
          <li>Rotate secrets without redeploying — update Bitwarden item, restart backend, done</li>
          <li>Backend code can call <code className="text-green-400 bg-black/40 px-1 rounded text-xs">get_bitwarden_service().get_secret("STRIPE_API_KEY")</code> and falls back to env if vault is offline</li>
          <li>Self-host Vaultwarden in Docker on the same OCI instance = $0/month forever</li>
        </ul>
      </div>
    </div>
  );
}
