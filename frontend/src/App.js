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
import { Toaster } from "sonner";

function App() {
  return (
    <div className="App">
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<DashboardLayout />}>
            <Route index element={<Navigate to="/overview" replace />} />
            <Route path="overview" element={<Overview />} />
            <Route path="revenue" element={<Revenue />} />
            <Route path="content" element={<Content />} />
            <Route path="agents" element={<Agents />} />
            <Route path="builds" element={<Builds />} />
            <Route path="deployments" element={<Deployments />} />
            <Route path="approvals" element={<Approvals />} />
            <Route path="audit" element={<Audit />} />
          </Route>
        </Routes>
      </BrowserRouter>
      <Toaster position="top-right" richColors />
    </div>
  );
}

export default App;