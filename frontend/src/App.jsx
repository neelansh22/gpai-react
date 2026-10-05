import { HashRouter, Routes, Route } from "react-router-dom";
import { AppStateProvider } from "./state/AppState";
import { PricingStateProvider } from "./state/PricingState";
import { SdodStateProvider } from "./state/SdodState";
import Sidebar from "./components/Sidebar";
import PricingSidebar from "./components/PricingSidebar";
import SdodSidebar from "./components/SdodSidebar";
import Toast from "./components/Toast";
import SdodToast from "./components/SdodToast";
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
import SdodOverview from "./pages/sdod/SdodOverview";
import IntentWizard from "./pages/sdod/IntentWizard";
import SchemaBuilder from "./pages/sdod/SchemaBuilder";
import SchemaEditor from "./pages/sdod/SchemaEditor";
import GenerateData from "./pages/sdod/GenerateData";
import AugmentExplore from "./pages/sdod/AugmentExplore";
import { MonitorStateProvider } from "./state/MonitorState";
import MonitorSidebar from "./components/MonitorSidebar";
import MonitorOverview from "./pages/monitor/MonitorOverview";
import MonitorCache from "./pages/monitor/MonitorCache";
import MonitorUsage from "./pages/monitor/MonitorUsage";
import MonitorHeatmap from "./pages/monitor/MonitorHeatmap";

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

function SdodLayout() {
  return (
    <SdodStateProvider>
      <div className="flex h-screen w-full overflow-hidden">
        <SdodSidebar />
        <main className="flex-1 overflow-y-auto">
          <div className="mx-auto max-w-6xl px-6 py-8 md:px-10">
            <Routes>
              <Route index element={<SdodOverview />} />
              <Route path="intent" element={<IntentWizard />} />
              <Route path="schema" element={<SchemaBuilder />} />
              <Route path="editor" element={<SchemaEditor />} />
              <Route path="generate" element={<GenerateData />} />
              <Route path="augment" element={<AugmentExplore />} />
            </Routes>
          </div>
        </main>
      </div>
      <SdodToast />
    </SdodStateProvider>
  );
}

function MonitorLayout() {
  return (
    <MonitorStateProvider>
      <div className="flex h-screen w-full overflow-hidden">
        <MonitorSidebar />
        <main className="flex-1 overflow-y-auto">
          <div className="mx-auto max-w-6xl px-6 py-8 md:px-10">
            <Routes>
              <Route index element={<MonitorOverview />} />
              <Route path="cache" element={<MonitorCache />} />
              <Route path="usage" element={<MonitorUsage />} />
              <Route path="heatmap" element={<MonitorHeatmap />} />
            </Routes>
          </div>
        </main>
      </div>
    </MonitorStateProvider>
  );
}

function App() {
  return (
    <HashRouter>
      <Routes>
        <Route path="/" element={<AppSelector />} />
        <Route path="/sdod/*" element={<SdodLayout />} />
        <Route path="/gpai/*" element={<GpaiLayout />} />
        <Route path="/pricing/*" element={<PricingLayout />} />
        <Route path="/monitor/*" element={<MonitorLayout />} />
      </Routes>
    </HashRouter>
  );
}

export default App;
