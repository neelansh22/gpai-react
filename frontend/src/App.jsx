import { HashRouter, Routes, Route } from "react-router-dom";
import { AppStateProvider } from "./state/AppState";
import { PricingStateProvider } from "./state/PricingState";
import Sidebar from "./components/Sidebar";
import PricingSidebar from "./components/PricingSidebar";
import Toast from "./components/Toast";
import AppSelector from "./pages/AppSelector";
import Overview from "./pages/Overview";
import DataIngestion from "./pages/DataIngestion";
import ProcessEmbed from "./pages/ProcessEmbed";
import Clusters from "./pages/Clusters";
import TrainModel from "./pages/TrainModel";
import Diagnose from "./pages/Diagnose";
import HistoryAnalytics from "./pages/HistoryAnalytics";
import PricingOverview from "./pages/pricing/PricingOverview";
import CorridorAnalysis from "./pages/pricing/CorridorAnalysis";
import YearlyTrend from "./pages/pricing/YearlyTrend";
import SummaryTable from "./pages/pricing/SummaryTable";

function GpaiLayout() {
  return (
    <AppStateProvider>
      <div className="flex h-screen w-full overflow-hidden">
        <Sidebar />
        <main className="flex-1 overflow-y-auto">
          <div className="mx-auto max-w-6xl px-6 py-8 md:px-10">
            <Routes>
              <Route index element={<Overview />} />
              <Route path="data" element={<DataIngestion />} />
              <Route path="process" element={<ProcessEmbed />} />
              <Route path="clusters" element={<Clusters />} />
              <Route path="train" element={<TrainModel />} />
              <Route path="diagnose" element={<Diagnose />} />
              <Route path="history" element={<HistoryAnalytics />} />
            </Routes>
          </div>
        </main>
      </div>
      <Toast />
    </AppStateProvider>
  );
}

function PricingLayout() {
  return (
    <PricingStateProvider>
      <div className="flex h-screen w-full overflow-hidden">
        <PricingSidebar />
        <main className="flex-1 overflow-y-auto">
          <div className="mx-auto max-w-6xl px-6 py-8 md:px-10">
            <Routes>
              <Route index element={<PricingOverview />} />
              <Route path="corridor" element={<CorridorAnalysis />} />
              <Route path="trend" element={<YearlyTrend />} />
              <Route path="table" element={<SummaryTable />} />
            </Routes>
          </div>
        </main>
      </div>
    </PricingStateProvider>
  );
}

function App() {
  return (
    <HashRouter>
      <Routes>
        <Route path="/" element={<AppSelector />} />
        <Route path="/gpai/*" element={<GpaiLayout />} />
        <Route path="/pricing/*" element={<PricingLayout />} />
      </Routes>
    </HashRouter>
  );
}

export default App;
