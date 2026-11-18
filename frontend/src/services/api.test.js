import { describe, it, expect, vi, beforeEach } from 'vitest';
import { api } from './api';

describe('API Service Client', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it('getDashboardStats requests /api/v1/dashboard/stats', async () => {
    const mockData = { total_substations: 2, total_feeders: 8, active_incidents_count: 1 };
    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => mockData,
    });

    const result = await api.getDashboardStats();
    expect(global.fetch).toHaveBeenCalledWith('/api/v1/dashboard/stats', expect.objectContaining({
      headers: expect.objectContaining({ 'Accept': 'application/json' })
    }));
    expect(result).toEqual(mockData);
  });

  it('simulateScenario posts to /api/v1/simulate/scenario with f4_hero preset', async () => {
    const mockSim = { scenario_type: 'f4_hero', incident_id: 42 };
    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => mockSim,
    });

    const result = await api.simulateScenario('f4_hero');
    expect(global.fetch).toHaveBeenCalledWith('/api/v1/simulate/scenario', expect.objectContaining({
      method: 'POST',
      body: JSON.stringify({
        scenario_type: 'f4_hero',
        feeder_code: 'F4',
        complaint_count: 142,
        wind_speed_kmh: 48.0,
        noise_level: 0.05,
      }),
    }));
    expect(result).toEqual(mockSim);
  });

  it('propagates HTTP error message on failure', async () => {
    global.fetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 404,
      statusText: 'Not Found',
      json: async () => ({ detail: 'Incident not found' }),
    });

    await expect(api.getIncident(999)).rejects.toThrow('Incident not found');
  });
});
