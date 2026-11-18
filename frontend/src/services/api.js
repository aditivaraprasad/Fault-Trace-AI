/**
 * Centralized API client for FAULTTRACE AI.
 * Communicates exclusively with the FastAPI backend.
 * Handles timeouts, normalization, and structured error propagation.
 */

const BASE_URL = '/api/v1';

async function request(endpoint, options = {}) {
  const url = `${BASE_URL}${endpoint}`;
  const config = {
    ...options,
    headers: {
      'Accept': 'application/json',
      ...options.headers,
    },
  };

  try {
    const response = await fetch(url, config);
    if (!response.ok) {
      let errorDetail = `HTTP ${response.status} ${response.statusText}`;
      try {
        const errorJson = await response.json();
        errorDetail = errorJson.detail || JSON.stringify(errorJson);
      } catch {
        // Fallback to text
        const text = await response.text();
        if (text) errorDetail = text;
      }
      const err = new Error(errorDetail);
      err.status = response.status;
      throw err;
    }
    return await response.json();
  } catch (error) {
    console.error(`[API Error] ${options.method || 'GET'} ${url}:`, error.message);
    throw error;
  }
}

export const api = {
  // 0. System Health
  getHealth: () => request('/health'),

  // 1. Dashboard & Grid Health
  getDashboardStats: () => request('/dashboard/stats'),

  // 2. Network Topology & Graph
  getTopology: (feederId = null) => {
    const q = feederId ? `?feeder_id=${feederId}` : '';
    return request(`/network/topology${q}`);
  },

  localizeGraph: (data) => request('/network/localize/graph', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  }),

  // 3. Feeders & Assets
  getFeeders: () => request('/feeders'),
  getFeeder: (id) => request(`/feeders/${id}`),

  getAssets: (params = {}) => {
    const query = new URLSearchParams();
    if (params.asset_type) query.append('asset_type', params.asset_type);
    if (params.condition_rating) query.append('condition_rating', params.condition_rating);
    if (params.min_health_index !== undefined && params.min_health_index !== '') {
      query.append('min_health_index', params.min_health_index);
    }
    if (params.max_health_index !== undefined && params.max_health_index !== '') {
      query.append('max_health_index', params.max_health_index);
    }
    if (params.identifier) query.append('identifier', params.identifier);
    if (params.limit) query.append('limit', params.limit);
    const qs = query.toString();
    return request(`/assets${qs ? `?${qs}` : ''}`);
  },

  getAsset: (id) => request(`/assets/${id}`),

  // 4. Incidents & Localization
  getIncidents: (params = {}) => {
    const query = new URLSearchParams();
    if (params.feeder_id) query.append('feeder_id', params.feeder_id);
    if (params.status) query.append('status', params.status);
    if (params.limit) query.append('limit', params.limit || 50);
    const qs = query.toString();
    return request(`/incidents${qs ? `?${qs}` : ''}`);
  },

  getIncident: (id) => request(`/incidents/${id}`),

  localizeIncident: (id) => request(`/incidents/${id}/localize`, {
    method: 'POST',
  }),

  getIncidentExplanation: (id) => request(`/incidents/${id}/explanation`),
  getIncidentAssets: (id) => request(`/incidents/${id}/assets`),
  getIncidentRestoration: (id) => request(`/incidents/${id}/restoration`),

  // 5. Scenario Simulation
  simulateScenario: (scenarioType = 'f4_hero', customData = {}) => request('/simulate/scenario', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      scenario_type: scenarioType,
      feeder_code: customData.feeder_code || 'F4',
      complaint_count: customData.complaint_count || (scenarioType === 'f4_hero' ? 142 : undefined),
      wind_speed_kmh: customData.wind_speed_kmh || (scenarioType === 'f4_hero' ? 48.0 : undefined),
      noise_level: customData.noise_level || 0.05,
    }),
  }),

  // 6. Weather Telemetry
  getCurrentWeather: () => request('/weather/current'),
  fetchWeather: (forceSynthetic = false) => request(`/weather/fetch?force_synthetic=${forceSynthetic}`, {
    method: 'POST',
  }),

  // 7. Model Metrics & Evaluation
  getModelMetrics: () => request('/model/metrics'),

  // 8. CSV Ingestion
  uploadCsv: async (datasetType, file) => {
    const formData = new FormData();
    formData.append('file', file);
    const response = await fetch(`${BASE_URL}/ingest/${datasetType}`, {
      method: 'POST',
      body: formData,
    });
    if (!response.ok) {
      let errText = `Upload failed with status ${response.status}`;
      try {
        const j = await response.json();
        errText = j.detail || JSON.stringify(j);
      } catch {
        errText = await response.text();
      }
      const e = new Error(errText);
      e.status = response.status;
      throw e;
    }
    return await response.json();
  },
};
