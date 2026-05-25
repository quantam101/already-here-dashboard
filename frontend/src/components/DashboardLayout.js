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
  Menu,
  X,
} from "lucide-react";
import { useState } from "react";

const navigation = [
  { name: "Overview", path: "/overview", icon: LayoutDashboard },
  { name: "Revenue", path: "/revenue", icon: DollarSign },
  { name: "Content", path: "/content", icon: FileText },
  { name: "Agents", path: "/agents", icon: Bot },
  { name: "Builds", path: "/builds", icon: Package },
  { name: "Deployments", path: "/deployments", icon: Rocket },
  { name: "Approvals", path: "/approvals", icon: CheckCircle2 },
  { name: "Audit", path: "/audit", icon: Shield },
];

export default function DashboardLayout() {
  const location = useLocation();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  return (
    <div className="dashboard-layout">
      {/* Sidebar - Desktop */}
      <aside className="hidden lg:block bg-white border-r border-gray-200 px-6 py-8">
        <div className="mb-12">
          <h1 className="text-2xl font-bold gradient-text" data-testid="dashboard-title">
            Command OS
          </h1>
          <p className="text-sm text-gray-500 mt-1">Already Here Ecosystem</p>
        </div>

        <nav className="space-y-1" data-testid="sidebar-nav">
          {navigation.map((item) => {
            const Icon = item.icon;
            const isActive = location.pathname === item.path;
            return (
              <NavLink
                key={item.path}
                to={item.path}
                className={`sidebar-link ${isActive ? "active" : ""}`}
                data-testid={`nav-${item.name.toLowerCase()}`}
              >
                <Icon className="w-5 h-5" />
                {item.name}
              </NavLink>
            );
          })}
        </nav>

        <div className="mt-12 p-4 bg-gradient-to-br from-purple-50 to-blue-50 rounded-lg" data-testid="sidebar-info">
          <div className="text-sm font-semibold text-gray-700 mb-1">
            System Status
          </div>
          <div className="flex items-center gap-2">
            <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse"></div>
            <span className="text-xs text-gray-600">All Systems Operational</span>
          </div>
        </div>
      </aside>

      {/* Mobile Header */}
      <div className="lg:hidden fixed top-0 left-0 right-0 bg-white border-b border-gray-200 px-4 py-3 z-40">
        <div className="flex items-center justify-between">
          <h1 className="text-xl font-bold gradient-text">Command OS</h1>
          <button
            onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
            className="p-2 hover:bg-gray-100 rounded-lg"
            data-testid="mobile-menu-toggle"
          >
            {mobileMenuOpen ? <X /> : <Menu />}
          </button>
        </div>
      </div>

      {/* Mobile Menu */}
      {mobileMenuOpen && (
        <div className="lg:hidden mobile-sidebar-open" data-testid="mobile-sidebar">
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
                    <Icon className="w-5 h-5" />
                    {item.name}
                  </NavLink>
                );
              })}
            </nav>
          </div>
        </div>
      )}

      {/* Main Content */}
      <main className="min-h-screen bg-gradient-to-br from-gray-50 via-white to-blue-50 p-6 lg:p-12 mt-16 lg:mt-0" data-testid="main-content">
        <Outlet />
      </main>
    </div>
  );
}