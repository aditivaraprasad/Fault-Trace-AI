import React, { useState } from 'react';
import {
  Play,
  Zap,
  UploadCloud,
  FileSpreadsheet,
  CheckCircle2,
  AlertCircle,
  FileUp,
  Cpu,
  Layers,
  ArrowRight,
  Database,
  ShieldAlert,
} from 'lucide-react';
import { api } from '../services/api';
import LoadingSpinner from '../components/LoadingSpinner';
import ErrorMessage from '../components/ErrorMessage';
import StatusBadge from '../components/StatusBadge';

export default function SimulationPage({ onNavigateToIncident }) {
  // Simulation State
  const [runningSim, setRunningSim] = useState(false);
  const [simResult, setSimResult] = useState(null);
  const [simError, setSimError] = useState(null);

  // Ingestion State
  const [selectedDataset, setSelectedDataset] = useState('breaker-trips');
  const [uploadFile, setUploadFile] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [uploadResult, setUploadResult] = useState(null);
  const [uploadError, setUploadError] = useState(null);

  // 1. Run Simulation
  const handleTriggerSimulation = async (type = 'f4_hero') => {
    try {
      setRunningSim(true);
      setSimError(null);
      setSimResult(null);
      const res = await api.simulateScenario(type);
      setSimResult(res);
    } catch (err) {
      setSimError(err.message || 'Simulation execution failed.');
    } finally {
      setRunningSim(false);
    }
  };

  // 2. CSV Upload
  const handleCsvUpload = async (e) => {
    e.preventDefault();
    if (!uploadFile) {
      setUploadError('Please select a CSV file to upload.');
      return;
    }

    try {
      setUploading(true);
      setUploadError(null);
      setUploadResult(null);
      const res = await api.uploadCsv(selectedDataset, uploadFile);
      setUploadResult(res);
    } catch (err) {
      setUploadError(err.message || 'CSV Ingestion failed.');
    } finally {
      setUploading(false);
    }
  };

  // 3. Quick Sample Data Load
  const handleLoadSample = async (sampleType) => {
    // Generate sample raw file contents corresponding to sample datasets
    const sampleFiles = {
      'breaker-trips': new File(
        ['section_code,event_timestamp,event_type,source\nF4-S14,2026-11-18T14:15:00Z,BREAKER_TRIP,SCADA\nF4-S12,2026-11-18T14:15:03Z,RECLOSER_LOCKOUT,RTU\nF4-S13,2026-11-18T14:15:10Z,AMI_LAST_GASP,AMI\n'],
        'sample_breaker_trips.csv',
        { type: 'text/csv' }
      ),
      'voltage-readings': new File(
        ['transformer_code,timestamp,voltage_v,current_a,active_power_kw,power_factor,frequency_hz\nDT-14,2026-11-18T14:15:02Z,0.0,0.0,0.0,0.0,50.0\nDT-13,2026-11-18T14:15:02Z,0.0,0.0,0.0,0.0,50.0\nDT-16,2026-11-18T14:15:02Z,0.0,0.0,0.0,0.0,50.0\nDT-12,2026-11-18T14:15:02Z,185.4,42.5,7.8,0.88,49.8\nDT-08,2026-11-18T14:15:02Z,228.6,85.2,19.4,0.95,50.0\n'],
        'sample_voltage_readings.csv',
        { type: 'text/csv' }
      ),
      'complaints': new File(
        ['section_code,cluster_name,timestamp,complaint_type,phone,remarks\nF4-S14,Peenya Ind Sector 2,2026-11-18T14:16:30Z,NO_POWER,9845012345,Power cut near District Water Pump\nF4-S14,Peenya Ind Sector 2,2026-11-18T14:17:15Z,NO_POWER,9845012346,Transformer spark\nF4-S13,Hebbal 4th Block,2026-11-18T14:18:00Z,VOLTAGE_FLUCTUATION,9845012347,Lights flickering\n'],
        'sample_complaints.csv',
        { type: 'text/csv' }
      ),
      'malformed': new File(
        ['section_code,event_timestamp,event_type,source\nF4-S14,INVALID_TIMESTAMP_FORMAT,BREAKER_TRIP,SCADA\nF4-S9999,2026-11-18T14:15:00Z,UNKNOWN_EVENT,TEST\n'],
        'malformed_trips.csv',
        { type: 'text/csv' }
      ),
    };

    const targetType = sampleType === 'malformed' ? 'breaker-trips' : sampleType;
    const file = sampleFiles[sampleType];

    try {
      setUploading(true);
      setUploadError(null);
      setUploadResult(null);
      setSelectedDataset(targetType);
      const res = await api.uploadCsv(targetType, file);
      setUploadResult(res);
    } catch (err) {
      setUploadError(err.message || 'Validation failed.');
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className="p-6 space-y-8 max-w-7xl mx-auto">
      {/* Page Header */}
      <div>
        <h2 className="text-lg font-bold text-white uppercase tracking-wider flex items-center gap-2.5">
          <Zap className="w-5 h-5 text-orange-500" />
          Scenario Simulation & Telemetry Ingestion
        </h2>
        <p className="text-xs text-slate-400 mt-1">
          Execute reproducible distribution grid fault scenarios or ingest multi-source SCADA/AMI CSV telemetry packets.
        </p>
      </div>

      {/* Grid: 2 Column Layout for Simulation & Ingestion */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        {/* Left Column: Live Scenario Simulator */}
        <div className="space-y-6">
          <div className="bg-control-panel border border-control-border rounded-xl p-5 shadow-sm space-y-5">
            <div className="flex items-center justify-between pb-3 border-b border-control-border">
              <div>
                <h3 className="text-sm font-bold text-white uppercase tracking-wide">
                  Distribution Fault Simulator
                </h3>
                <p className="text-xs text-slate-400">Trigger deterministic or randomized grid disturbances</p>
              </div>
              <Cpu className="w-4 h-4 text-orange-400" />
            </div>

            {/* F4 Hero Scenario Card */}
            <div className="bg-control-card border border-orange-500/30 rounded-lg p-4 space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-xs font-bold uppercase tracking-wider text-orange-400 bg-orange-500/10 px-2.5 py-0.5 rounded border border-orange-500/30">
                  Hero Scenario Preset &bull; Feeder F4
                </span>
                <span className="text-xs font-mono text-slate-400">Theme 10 Benchmark</span>
              </div>
              <p className="text-xs text-slate-300 leading-relaxed">
                Simulates high-impedance fault on section <strong className="text-white">F4-S14</strong> serving the{' '}
                <strong className="text-rose-400">District Water Pumping Station</strong> under severe pre-monsoon wind gusts (48 km/h),
                generating 142 customer calls and downstream transformer voltage collapse.
              </p>
              <div className="flex items-center justify-between pt-2">
                <div className="text-[11px] text-slate-400">
                  Ground Truth Section: <span className="text-orange-400 font-mono font-bold">F4-S14</span>
                </div>
                <button
                  onClick={() => handleTriggerSimulation('f4_hero')}
                  disabled={runningSim}
                  className="px-4 py-2 bg-orange-600 hover:bg-orange-500 disabled:bg-slate-700 text-white rounded-lg text-xs font-bold flex items-center gap-2 shadow-lg shadow-orange-950/50 transition-all"
                >
                  <Play className="w-3.5 h-3.5 fill-current" />
                  {runningSim ? 'Simulating Pipeline...' : 'Run F4 Hero Scenario'}
                </button>
              </div>
            </div>

            {/* Random Scenario Card */}
            <div className="bg-control-card border border-control-border rounded-lg p-4 space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-xs font-bold uppercase tracking-wider text-sky-400 bg-sky-500/10 px-2.5 py-0.5 rounded border border-sky-500/30">
                  Randomized Scenario
                </span>
                <span className="text-xs font-mono text-slate-400">Stochastic Grid Trip</span>
              </div>
              <p className="text-xs text-slate-300 leading-relaxed">
                Stochastically selects an arbitrary 11kV feeder and candidate section, generating noisy AMI telemetry,
                packet drops, and customer complaints across the Bengaluru network tree.
              </p>
              <div className="flex items-center justify-between pt-2">
                <div className="text-[11px] text-slate-400">
                  Target: <span className="text-slate-300 font-mono">Arbitrary Feeder Branch</span>
                </div>
                <button
                  onClick={() => handleTriggerSimulation('random')}
                  disabled={runningSim}
                  className="px-4 py-2 bg-slate-800 hover:bg-slate-700 disabled:bg-slate-700 text-white rounded-lg text-xs font-bold flex items-center gap-2 border border-slate-600 transition-all"
                >
                  <Play className="w-3.5 h-3.5 fill-current" />
                  {runningSim ? 'Simulating...' : 'Run Random Scenario'}
                </button>
              </div>
            </div>

            {/* Status Feedback */}
            {runningSim && <LoadingSpinner message="Executing 9-stage pipeline: Collect → Prune → Rank → Explain → Restore..." />}
            {simError && <ErrorMessage message={simError} onRetry={() => handleTriggerSimulation('f4_hero')} />}

            {/* Active Simulation Result Banner */}
            {simResult && (
              <div className="bg-slate-900 border border-emerald-500/40 rounded-xl p-4 space-y-3 shadow-md">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2 text-emerald-400 font-bold text-xs uppercase tracking-wide">
                    <CheckCircle2 className="w-4 h-4" />
                    Simulation Executed & Persisted
                  </div>
                  <span className="text-xs font-mono text-slate-400">{simResult.simulation_scenario_id}</span>
                </div>

                <div className="grid grid-cols-2 gap-2 text-xs">
                  <div className="p-2 bg-slate-800/60 rounded">
                    <span className="text-slate-400">Feeder:</span>{' '}
                    <strong className="text-sky-400">{simResult.feeder_code}</strong>
                  </div>
                  <div className="p-2 bg-slate-800/60 rounded">
                    <span className="text-slate-400">True Fault Section:</span>{' '}
                    <strong className="text-orange-400 font-mono">{simResult.actual_fault_section.section_code}</strong>
                  </div>
                  <div className="p-2 bg-slate-800/60 rounded">
                    <span className="text-slate-400">Candidates Found:</span>{' '}
                    <strong className="text-white">{simResult.localization_result.candidates.length}</strong>
                  </div>
                  <div className="p-2 bg-slate-800/60 rounded">
                    <span className="text-slate-400">Pruning %:</span>{' '}
                    <strong className="text-emerald-400">{simResult.localization_result.pruning_percentage}%</strong>
                  </div>
                </div>

                <div className="pt-2 flex justify-end">
                  <button
                    onClick={() => onNavigateToIncident && onNavigateToIncident(simResult.incident_id)}
                    className="px-3.5 py-1.5 bg-orange-600 hover:bg-orange-500 text-white rounded text-xs font-bold flex items-center gap-1.5 transition"
                  >
                    Open Incident View &bull; Inspect SHAP &amp; Restoration
                    <ArrowRight className="w-3.5 h-3.5" />
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Right Column: Multi-Source CSV Ingestion */}
        <div className="space-y-6">
          <div className="bg-control-panel border border-control-border rounded-xl p-5 shadow-sm space-y-5">
            <div className="flex items-center justify-between pb-3 border-b border-control-border">
              <div>
                <h3 className="text-sm font-bold text-white uppercase tracking-wide">
                  SCADA &amp; AMI CSV Data Ingestion
                </h3>
                <p className="text-xs text-slate-400">Upload batch telemetry with strict Pydantic validation</p>
              </div>
              <FileSpreadsheet className="w-4 h-4 text-sky-400" />
            </div>

            {/* Dataset Selector */}
            <div className="space-y-1.5">
              <label className="text-xs font-bold text-slate-300 uppercase tracking-wider">
                Target Dataset Type:
              </label>
              <select
                value={selectedDataset}
                onChange={(e) => setSelectedDataset(e.target.value)}
                className="w-full bg-control-card border border-control-border text-white text-xs rounded-lg p-2.5 focus:outline-none focus:border-orange-500"
              >
                <option value="breaker-trips">Breaker Trips &amp; Outage Events (/ingest/breaker-trips)</option>
                <option value="voltage-readings">Transformer Secondary Voltage Readings (/ingest/voltage-readings)</option>
                <option value="complaints">Customer CRM Outage Complaints (/ingest/complaints)</option>
                <option value="dt-status">Distribution Transformer Status Updates (/ingest/dt-status)</option>
                <option value="weather">Regional Weather Observations (/ingest/weather)</option>
                <option value="asset-records">Asset Health &amp; Condition Records (/ingest/asset-records)</option>
              </select>
            </div>

            {/* File Upload Dropzone Form */}
            <form onSubmit={handleCsvUpload} className="space-y-4">
              <div className="border-2 border-dashed border-control-border hover:border-slate-500 rounded-xl p-6 text-center bg-control-card/40 transition">
                <UploadCloud className="w-8 h-8 text-slate-400 mx-auto mb-2" />
                <div className="text-xs text-slate-300 font-medium">
                  {uploadFile ? (
                    <span className="text-orange-400 font-bold">{uploadFile.name} ({(uploadFile.size / 1024).toFixed(1)} KB)</span>
                  ) : (
                    <span>Select a formatted CSV telemetry file to upload</span>
                  )}
                </div>
                <input
                  type="file"
                  accept=".csv"
                  onChange={(e) => setUploadFile(e.target.files[0] || null)}
                  className="mt-3 text-xs text-slate-400 file:mr-3 file:py-1.5 file:px-3 file:rounded-md file:border-0 file:text-xs file:font-semibold file:bg-slate-800 file:text-slate-200 hover:file:bg-slate-700 cursor-pointer"
                />
              </div>

              <div className="flex items-center justify-between">
                <div className="text-[11px] text-slate-400">
                  Validates ISO-8601 timestamps &amp; physical voltage ranges
                </div>
                <button
                  type="submit"
                  disabled={uploading || !uploadFile}
                  className="px-4 py-2 bg-sky-600 hover:bg-sky-500 disabled:bg-slate-700 text-white rounded-lg text-xs font-bold flex items-center gap-2 transition"
                >
                  <FileUp className="w-3.5 h-3.5" />
                  {uploading ? 'Ingesting...' : 'Upload & Ingest CSV'}
                </button>
              </div>
            </form>

            {/* Quick Sample Dataset Loaders */}
            <div className="pt-3 border-t border-control-border space-y-2.5">
              <span className="text-[11px] font-bold uppercase tracking-wider text-slate-400">
                Quick Sample Ingestion:
              </span>
              <div className="flex flex-wrap gap-2">
                <button
                  onClick={() => handleLoadSample('breaker-trips')}
                  disabled={uploading}
                  className="px-2.5 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs rounded border border-slate-700 transition"
                >
                  + Sample Breaker Trips
                </button>
                <button
                  onClick={() => handleLoadSample('voltage-readings')}
                  disabled={uploading}
                  className="px-2.5 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs rounded border border-slate-700 transition"
                >
                  + Sample Voltage Telemetry
                </button>
                <button
                  onClick={() => handleLoadSample('complaints')}
                  disabled={uploading}
                  className="px-2.5 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs rounded border border-slate-700 transition"
                >
                  + Sample Complaints
                </button>
                <button
                  onClick={() => handleLoadSample('malformed')}
                  disabled={uploading}
                  className="px-2.5 py-1.5 bg-rose-950/40 hover:bg-rose-900/50 text-rose-300 text-xs rounded border border-rose-700/50 transition font-bold"
                  title="Uploads bad CSV to demonstrate 422 error response"
                >
                  ⚠ Test Malformed CSV (422)
                </button>
              </div>
            </div>

            {/* Ingestion Response Feedback */}
            {uploadResult && (
              <div className="bg-emerald-950/30 border border-emerald-500/40 rounded-lg p-3.5 text-xs text-emerald-200 flex items-start gap-2.5">
                <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0 mt-0.5" />
                <div>
                  <strong className="text-emerald-300">Ingestion Successful:</strong> {uploadResult.message}
                  <div className="mt-1 text-[11px] text-emerald-400">
                    Received: {uploadResult.rows_received} rows | Stored: {uploadResult.rows_ingested} rows
                  </div>
                </div>
              </div>
            )}

            {uploadError && (
              <ErrorMessage
                message={uploadError}
                onRetry={() => setUploadError(null)}
              />
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
