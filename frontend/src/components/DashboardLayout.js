import { Outlet, NavLink, useLocation } from "react-router-dom";
import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { motion } from "framer-motion";
import QuickstartWizard from "./QuickstartWizard";
import CatchAndCorrectPanel from "./CatchAndCorrectPanel";
import GovernanceStatusBadges from "./GovernanceStatusBadges";
import { TakeTourButton } from "./FirstRunWalkthrough";
import {
  LayoutDashboard,
  DollarSign,
  FileText,
  Bot,
  Package,
  Rocket,
  Shield,
  TrendingUp,
  Link as LinkIcon,
  Sparkles,
  Trophy,
  Radar,
  ScrollText,
  BookOpen,
  BarChart3,
  CreditCard,
  Shield as ShieldIcon,
  Menu,
  X,
  Film,
  Radio,
  Network,
  Briefcase,
  Zap,
} from "lucide-react";

const NAVIGATION = [
  { name: "Command Center", path: "/overview", icon: LayoutDashboard, section: "operations" },
  { name: "Analytics", path: "/analytics", icon: BarChart3, section: "operations" },
  { name: "Income Streams", path: "/revenue", icon: DollarSign, section: "operations" },
  { name: "AI Agents", path: "/agents", icon: Bot, section: "operations" },
  { name: "Content Factory", path: "/studio", icon: Sparkles, section: "operations" },
  { name: "Video Engine", path: "/video-studio", icon: Film, section: "operations" },
  { name: "Voice Lab", path: "/voice-lab", icon: Radio, section: "operations" },
  { name: "D-ASI Matrix", path: "/dasi-matrix", icon: Network, section: "operations", highlight: true },
  { name: "Cash Command", path: "/cash-command", icon: Zap, section: "operations", highlight: true },
  { name: "Work Orders", path: "/work-orders", icon: Briefcase, section: "operations" },
  { name: "Scout", path: "/scout", icon: Radar, section: "operations" },
  { name: "Proof of Work", path: "/proof-of-work", icon: Trophy, section: "revenue" },
  { name: "Pricing & Pay In", path: "/pricing", icon: CreditCard, section: "revenue" },
  { name: "Proposals", path: "/proposals", icon: ScrollText, section: "revenue" },
  { name: "Books & Audiobooks", path: "/books", icon: BookOpen, section: "revenue" },
  { name: "Content Library", path: "/content", icon: FileText, section: "revenue" },
  { name: "Build Registry", path: "/builds", icon: TrendingUp, section: "revenue" },
  { name: "Deployments", path: "/deployments", icon: Package, section: "revenue" },
  { name: "Approval Queue", path: "/approvals", icon: LinkIcon, section: "revenue" },
  { name: "Audit Log", path: "/audit", icon: Rocket, section: "system" },
  { name: "Secrets Vault", path: "/secrets", icon: ShieldIcon, section: "system" },
  { name: "LGAC Monitor", path: "/audit", icon: Shield, section: "system" },
];

const SECTIONS = ["operations", "revenue", "system"];
const SECTION_LABELS = { operations: "Operations", revenue: "Revenue", system: "System" };

function NavSection({ title, items, pathname, onLinkClick }) {
  return (
    <div className="mb-5">
      <div className="text-gray-600 text-xs font-semibold uppercase tracking-widest mb-1.5 px-3">
        {title}
      </div>
      {items.map((item) => {
        const Icon = item.icon;
        const isActive = pathname === item.path || pathname.startsWith(item.path + "/");
        const isSovereign = item.highlight;
        return (
          <NavLink
            key={`${item.name}-${item.path}`}
            to={item.path}
            onClick={onLinkClick}
            className={`sidebar-link ${isActive ? "active" : ""} ${isSovereign ? "sovereign-link" : ""}`}
            data-testid={`nav-${item.name.toLowerCase().replace(/\s+/g, "-")}`}
          >
            <Icon className="w-4 h-4 flex-shrink-0" />
            <span className="text-sm flex-1">{item.name}</span>
            {isSovereign && (
              <span className="text-xs font-bold px-1.5 py-0.5 rounded"
                style={{ background: "rgba(99,102,241,0.2)", color: "#a5b4fc", fontSize: "0.6rem", letterSpacing: "0.08em" }}>
                AI
              </span>
            )}
          </NavLink>
        );
      })}
    </div>
  );
}

function SidebarFooter() {
  const { data: sovereign } = useQuery({
    queryKey: ["sovereignStatus"],
    queryFn: () => sovereignAPI.status().then((r) => r.data),
    refetchInterval: 60_000,
    retry: false,
  });

  const { data: progress } = useQuery({
    queryKey: ["ledgerProgress"],
    queryFn: () => ledgerAPI.progress().then((r) => r.data),
    refetchInterval: 120_000,
    retry: false,
  });

  const allOk = !sovereign || Object.values(sovereign.agents || {}).every((a) => a.last_success !== false);
  const pct = Math.min(100, progress?.progress_pct ?? 0);

  return (
    <div className="mt-auto pt-4 space-y-3">
      {/* Revenue unlock mini-bar */}
      {pct > 0 && (
        <div className="px-3">
          <div className="flex justify-between text-xs text-gray-500 mb-1">
            <span>$25K Unlock</span>
            <span className="text-green-400 font-semibold">{pct.toFixed(1)}%</span>
          </div>
          <div className="h-1.5 rounded-full" style={{ background: "rgba(255,255,255,0.06)" }}>
            <motion.div
              className="h-full rounded-full"
              style={{ background: "linear-gradient(90deg, #22c55e, #16a34a)" }}
              initial={{ width: 0 }}
              animate={{ width: `${pct}%` }}
              transition={{ duration: 1.2, ease: "easeOut" }}
            />
          </div>
        </div>
      )}

      {/* System status card */}
      <div className="mx-3 p-3 rounded-xl" style={{ background: "rgba(255,255,255,0.03)", border: "1px solid rgba(255,255,255,0.06)" }}>
        <div className="flex items-center gap-2 mb-1.5">
          <span className={allOk ? "live-dot" : "w-2 h-2 rounded-full bg-yellow-400 inline-block"} />
          <span className="text-xs font-semibold text-gray-300">
            {allOk ? "All Systems Operational" : "System Degraded"}
          </span>
        </div>
        {sovereign?.sovereign?.priority_action && (
          <p className="text-xs text-gray-500 line-clamp-2 leading-tight">
            <Zap className="w-2.5 h-2.5 inline mr-0.5 text-indigo-400" />
            {sovereign.sovereign.priority_action}
          </p>
        )}
        <div className="text-xs text-green-400 mt-1.5">$0/month fixed cost</div>
      </div>
    </div>
  );
}

export default function DashboardLayout() {
  const location = useLocation();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [wizardKey, setWizardKey] = useState(0);

  const navGroups = useMemo(() => {
    const groups = {};
    SECTIONS.forEach((s) => { groups[s] = NAVIGATION.filter((item) => item.section === s); });
    return groups;
  }, []);

  const closeMobileMenu = () => setMobileMenuOpen(false);

  return (
    <div className="dashboard-layout">
      {/* ── Desktop sidebar ── */}
      <aside className="hidden lg:flex flex-col border-r overflow-y-auto"
        style={{ background: "#080d18", borderColor: "rgba(255,255,255,0.05)" }}>
        <div className="px-4 py-5">
          {/* Brand */}
          <div className="flex items-center gap-3 mb-6">
            <div className="w-9 h-9 rounded-xl flex items-center justify-center"
              style={{ background: "linear-gradient(135deg, #22c55e, #16a34a)", boxShadow: "0 0 16px rgba(34,197,94,0.3)" }}>
              <span className="text-white font-bold text-base">A</span>
            </div>
            <div>
              <h1 className="text-white font-bold text-base leading-tight" style={{ fontFamily: "Space Grotesk" }} data-testid="dashboard-title">
                Already Here
              </h1>
              <p className="text-gray-600 text-xs">Command OS · v2.0 · LIVE</p>
            </div>
          </div>

          <nav data-testid="sidebar-nav">
            {SECTIONS.map((s) => (
              <NavSection key={s} title={SECTION_LABELS[s]} items={navGroups[s]} pathname={location.pathname} />
            ))}
          </nav>
        </div>

        <SidebarFooter />

        <div className="mt-auto pt-6" data-testid="sidebar-info">
          <div className="p-3 border border-gray-700 rounded-lg" style={{ background: 'rgba(31, 41, 55, 0.5)' }}>
            <div className="flex items-center gap-2 mb-2">
              <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse"></div>
              <span className="text-xs font-semibold text-gray-300">System Status</span>
            </div>
            <div className="text-xs text-gray-400">All services operational</div>
            <div className="text-xs text-green-400 mt-1">$0/month cost</div>
            <GovernanceStatusBadges />
            <button
              onClick={() => {
                window.localStorage.removeItem("ah_quickstart_completed_v1");
                if (window.ahOpenQuickstart) window.ahOpenQuickstart();
                else setWizardKey((k) => k + 1);
              }}
              className="mt-3 w-full text-xs text-green-300 hover:text-green-200 border border-green-500/20 rounded px-2 py-1.5 hover:bg-green-500/10 transition-colors"
              data-testid="sidebar-quickstart-trigger"
            >
              Re-open Quickstart
            </button>
            <div className="mt-2 flex justify-center">
              <TakeTourButton />
            </div>
          </div>
        </div>
      </aside>

      {/* ── Mobile top bar ── */}
      <div className="lg:hidden fixed top-0 left-0 right-0 border-b z-40 px-4 py-3"
        style={{ background: "#080d18", borderColor: "rgba(255,255,255,0.05)" }}>
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-lg flex items-center justify-center"
              style={{ background: "linear-gradient(135deg, #22c55e, #16a34a)" }}>
              <span className="text-white font-bold text-sm">A</span>
            </div>
            <h1 className="text-white font-bold" style={{ fontFamily: "Space Grotesk" }}>Already Here</h1>
          </div>
          <button onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
            className="p-2 hover:bg-white/5 rounded-lg text-gray-400" data-testid="mobile-menu-toggle">
            {mobileMenuOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
          </button>
        </div>
      </div>

      {/* ── Mobile drawer ── */}
      {mobileMenuOpen && (
        <div className="lg:hidden fixed inset-0 z-30 overflow-y-auto pt-16"
          style={{ background: "#080d18" }} data-testid="mobile-sidebar">
          <div className="px-4 py-5">
            {SECTIONS.map((s) => (
              <NavSection key={s} title={SECTION_LABELS[s]} items={navGroups[s]} pathname={location.pathname} onLinkClick={closeMobileMenu} />
            ))}
          </div>
        </div>
      )}

      <main className="min-h-screen mt-16 lg:mt-0 overflow-x-hidden" data-testid="main-content">
        <Outlet />
      </main>
      <QuickstartWizard key={wizardKey} />
      <CatchAndCorrectPanel />
    </div>
  );
}