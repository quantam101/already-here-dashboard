// Chart configuration constants
export const CHART_AXIS_FONT_SIZE = 11;
export const CHART_HEIGHT_PX = 200;

export const CHART_TICK_STYLE = { fill: '#6b7280', fontSize: CHART_AXIS_FONT_SIZE };

export const CHART_TOOLTIP_STYLE = {
  background: 'rgba(23, 27, 40, 0.95)',
  border: '1px solid rgba(34, 197, 94, 0.2)',
  borderRadius: '8px',
  color: '#fff',
};

export const CHART_CURSOR_STYLE = { fill: 'rgba(34, 197, 94, 0.1)' };

export const CHART_BAR_RADIUS = [4, 4, 0, 0];

export const ACTIVITY_TYPES = {
  success: 'bg-green-400',
  pending: 'bg-yellow-400',
  info: 'bg-blue-400',
};

// Revenue chart generation constants
export const REVENUE_CHART_DAYS = 14;
export const REVENUE_CHART_MIN = 100;
export const REVENUE_CHART_RANGE = 200;

// Days in month for daily average calculation
export const DAYS_PER_MONTH = 30;

// Stream health calculation constants
export const HEALTH_BASE = 85;
export const HEALTH_INCREMENT_FACTOR = 7;
export const HEALTH_INCREMENT_RANGE = 15;
export const TREND_DOWN_INTERVAL = 3;

// Health threshold tiers
export const HEALTH_THRESHOLD_EXCELLENT = 95;
export const HEALTH_THRESHOLD_GOOD = 85;
export const HEALTH_THRESHOLD_FAIR = 70;

// React Query config
export const QUERY_STALE_TIME_MS = 30000;
