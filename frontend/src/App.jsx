import React, { useState } from 'react';
import Header from './components/Header';
import Sidebar from './components/Sidebar';
import DashboardPage from './pages/DashboardPage';
import NetworkMapPage from './pages/NetworkMapPage';
import SimulationPage from './pages/SimulationPage';
import IncidentViewPage from './pages/IncidentViewPage';
import AssetsPage from './pages/AssetsPage';
import RestorationPage from './pages/RestorationPage';
import HistoryPage from './pages/HistoryPage';
import ModelPage from './pages/ModelPage';

export default function App() {
  const [activePage, setActivePage] = useState('dashboard');
  const [activeIncidentId, setActiveIncidentId] = useState(null);

  const navigateToIncident = (incidentId) => {
    setActiveIncidentId(incidentId);
    setActivePage('incident');
  };

  const navigateToRestoration = (incidentId) => {
    setActiveIncidentId(incidentId);
    setActivePage('restoration');
  };

  return (
    <div className="min-h-screen bg-control-bg text-slate-100 flex flex-col font-sans selection:bg-orange-500/30">
      {/* Top Navigation & Status Header */}
      <Header />

      {/* Main Control-Room Shell: Sidebar + Active Page */}
      <div className="flex-1 flex overflow-hidden">
        <Sidebar activePage={activePage} setActivePage={setActivePage} />

        <main className="flex-1 overflow-y-auto bg-control-bg">
          {activePage === 'dashboard' && (
            <DashboardPage onNavigateToIncident={navigateToIncident} />
          )}
          {activePage === 'map' && (
            <NetworkMapPage />
          )}
          {activePage === 'simulate' && (
            <SimulationPage onNavigateToIncident={navigateToIncident} />
          )}
          {activePage === 'incident' && (
            <IncidentViewPage
              initialIncidentId={activeIncidentId}
              onNavigateToRestoration={navigateToRestoration}
            />
          )}
          {activePage === 'assets' && (
            <AssetsPage />
          )}
          {activePage === 'restoration' && (
            <RestorationPage incidentId={activeIncidentId} />
          )}
          {activePage === 'history' && (
            <HistoryPage onInspectIncident={navigateToIncident} />
          )}
          {activePage === 'model' && (
            <ModelPage />
          )}
        </main>
      </div>
    </div>
  );
}
