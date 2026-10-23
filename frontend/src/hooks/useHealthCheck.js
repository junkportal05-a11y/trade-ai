import { useState, useEffect, useCallback } from 'react';
import { API_BASE_URL } from '../api';

export function useHealthCheck(pollIntervalMs = 20000) {
  const [health, setHealth] = useState({
    status: 'checking',
    checks: null,
    latencyMs: null,
    lastChecked: null,
    error: null,
  });

  const checkHealth = useCallback(async () => {
    const t0 = performance.now();
    try {
      const res = await fetch(`${API_BASE_URL}/api/health`, {
        headers: { 'Accept': 'application/json' },
      });
      const latencyMs = Math.round(performance.now() - t0);
      if (res.ok) {
        const data = await res.json();
        setHealth({
          status: data.status || 'healthy',
          checks: data.checks || null,
          version: data.version,
          environment: data.environment,
          latencyMs,
          lastChecked: new Date(),
          error: null,
        });
      } else {
        setHealth(prev => ({
          ...prev,
          status: 'degraded',
          latencyMs,
          lastChecked: new Date(),
          error: `HTTP ${res.status}`,
        }));
      }
    } catch (err) {
      setHealth({
        status: 'offline',
        checks: null,
        latencyMs: null,
        lastChecked: new Date(),
        error: err.message || 'Connection failed',
      });
    }
  }, []);

  useEffect(() => {
    checkHealth();
    if (pollIntervalMs > 0) {
      const interval = setInterval(checkHealth, pollIntervalMs);
      return () => clearInterval(interval);
    }
  }, [checkHealth, pollIntervalMs]);

  return { ...health, refresh: checkHealth };
}
