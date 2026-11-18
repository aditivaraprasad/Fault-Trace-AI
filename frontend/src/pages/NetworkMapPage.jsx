import React, { useState, useEffect, useMemo } from 'react';
import { MapContainer, TileLayer, Marker, Popup, Polyline, CircleMarker, useMap } from 'react-leaflet';
import L from 'leaflet';
import {
  Layers,
  RefreshCw,
  Sun,
  Moon,
} from 'lucide-react';
import { api } from '../services/api';
import LoadingSpinner from '../components/LoadingSpinner';
import ErrorMessage from '../components/ErrorMessage';

// Safe Leaflet object reference
const leaflet = (typeof L !== 'undefined' && L && L.divIcon) ? L : (L?.default || (typeof window !== 'undefined' ? window.L : null) || L);

// Helper component: forces Leaflet canvas recalculation (invalidateSize) and re-centers
function MapResizerAndRecenter({ center }) {
  const map = useMap();

  useEffect(() => {
    // Invalidate size immediately, after 100ms, and 300ms to eliminate 0-height canvas in flex layouts
    map.invalidateSize();
    const t1 = setTimeout(() => map.invalidateSize(), 100);
    const t2 = setTimeout(() => map.invalidateSize(), 300);
    const handleResize = () => map.invalidateSize();
    window.addEventListener('resize', handleResize);
    return () => {
      clearTimeout(t1);
      clearTimeout(t2);
      window.removeEventListener('resize', handleResize);
    };
  }, [map]);

  useEffect(() => {
    if (center && Number.isFinite(center[0]) && Number.isFinite(center[1])) {
      map.setView(center, 13, { animate: true });
    }
  }, [center, map]);

  return null;
}

// Custom DivIcons
const createSubstationIcon = (code) => {
  if (!leaflet || !leaflet.divIcon) return undefined;
  return leaflet.divIcon({
    className: 'custom-substation-icon',
    html: `<div style="background-color: #0F172A; border: 2px solid #F59E0B; color: #F59E0B; border-radius: 6px; padding: 3px 6px; font-weight: bold; font-size: 10px; display: flex; align-items: center; gap: 3px; box-shadow: 0 0 10px rgba(245, 158, 11, 0.4);">
      <span>⚡</span><span>${code}</span>
    </div>`,
    iconSize: [60, 24],
    iconAnchor: [30, 12],
  });
};

const createCriticalLoadIcon = (name, tier) => {
  if (!leaflet || !leaflet.divIcon) return undefined;
  return leaflet.divIcon({
    className: 'custom-critical-icon',
    html: `<div style="background-color: #7F1D1D; border: 2px solid #EF4444; color: #FEE2E2; border-radius: 6px; padding: 3px 6px; font-weight: bold; font-size: 10px; display: flex; align-items: center; gap: 4px; box-shadow: 0 0 12px rgba(239, 68, 68, 0.6);">
      <span>🚨</span><span>${name} [T${tier}]</span>
    </div>`,
    iconSize: [120, 24],
    iconAnchor: [60, 12],
  });
};

const createTieSwitchIcon = (code) => {
  if (!leaflet || !leaflet.divIcon) return undefined;
  return leaflet.divIcon({
    className: 'custom-tie-icon',
    html: `<div style="background-color: #1E293B; border: 2px dashed #94A3B8; color: #E2E8F0; border-radius: 4px; padding: 2px 5px; font-size: 9px; font-weight: bold;">
      <span>⚲ NO: ${code}</span>
    </div>`,
    iconSize: [80, 20],
    iconAnchor: [40, 10],
  });
};

export default function NetworkMapPage({ candidateSectionIds = [], affectedSectionIds = [] }) {
  const [topology, setTopology] = useState(null);
  const [selectedFeeder, setSelectedFeeder] = useState('ALL');
  const [mapTheme, setMapTheme] = useState('osm'); // 'osm' (OpenStreetMap) | 'dark' (CartoDB)
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    loadTopology();
  }, [selectedFeeder]);

  const loadTopology = async () => {
    try {
      setLoading(true);
      setError(null);
      const feederId = selectedFeeder === 'ALL' ? null : parseInt(selectedFeeder);
      const data = await api.getTopology(feederId);
      setTopology(data);
    } catch (err) {
      setError(err.message || 'Failed to load network topology GIS data.');
    } finally {
      setLoading(false);
    }
  };

  // Compute map center dynamically from current sections or default to Hebbal
  const center = useMemo(() => {
    if (topology && topology.sections && topology.sections.length > 0) {
      const valid = topology.sections.filter(s => 
        (s.start_latitude && s.start_longitude) || 
        (s.coordinates && s.coordinates[0] && Number.isFinite(s.coordinates[0][0]))
      );
      if (valid.length > 0) {
        let totalLat = 0;
        let totalLng = 0;
        valid.forEach(s => {
          const lat = s.start_latitude || s.coordinates[0][0];
          const lng = s.start_longitude || s.coordinates[0][1];
          totalLat += lat;
          totalLng += lng;
        });
        return [totalLat / valid.length, totalLng / valid.length];
      }
    }
    return [13.0358, 77.5970];
  }, [topology]);

  if (loading && !topology) return <LoadingSpinner message="Rendering GIS electrical network..." fullPage />;
  if (error && !topology) return <ErrorMessage message={error} onRetry={loadTopology} className="m-6" />;
  if (!topology) return null;

  return (
    <div className="h-[calc(100vh-4rem)] min-h-[700px] flex flex-col bg-control-bg">
      {/* Top Filter & Legend Bar */}
      <div className="bg-control-panel border-b border-control-border px-6 py-3 flex flex-wrap items-center justify-between gap-4 z-20">
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2 text-white text-xs font-bold uppercase tracking-wider">
            <Layers className="w-4 h-4 text-orange-500" />
            <span>GIS Grid Topology</span>
          </div>
          <span className="text-[11px] bg-slate-800 text-slate-300 border border-slate-700 px-2 py-0.5 rounded">
            Synthetic Coordinates (Bengaluru Grid Region)
          </span>
          <span className="text-[11px] bg-emerald-950/40 text-emerald-300 border border-emerald-600/40 px-2 py-0.5 rounded font-mono">
            {topology.sections.length} Sections &bull; {topology.transformers.length} DTs
          </span>
        </div>

        {/* Feeder Filter & Map Theme Toggle */}
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2">
            <span className="text-xs text-slate-400 font-medium">Filter Feeder:</span>
            <select
              value={selectedFeeder}
              onChange={(e) => setSelectedFeeder(e.target.value)}
              className="bg-control-card border border-control-border text-white text-xs rounded-lg px-2.5 py-1.5 focus:outline-none focus:border-orange-500"
            >
              <option value="ALL">All Feeders (8 Total)</option>
              {topology.feeders.map((f) => (
                <option key={f.id} value={f.id}>
                  {f.feeder_code} - {f.name}
                </option>
              ))}
            </select>
          </div>

          {/* Theme Toggle (OpenStreetMap vs Carto Dark) */}
          <button
            onClick={() => setMapTheme(mapTheme === 'osm' ? 'dark' : 'osm')}
            className="flex items-center gap-1.5 px-2.5 py-1.5 bg-control-card border border-control-border text-slate-300 hover:text-white rounded-lg text-xs font-medium transition"
            title="Toggle Map Tile Theme"
          >
            {mapTheme === 'osm' ? (
              <>
                <Moon className="w-3.5 h-3.5 text-indigo-400" />
                <span>Dark Tiles</span>
              </>
            ) : (
              <>
                <Sun className="w-3.5 h-3.5 text-amber-400" />
                <span>Street Tiles</span>
              </>
            )}
          </button>

          <button
            onClick={loadTopology}
            className="p-1.5 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded border border-slate-700 transition"
            title="Reload Network Topology"
          >
            <RefreshCw className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>

      {/* Map Container */}
      <div className="flex-1 w-full relative min-h-[600px]" style={{ height: 'calc(100vh - 8rem)' }}>
        <MapContainer
          center={center}
          zoom={13}
          scrollWheelZoom={true}
          style={{ height: '100%', minHeight: '600px', width: '100%', background: '#0B1120' }}
        >
          <MapResizerAndRecenter center={center} />

          {/* Map Tile Layer */}
          {mapTheme === 'osm' ? (
            <TileLayer
              attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
              url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
            />
          ) : (
            <TileLayer
              attribution='&copy; <a href="https://carto.com/">CartoDB</a>'
              url="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"
            />
          )}

          {/* 1. Feeder Sections (Polylines) */}
          {topology.sections.map((sec) => {
            const isCandidate = candidateSectionIds.includes(sec.id);
            const isAffected = affectedSectionIds.includes(sec.id);
            const isDeEnergized = sec.status === 'DE_ENERGIZED' || isAffected;

            let coords = null;
            if (sec.coordinates && Array.isArray(sec.coordinates) && sec.coordinates.length === 2) {
              coords = sec.coordinates;
            } else if (sec.start_latitude && sec.start_longitude && sec.end_latitude && sec.end_longitude) {
              coords = [[sec.start_latitude, sec.start_longitude], [sec.end_latitude, sec.end_longitude]];
            }

            if (!coords || !Number.isFinite(coords[0][0]) || !Number.isFinite(coords[0][1]) || 
                !Number.isFinite(coords[1][0]) || !Number.isFinite(coords[1][1])) {
              return null;
            }

            let strokeColor = '#0284C7'; // Healthy trunk blue
            let strokeWidth = 3;
            let opacity = 0.85;

            if (isCandidate) {
              strokeColor = '#F97316'; // Glowing candidate orange
              strokeWidth = 6;
              opacity = 1.0;
            } else if (isDeEnergized) {
              strokeColor = '#EF4444'; // Interrupted red
              strokeWidth = 4;
            }

            return (
              <Polyline
                key={`sec-${sec.id}`}
                positions={coords}
                pathOptions={{
                  color: strokeColor,
                  weight: strokeWidth,
                  opacity: opacity,
                  dashArray: isCandidate ? '8, 4' : null,
                }}
              >
                <Popup>
                  <div className="text-xs p-1 space-y-1">
                    <div className="font-bold text-slate-900 flex items-center justify-between gap-3">
                      <span>Section: {sec.section_code}</span>
                      {isCandidate && (
                        <span className="bg-orange-100 text-orange-800 px-1.5 py-0.5 rounded text-[10px] uppercase font-bold">
                          Candidate
                        </span>
                      )}
                    </div>
                    <div className="text-slate-600">
                      <div>Length: {sec.length_km} km</div>
                      <div>Conductor: {sec.conductor_type || 'ACSR'}</div>
                      <div>Capacity: {sec.rated_capacity_kva} kVA</div>
                      <div>Status: <strong>{sec.status}</strong></div>
                    </div>
                  </div>
                </Popup>
              </Polyline>
            );
          })}

          {/* 2. Substations */}
          {topology.substations.map((sub) => {
            if (!Number.isFinite(sub.latitude) || !Number.isFinite(sub.longitude)) return null;
            return (
              <Marker
                key={`sub-${sub.id}`}
                position={[sub.latitude, sub.longitude]}
                icon={createSubstationIcon(sub.code)}
              >
                <Popup>
                  <div className="text-xs p-1 space-y-1 text-slate-800">
                    <div className="font-bold text-base text-slate-900">{sub.name}</div>
                    <div>Code: <strong>{sub.code}</strong></div>
                    <div>Voltage: {sub.voltage_kv} kV</div>
                    <div>Capacity: {sub.capacity_mva} MVA</div>
                    <div>Division: {sub.division}</div>
                  </div>
                </Popup>
              </Marker>
            );
          })}

          {/* 3. Distribution Transformers (Circle Markers) */}
          {topology.transformers.map((dt) => {
            if (!Number.isFinite(dt.latitude) || !Number.isFinite(dt.longitude)) return null;
            const isOffline = dt.current_load_kva === 0;
            return (
              <CircleMarker
                key={`dt-${dt.id}`}
                center={[dt.latitude, dt.longitude]}
                radius={5}
                pathOptions={{
                  fillColor: isOffline ? '#EF4444' : '#10B981',
                  fillOpacity: 0.9,
                  color: '#FFFFFF',
                  weight: 1.5,
                }}
              >
                <Popup>
                  <div className="text-xs p-1 space-y-1 text-slate-800">
                    <div className="font-bold text-slate-900">Transformer: {dt.transformer_code}</div>
                    <div>Rated: {dt.rated_kva} kVA</div>
                    <div>Current Load: {dt.current_load_kva} kVA</div>
                    <div>Load Percentage: {dt.load_percentage}%</div>
                    <div>Status: <strong>{isOffline ? 'DE-ENERGIZED (0V)' : 'HEALTHY (230V)'}</strong></div>
                  </div>
                </Popup>
              </CircleMarker>
            );
          })}

          {/* 4. Critical Facilities */}
          {topology.critical_loads.map((crit) => {
            const sec = topology.sections.find(s => s.id === crit.section_id);
            if (!sec) return null;
            let lat = sec.end_latitude;
            let lng = sec.end_longitude;
            if ((!lat || !lng) && sec.coordinates && sec.coordinates[1]) {
              lat = sec.coordinates[1][0];
              lng = sec.coordinates[1][1];
            }
            if (!Number.isFinite(lat) || !Number.isFinite(lng)) return null;

            return (
              <Marker
                key={`crit-${crit.id}`}
                position={[lat, lng]}
                icon={createCriticalLoadIcon(crit.facility_name, crit.priority_tier)}
              >
                <Popup>
                  <div className="text-xs p-1 space-y-1 text-slate-800">
                    <div className="font-bold text-rose-700 text-sm">Critical Load: {crit.facility_name}</div>
                    <div>Facility Type: {crit.facility_type}</div>
                    <div>Priority Tier: Tier {crit.priority_tier} (Life/Essential)</div>
                    <div>Generator Backup: {crit.backup_generator_present ? 'Present (8 hrs)' : 'None'}</div>
                    <div>Contact: {crit.contact_number || 'N/A'}</div>
                  </div>
                </Popup>
              </Marker>
            );
          })}

          {/* 5. Normally-Open Tie Switches */}
          {topology.tie_switches.map((tie) => {
            const fromSec = topology.sections.find(s => s.id === tie.from_section_id);
            if (!fromSec) return null;
            let lat = fromSec.end_latitude;
            let lng = fromSec.end_longitude;
            if ((!lat || !lng) && fromSec.coordinates && fromSec.coordinates[1]) {
              lat = fromSec.coordinates[1][0];
              lng = fromSec.coordinates[1][1];
            }
            if (!Number.isFinite(lat) || !Number.isFinite(lng)) return null;

            return (
              <Marker
                key={`tie-${tie.id}`}
                position={[lat, lng]}
                icon={createTieSwitchIcon(tie.switch_code)}
              >
                <Popup>
                  <div className="text-xs p-1 space-y-1 text-slate-800">
                    <div className="font-bold text-slate-900">Normally-Open Tie Switch</div>
                    <div>Switch Code: <strong>{tie.switch_code}</strong></div>
                    <div>State: <strong>NORMALLY OPEN (Radial Invariant)</strong></div>
                    <div className="text-slate-600">Available for back-feed restoration on adjacent feeder.</div>
                  </div>
                </Popup>
              </Marker>
            );
          })}
        </MapContainer>

        {/* Floating Status Legend */}
        <div className="absolute bottom-4 right-4 bg-control-panel/95 border border-control-border backdrop-blur-md rounded-xl p-3 shadow-xl z-[1000] text-xs space-y-2 text-slate-300 w-56">
          <div className="font-bold text-white text-[11px] uppercase tracking-wider pb-1 border-b border-control-border">
            GIS Grid Legend
          </div>
          <div className="flex items-center gap-2">
            <span className="w-3.5 h-1 bg-[#0284C7] rounded-full inline-block" />
            <span>Energized 11kV Trunk</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="w-3.5 h-1.5 bg-[#F97316] rounded-full inline-block animate-pulse" />
            <span className="text-orange-400 font-bold">Topology Candidate</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="w-3.5 h-1 bg-[#EF4444] rounded-full inline-block" />
            <span>De-Energized Branch</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="w-2.5 h-2.5 rounded-full bg-emerald-500 inline-block border border-white" />
            <span>Healthy DT (230V)</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="w-2.5 h-2.5 rounded-full bg-rose-500 inline-block border border-white" />
            <span>Zero-Volt DT (Offline)</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-xs">⚡</span>
            <span>66/11kV Substation</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-xs">🚨</span>
            <span className="text-rose-400 font-bold">Critical Load (Hospital/Pump)</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-[10px] text-slate-400">⚲ NO</span>
            <span>Tie Switch (Normally Open)</span>
          </div>
        </div>
      </div>
    </div>
  );
}
