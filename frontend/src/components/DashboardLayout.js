import { Outlet, NavLink, useLocation } from "react-router-dom";
import { useMemo, useState } from "react";
import QuickstartWizard from "./QuickstartWizard";
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
} from "lucide-react";

const NAVIGATION = [
  { name: "Command Center", path: "/overview", icon: LayoutDashboard, section: "operations" },
  { name: "Analytics", path: "/analytics", icon: BarChart3, section: "operations" },
  { name: "Income Streams", path: "/revenue", icon: DollarSign, section: "operations" },
  { name: "AI Agents", path: "/agents", icon: Bot, section: "operations" },
  { name: "Content Factory", path: "/studio", icon: Sparkles, section: "operations" },
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

function NavSection({ title, items, pathname, onLinkClick }) {
  return (
    <div className="mb-6">
      <div className="text-gray-500 text-xs font-semibold uppercase tracking-wider mb-2 px-3">
        {title}
      </div>
      {items.map((item) => {
        const Icon = item.icon;
        const isActive = pathname === item.path;
        return (
          <NavLink
            key={`${item.name}-${item.path}`}
            to={item.path}
            onClick={onLinkClick}
            className={`sidebar-link ${isActive ? "active" : ""}`}
            data-testid={`nav-${item.name.toLowerCase().replace(/\s+/g, '-')}`}
          >
            <Icon className="w-4 h-4" />
            <span className="text-sm">{item.name}</span>
          </NavLink>
        );
      })}
    </div>
  );
}

export default function DashboardLayout() {
  const location = useLocation();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [wizardKey, setWizardKey] = useState(0);

  // Memoize grouped navigation to prevent re-computation on every render
  const navGroups = useMemo(() => {
    const groups = {};
    SECTIONS.forEach((section) => {
      groups[section] = NAVIGATION.filter((item) => item.section === section);
    });
    return groups;
  }, []);

  const closeMobileMenu = () => setMobileMenuOpen(false);

  return (
    <div className="dashboard-layout">
      <aside className="hidden lg:block border-r border-gray-800 px-5 py-6" style={{ background: '#0f1419' }}>
        <div className="mb-8">
          <div className="flex items-center gap-3 mb-2">
            <div className="w-10 h-10 bg-gradient-to-br from-blue-500 to-blue-600 rounded-lg flex items-center justify-center">
              <span className="text-white font-bold text-lg">P</span>
            </div>
            <div>
              <h1 className="text-white font-bold text-lg" style={{ fontFamily: 'Space Grotesk' }} data-testid="dashboard-title">
                ProfitEngine
              </h1>
              <p className="text-gray-500 text-xs">v5.0x · PRODUCTION · VHLL</p>
            </div>
          </div>
        </div>

        <nav className="space-y-1" data-testid="sidebar-nav">
          <NavSection title="Operations" items={navGroups.operations} pathname={location.pathname} />
          <NavSection title="Revenue" items={navGroups.revenue} pathname={location.pathname} />
          <NavSection title="System" items={navGroups.system} pathname={location.pathname} />
        </nav>

        <div className="mt-auto pt-6" data-testid="sidebar-info">
          <div className="p-3 border border-gray-700 rounded-lg" style={{ background: 'rgba(31, 41, 55, 0.5)' }}>
            <div className="flex items-center gap-2 mb-2">
              <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse"></div>
              <span className="text-xs font-semibold text-gray-300">System Status</span>
            </div>
            <div className="text-xs text-gray-400">All services operational</div>
            <div className="text-xs text-green-400 mt-1">$0/month cost</div>
            <button
              onClick={() => {
                window.localStorage.removeItem("ah_quickstart_completed_v1");
                setWizardKey((k) => k + 1);
              }}
              className="mt-3 w-full text-xs text-green-300 hover:text-green-200 border border-green-500/20 rounded px-2 py-1.5 hover:bg-green-500/10 transition-colors"
              data-testid="sidebar-quickstart-trigger"
            >
              Re-open Quickstart
            </button>
          </div>
        </div>
      </aside>

      <div className="lg:hidden fixed top-0 left-0 right-0 border-b border-gray-800 px-4 py-3 z-40" style={{ background: '#0f1419' }}>
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 bg-gradient-to-br from-blue-500 to-blue-600 rounded-lg flex items-center justify-center">
              <span className="text-white font-bold">P</span>
            </div>
            <h1 className="text-white font-bold" style={{ fontFamily: 'Space Grotesk' }}>
              ProfitEngine
            </h1>
          </div>
          <button
            onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
            className="p-2 hover:bg-gray-800 rounded-lg text-gray-400"
            data-testid="mobile-menu-toggle"
          >
            {mobileMenuOpen ? <X /> : <Menu />}
          </button>
        </div>
      </div>

      {mobileMenuOpen && (
        <div className="lg:hidden fixed inset-0 z-30 overflow-y-auto pt-16" style={{ background: '#0f1419' }} data-testid="mobile-sidebar">
          <div className="px-4 py-6">
            <NavSection title="Operations" items={navGroups.operations} pathname={location.pathname} onLinkClick={closeMobileMenu} />
            <NavSection title="Revenue" items={navGroups.revenue} pathname={location.pathname} onLinkClick={closeMobileMenu} />
            <NavSection title="System" items={navGroups.system} pathname={location.pathname} onLinkClick={closeMobileMenu} />
          </div>
        </div>
      )}

      <main className="min-h-screen mt-16 lg:mt-0" data-testid="main-content">
        <Outlet />
      </main>
      <QuickstartWizard key={wizardKey} />
    </div>
  );
}
