import { Outlet, NavLink, useLocation } from "react-router-dom";
import {
  LayoutDashboard,
  DollarSign,
  FileText,
  Bot,
  Package,
  Rocket,
  CheckCircle2,
  Shield,
  TrendingUp,
  Link as LinkIcon,
  Menu,
  X,
} from "lucide-react";
import { useState } from "react";

const navigation = [
  { name: "Command Center", path: "/overview", icon: LayoutDashboard, section: "operations" },
  { name: "Income Streams", path: "/revenue", icon: DollarSign, section: "operations" },
  { name: "AI Agents", path: "/agents", icon: Bot, section: "operations" },
  { name: "Content Factory", path: "/content", icon: FileText, section: "operations" },
  { name: "Revenue Intel", path: "/builds", icon: TrendingUp, section: "revenue" },
  { name: "Merch / POD", path: "/deployments", icon: Package, section: "revenue" },
  { name: "Affiliate Links", path: "/approvals", icon: LinkIcon, section: "revenue" },
  { name: "VHLL / AAF", path: "/audit", icon: Rocket, section: "system" },
  { name: "LGAC Monitor", path: "/audit", icon: Shield, section: "system" },
];

export default function DashboardLayout() {
  const location = useLocation();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

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
              <p className="text-gray-500 text-xs">v5.0x - PRODUCTION - VHLL PROD</p>
            </div>
          </div>
        </div>

        <nav className="space-y-1" data-testid="sidebar-nav">
          <div className="mb-6">
            <div className="text-gray-500 text-xs font-semibold uppercase tracking-wider mb-2 px-3">
              Operations
            </div>
            {navigation
              .filter((item) => item.section === "operations")
              .map((item) => {
                const Icon = item.icon;
                const isActive = location.pathname === item.path;
                return (
                  <NavLink
                    key={item.path}
                    to={item.path}
                    className={`sidebar-link ${isActive ? "active" : ""}`}
                    data-testid={`nav-${item.name.toLowerCase().replace(/\\s+/g, '-')}`}
                  >
                    <Icon className="w-4 h-4" />
                    <span className="text-sm">{item.name}</span>
                  </NavLink>
                );
              })}
          </div>

          <div className="mb-6">
            <div className="text-gray-500 text-xs font-semibold uppercase tracking-wider mb-2 px-3">
              Revenue
            </div>
            {navigation
              .filter((item) => item.section === "revenue")
              .map((item) => {
                const Icon = item.icon;
                const isActive = location.pathname === item.path;
                return (
                  <NavLink
                    key={item.path}
                    to={item.path}
                    className={`sidebar-link ${isActive ? "active" : ""}`}
                  >
                    <Icon className="w-4 h-4" />
                    <span className="text-sm">{item.name}</span>
                  </NavLink>
                );
              })}
          </div>

          <div>
            <div className="text-gray-500 text-xs font-semibold uppercase tracking-wider mb-2 px-3">
              System
            </div>
            {navigation
              .filter((item) => item.section === "system")
              .map((item) => {
                const Icon = item.icon;
                const isActive = location.pathname === item.path;
                return (
                  <NavLink
                    key={item.path}
                    to={item.path}
                    className={`sidebar-link ${isActive ? "active" : ""}`}
                  >
                    <Icon className="w-4 h-4" />
                    <span className="text-sm">{item.name}</span>
                  </NavLink>
                );
              })}
          </div>
        </nav>

        <div className="mt-auto pt-6" data-testid="sidebar-info">
          <div className="p-3 border border-gray-700 rounded-lg" style={{ background: 'rgba(31, 41, 55, 0.5)' }}>
            <div className="flex items-center gap-2 mb-2">
              <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse"></div>
              <span className="text-xs font-semibold text-gray-300">System Status</span>
            </div>
            <div className="text-xs text-gray-400">All services operational</div>
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
        <div className="lg:hidden mobile-sidebar-open" style={{ background: '#0f1419' }} data-testid="mobile-sidebar">
          <div className="px-4 py-20">
            <nav className="space-y-1">
              {navigation.map((item) => {
                const Icon = item.icon;
                const isActive = location.pathname === item.path;
                return (
                  <NavLink
                    key={item.path}
                    to={item.path}
                    onClick={() => setMobileMenuOpen(false)}
                    className={`sidebar-link ${isActive ? "active" : ""}`}
                  >
                    <Icon className="w-4 h-4" />
                    {item.name}
                  </NavLink>
                );
              })}
            </nav>
          </div>
        </div>
      )}

      <main className="min-h-screen mt-16 lg:mt-0" data-testid="main-content">
        <Outlet />
      </main>
    </div>
  );
}
