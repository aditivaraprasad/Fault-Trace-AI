import React, { useState, useEffect } from 'react';
import { Activity, CloudRain, Wind, AlertCircle, RefreshCw, ServerCrash, CheckCircle2 } from 'lucide-react';
import { api } from '../services/api';

export default function Header() {
  const [weather, setWeather] = useState(null);
  const [loadingWeather, setLoadingWeather] = useState(false);
  const [backendStatus, setBackendStatus] = useState('checking'); // 'connected' | 'degraded' | 'offline' | 'checking'
  const [backendDetails, setBackendDetails] = useState(null);

  useEffect(() => {
    loadHealth();
    loadWeather();
    const interval = setInterval(() => {
      loadHealth();
    }, 15000);
    return () => clearInterval(interval);
  }, []);

  const loadHealth = async () => {
    try {
      const data = await api.getHealth();
      setBackendDetails(data);
      if (data.status === 'healthy' && data.database?.status === 'connected') {
        setBackendStatus('connected');
      } else {
        setBackendStatus('degraded');
      }
    } catch (err) {
      console.warn("Backend health check failed:", err.message);
      setBackendStatus('offline');
      setBackendDetails(null);
    }
  };

  const loadWeather = async () => {
    try {
      setLoadingWeather(true);
      const data = await api.getCurrentWeather();
      setWeather(data);
    } catch (err) {
      console.warn("Weather fetch non-critical fallback", err);
    } finally {
      setLoadingWeather(false);
    }
  };

  return (
    <header className="h-16 bg-control-panel border-b border-control-border px-6 flex items-center justify-between sticky top-0 z-30 shadow-md">
      {/* Brand & Subtitle */}
      <div className="flex items-center gap-3">
        <div className="w-9 h-9 rounded-lg bg-orange-600 flex items-center justify-center shadow-lg shadow-orange-950/50">
          <Activity className="w-5 h-5 text-white" />
        </div>
        <div>
          <div className="flex items-center gap-2.5">
            <h1 className="text-base font-bold tracking-tight text-white uppercase">
              FAULTTRACE <span className="text-orange-500 font-extrabold">AI</span>
            </h1>
            <span className="bg-amber-500/15 border border-amber-500/40 text-amber-300 px-2 py-0.5 rounded text-[10px] font-bold tracking-wider uppercase">
              Synthetic data / prototype
            </span>
          </div>
          <p className="text-[11px] text-slate-400 font-medium">
            BESCOM Distribution Grid Control Room &bull; Theme 10 (Fault Localization & Advisory Restoration)
          </p>
        </div>
      </div>

      {/* Status & Weather Telemetry */}
      <div className="flex items-center gap-4">
        {/* Weather Indicator */}
        {weather && (
          <div className="hidden lg:flex items-center gap-3 px-3 py-1.5 bg-control-card border border-control-border rounded-lg text-xs">
            <div className="flex items-center gap-1.5 text-slate-300">
              <CloudRain className="w-3.5 h-3.5 text-sky-400" />
              <span>{weather.temperature_c.toFixed(1)}°C ({weather.precipitation_mm}mm)</span>
            </div>
            <div className="w-px h-3.5 bg-slate-700" />
            <div className="flex items-center gap-1.5 text-slate-300">
              <Wind className="w-3.5 h-3.5 text-orange-400" />
              <span>{weather.wind_gust_kmh.toFixed(0)} km/h gusts</span>
            </div>
            <span className={`text-[10px] font-bold px-1.5 py-0.5 rounded uppercase tracking-wider ${
              weather.source === 'live' 
                ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30' 
                : 'bg-slate-700/50 text-slate-400 border border-slate-600'
            }`}>
              {weather.source}
            </span>
          </div>
        )}

        {/* Live Backend & SCADA Telemetry Heartbeat */}
        <div 
          className={`flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs border transition-colors ${
            backendStatus === 'connected'
              ? 'bg-control-card border-control-border text-slate-200'
              : backendStatus === 'degraded'
              ? 'bg-amber-950/40 border-amber-600/50 text-amber-200'
              : backendStatus === 'offline'
              ? 'bg-rose-950/40 border-rose-600/50 text-rose-200'
              : 'bg-control-card border-control-border text-slate-400'
          }`}
          title={backendDetails ? `DB: ${backendDetails.database?.dialect} (${backendDetails.database?.status})` : 'Backend connection'}
        >
          {backendStatus === 'connected' && (
            <>
              <span className="relative flex h-2 w-2">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
                <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
              </span>
              <span className="font-semibold text-slate-200">SCADA/AMI Connected</span>
            </>
          )}

          {backendStatus === 'degraded' && (
            <>
              <AlertCircle className="w-3.5 h-3.5 text-amber-400" />
              <span className="font-semibold text-amber-300">Backend Degraded (DB Issue)</span>
            </>
          )}

          {backendStatus === 'offline' && (
            <>
              <ServerCrash className="w-3.5 h-3.5 text-rose-400" />
              <span className="font-semibold text-rose-300">Backend Offline (Port 8000)</span>
              <button 
                onClick={loadHealth}
                className="ml-1 text-[10px] underline text-rose-200 hover:text-white"
              >
                Retry
              </button>
            </>
          )}

          {backendStatus === 'checking' && (
            <>
              <RefreshCw className="w-3 h-3 text-slate-400 animate-spin" />
              <span className="text-slate-400">Connecting...</span>
            </>
          )}
        </div>
      </div>
    </header>
  );
}
