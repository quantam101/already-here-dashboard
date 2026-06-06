import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import "@/App.css";
import DashboardLayout from "./components/DashboardLayout";
import Overview from "./pages/Overview";
import Revenue from "./pages/Revenue";
import Content from "./pages/Content";
import Agents from "./pages/Agents";
import Builds from "./pages/Builds";
import Deployments from "./pages/Deployments";
import Approvals from "./pages/Approvals";
import Audit from "./pages/Audit";
import ContentStudio from "./pages/ContentStudio";
import VideoStudio from "./pages/VideoStudio";
import ProofOfWork from "./pages/ProofOfWork";
import Scout from "./pages/Scout";
import Proposals from "./pages/Proposals";
import Analytics from "./pages/Analytics";
import Pricing from "./pages/Pricing";
import PaymentSuccess from "./pages/PaymentSuccess";
import Books from "./pages/Books";
import Secrets from "./pages/Secrets";
import Sovereign from "./pages/Sovereign";
import VoiceLab from "./pages/VoiceLab";
import DASIMatrix from "./pages/DASIMatrix";
import WorkOrders from "./pages/WorkOrders";
import CashCommand from "./pages/CashCommand";
import GrowthVault from "./pages/GrowthVault";
import ProductFactory from "./pages/ProductFactory";
import AuthGate from "./components/AuthGate";
import { FirstRunWalkthrough } from "./components/FirstRunWalkthrough";
import { Toaster } from "sonner";

function App() {
  return (
    <div className="App">
      <BrowserRouter>
        <AuthGate>
          <FirstRunWalkthrough />
          <Routes>
            <Route path="/" element={<DashboardLayout />}>
              <Route index element={<Navigate to="/overview" replace />} />
              <Route path="overview" element={<Overview />} />
              <Route path="revenue" element={<Revenue />} />
              <Route path="content" element={<Content />} />
              <Route path="studio" element={<ContentStudio />} />
              <Route path="video-studio" element={<VideoStudio />} />
              <Route path="agents" element={<Agents />} />
              <Route path="builds" element={<Builds />} />
              <Route path="deployments" element={<Deployments />} />
              <Route path="approvals" element={<Approvals />} />
              <Route path="audit" element={<Audit />} />
              <Route path="proof-of-work" element={<ProofOfWork />} />
              <Route path="scout"         element={<Scout />} />
              <Route path="proposals"     element={<Proposals />} />
              <Route path="analytics"     element={<Analytics />} />
              <Route path="pricing"       element={<Pricing />} />
              <Route path="waitlist"      element={<Pricing />} />
              <Route path="books"         element={<Books />} />
              <Route path="secrets"       element={<Secrets />} />
              <Route path="sovereign"     element={<Sovereign />} />
              <Route path="voice-lab"    element={<VoiceLab />} />
              <Route path="dasi-matrix"  element={<DASIMatrix />} />
              <Route path="work-orders"    element={<WorkOrders />} />
              <Route path="cash-command"   element={<CashCommand />} />
              <Route path="growth-vault"   element={<GrowthVault />} />
              <Route path="products"       element={<ProductFactory />} />
            </Route>
            <Route path="/payment-success" element={<PaymentSuccess />} />
          </Routes>
        </AuthGate>
      </BrowserRouter>
      <Toaster position="top-right" richColors closeButton />
    </div>
  );
}

export default App;
