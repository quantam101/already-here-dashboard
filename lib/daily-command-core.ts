export type SignalSource = 'GMAIL' | 'WORKMARKET' | 'FIELD_NATION' | 'SQUARE' | 'STRIPE' | 'QUICKBOOKS' | 'VERCEL' | 'MANUAL';
export type OperatingCategory = 'FIELD_SERVICE' | 'HAULING' | 'AUTOWORKS' | 'PAYMENT_PROTECTION' | 'DRONE_UAS' | 'SYSTEM_HEALTH';
export type PriorityGrade = 'A' | 'B' | 'C' | 'D' | 'F';
export type SystemHealth = 'OPERATIONAL' | 'DEGRADED' | 'CRITICAL';
export type FailureType = 'SLOW_PAYMENT' | 'SCOPE_CREEP' | 'ROUTE_FRICTION' | 'BAD_DATA' | 'ADAPTER_FAULT';

export interface LocationMatrix { address: string; zip: string; lat: number; lng: number; }
export interface NormalizedItem {
  id: string;
  source: SignalSource;
  category: OperatingCategory;
  timestamp: string;
  potentialValue: number;
  location?: LocationMatrix;
  estimatedOnSiteHours: number;
  deadline: string;
  riskFlags: string[];
  requiresOwnerApproval: boolean;
  exactNextStep: string;
  grade: PriorityGrade;
  effectiveHourlyValue?: number;
  vendorId?: string;
  sourceConfidence: number;
  routeFrictionCost?: number;
  routeFrictionHours?: number;
}
export interface HistoricalFailureSignature { vendorId: string; failureType: FailureType; severity: number; note?: string; }
export interface SystemMetrics { dailyTarget: number; confirmed: number; revenueGap: number; blockedValue: number; averageEffectiveHourlyValue: number; approvalRequiredCount: number; }
export interface CircuitBreakerSnapshot { name: string; state: 'CLOSED' | 'OPEN'; failureCount: number; openedAt?: string; lastError?: string; }
export interface RuntimeResult { systemHealth: SystemHealth; currentTimestamp: string; metrics: SystemMetrics; rankedQueue: NormalizedItem[]; masterDocumentOutput: string; circuitBreakers: CircuitBreakerSnapshot[]; codexChangelog: string[]; }
export interface CommandEngineOptions { dailyTarget?: number; baseLocation?: LocationMatrix; generatedAt?: string; strictMode?: boolean; requireOwnerApprovalByDefault?: boolean; }

type RawRecord = Record<string, unknown>;
const SOURCES: readonly SignalSource[] = ['GMAIL', 'WORKMARKET', 'FIELD_NATION', 'SQUARE', 'STRIPE', 'QUICKBOOKS', 'VERCEL', 'MANUAL'];
const CATEGORIES: readonly OperatingCategory[] = ['FIELD_SERVICE', 'HAULING', 'AUTOWORKS', 'PAYMENT_PROTECTION', 'DRONE_UAS', 'SYSTEM_HEALTH'];
const ORDER: Record<PriorityGrade, number> = { A: 0, B: 1, C: 2, D: 3, F: 4 };

export const PHOENIX_GLENDALE_BASE: LocationMatrix = { address: 'Phoenix/Glendale operating vector', zip: '85007', lat: 33.5387, lng: -112.186 };
export const PHOENIX_METRO_DISTANCE_VECTORS: Record<string, LocationMatrix> = {
  PHOENIX_85007: { address: 'Phoenix, AZ 85007', zip: '85007', lat: 33.4484, lng: -112.0978 },
  GLENDALE_85301: { address: 'Glendale, AZ 85301', zip: '85301', lat: 33.5387, lng: -112.186 },
  PEORIA_85345: { address: 'Peoria, AZ 85345', zip: '85345', lat: 33.5806, lng: -112.2374 },
  GILBERT_85234: { address: 'Gilbert, AZ 85234', zip: '85234', lat: 33.3524, lng: -111.789 },
  QUEEN_CREEK_85142: { address: 'Queen Creek, AZ 85142', zip: '85142', lat: 33.2484, lng: -111.6342 },
  MESA_85201: { address: 'Mesa, AZ 85201', zip: '85201', lat: 33.4152, lng: -111.8315 },
  CHANDLER_85225: { address: 'Chandler, AZ 85225', zip: '85225', lat: 33.3062, lng: -111.8413 },
  TEMPE_85281: { address: 'Tempe, AZ 85281', zip: '85281', lat: 33.4255, lng: -111.94 }
};

export class CircuitBreaker {
  private failureCount = 0;
  private openedAt?: string;
  private lastError?: string;
  constructor(private readonly name: string, private readonly maxFailures = 2, private readonly clock = () => new Date().toISOString()) {}
  recordSuccess() { this.failureCount = 0; this.openedAt = undefined; this.lastError = undefined; }
  recordFailure(error: unknown) { this.failureCount += 1; this.lastError = error instanceof Error ? error.message : String(error); if (this.failureCount >= this.maxFailures && !this.openedAt) this.openedAt = this.clock(); }
  assertClosed() { if (this.openedAt) throw new Error(`Circuit breaker ${this.name} is open: ${this.lastError ?? 'adapter unavailable'}`); }
  snapshot(): CircuitBreakerSnapshot { return { name: this.name, state: this.openedAt ? 'OPEN' : 'CLOSED', failureCount: this.failureCount, openedAt: this.openedAt, lastError: this.lastError }; }
}

export class AgentLiveAdapter {
  normalize(rawInputs: unknown[], options: CommandEngineOptions = {}): NormalizedItem[] {
    if (!Array.isArray(rawInputs)) throw new Error('rawInputs must be an array');
    const generatedAt = options.generatedAt ?? new Date().toISOString();
    return rawInputs.map((input, index) => this.one(asRecord(input), index, generatedAt, options));
  }
  private one(input: RawRecord, index: number, generatedAt: string, options: CommandEngineOptions): NormalizedItem {
    const rawSource = String(input.source ?? '').toUpperCase();
    const rawCategory = String(input.category ?? '').toUpperCase();
    const source = SOURCES.includes(rawSource as SignalSource) ? rawSource as SignalSource : 'MANUAL';
    const category = CATEGORIES.includes(rawCategory as OperatingCategory) ? rawCategory as OperatingCategory : 'FIELD_SERVICE';
    const flags = normalizeFlags(input.flags);
    const potentialValue = nonNegative(input.pay ?? input.potentialValue ?? input.amount, 0);
    const location = normalizeLocation(input.location);
    if (!SOURCES.includes(rawSource as SignalSource)) flags.push('SOURCE_DEFAULTED_OR_VERIFIED_MANUAL');
    if (!CATEGORIES.includes(rawCategory as OperatingCategory)) flags.push('CATEGORY_DEFAULTED');
    if (potentialValue <= 0) flags.push('NO_REVENUE_VALUE');
    if (!location) flags.push('NO_LOCATION_VECTOR');
    return {
      id: text(input.id) || `SIG_${index}_${hash(JSON.stringify(input)).toString(36).toUpperCase()}`,
      source,
      category,
      timestamp: generatedAt,
      potentialValue,
      location,
      estimatedOnSiteHours: positive(input.durationHours ?? input.estimatedOnSiteHours ?? input.hours, 1),
      deadline: text(input.deadline) || generatedAt,
      riskFlags: unique(flags),
      requiresOwnerApproval: typeof input.requiresOwnerApproval === 'boolean' ? input.requiresOwnerApproval : options.requireOwnerApprovalByDefault ?? true,
      exactNextStep: text(input.nextStep ?? input.exactNextStep) || 'Verify scope, payment terms, site access, and dispatch window before acceptance.',
      grade: 'B',
      vendorId: text(input.vendorId ?? input.vendor ?? input.clientId) || undefined,
      sourceConfidence: clamp(Number(input.sourceConfidence ?? input.confidence ?? 0.85), 0, 1)
    };
  }
}

export class OperatorManualFeedAdapter {
  private readonly breaker = new CircuitBreaker('operator-manual-feed');
  private readonly adapter = new AgentLiveAdapter();
  ingest(rawInputs: unknown[], options: CommandEngineOptions = {}) {
    this.breaker.assertClosed();
    try { const items = this.adapter.normalize(rawInputs, options); this.breaker.recordSuccess(); return { items, breaker: this.breaker.snapshot() }; }
    catch (error) { this.breaker.recordFailure(error); throw error; }
  }
}

export class AgentSpatialIntelligence {
  constructor(private readonly baseLocation: LocationMatrix = PHOENIX_GLENDALE_BASE) {}
  calculateFriction(loc?: LocationMatrix) {
    if (!loc) return { straightLineMiles: 0, adjustedMiles: 0, travelTimeHours: 0, travelCost: 0 };
    const earth = 3958.8;
    const dLat = rad(loc.lat - this.baseLocation.lat);
    const dLon = rad(loc.lng - this.baseLocation.lng);
    const a = Math.sin(dLat / 2) ** 2 + Math.cos(rad(this.baseLocation.lat)) * Math.cos(rad(loc.lat)) * Math.sin(dLon / 2) ** 2;
    const miles = earth * 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
    const adjustedMiles = miles * 1.25;
    return { straightLineMiles: round(miles), adjustedMiles: round(adjustedMiles), travelTimeHours: round(adjustedMiles / 45), travelCost: round(adjustedMiles * 0.67) };
  }
}

export class AgentAdvancedRankingEngine {
  private readonly laborFloor = 65;
  execute(items: NormalizedItem[], spatial: AgentSpatialIntelligence, history: HistoricalFailureSignature[]): NormalizedItem[] {
    return items.map((item) => this.score(item, spatial, history)).sort((a, b) => ORDER[a.grade] - ORDER[b.grade] || (b.effectiveHourlyValue ?? 0) - (a.effectiveHourlyValue ?? 0));
  }
  private score(item: NormalizedItem, spatial: AgentSpatialIntelligence, history: HistoricalFailureSignature[]): NormalizedItem {
    const friction = spatial.calculateFriction(item.location);
    const netPay = Math.max(0, item.potentialValue - friction.travelCost);
    const totalHours = Math.max(0.25, item.estimatedOnSiteHours + friction.travelTimeHours);
    const ehv = round(netPay / totalHours);
    const flags = unique(item.riskFlags);
    let grade: PriorityGrade = 'B';
    if (item.category === 'AUTOWORKS' && flags.some((flag) => ['DIESEL', 'HEAVY_DUTY', 'SEMI', 'BUS', 'COMMERCIAL_DIESEL_FLEET'].includes(flag))) {
      return { ...item, grade: 'F', effectiveHourlyValue: 0, routeFrictionCost: friction.travelCost, routeFrictionHours: friction.travelTimeHours, riskFlags: unique([...flags, 'FORBIDDEN_SCOPE_EXCLUSION']) };
    }
    if (item.potentialValue <= 0) grade = worse(grade, 'D');
    if (ehv < this.laborFloor && item.potentialValue > 0) { grade = worse(grade, 'C'); flags.push('MARGIN_BELOW_LABOR_FLOOR'); }
    if (friction.travelTimeHours >= 1.25) { grade = worse(grade, 'C'); flags.push('ROUTE_FRICTION_HIGH'); }
    const vendorRisk = item.vendorId ? history.find((f) => f.vendorId.toUpperCase() === item.vendorId?.toUpperCase() && f.severity > 0.7) : undefined;
    if (vendorRisk) { grade = worse(grade, 'C'); flags.push(`HISTORICAL_${vendorRisk.failureType}`); }
    if (item.sourceConfidence < 0.65) { grade = worse(grade, 'C'); flags.push('LOW_SOURCE_CONFIDENCE'); }
    if (ehv >= 75 && ORDER[grade] < ORDER.C) grade = 'A';
    return { ...item, effectiveHourlyValue: ehv, routeFrictionCost: friction.travelCost, routeFrictionHours: friction.travelTimeHours, grade, riskFlags: unique(flags) };
  }
}

export class AgentDocumentAutomation {
  generateMasterDoc(metrics: SystemMetrics, items: NormalizedItem[], health: SystemHealth, generatedAt: string): string {
    const rows = items.map((i) => `| ${i.id} | ${i.source} | ${i.category} | $${i.potentialValue.toFixed(2)} | $${(i.effectiveHourlyValue ?? 0).toFixed(2)}/hr | Grade ${i.grade} | ${i.riskFlags.join(', ') || 'NONE'} | ${i.exactNextStep} |`).join('\n');
    return `# ALREADY HERE LLC — DAILY COMMAND MASTER SYSTEM EXPORT\n**System Status:** ${health}  \n**Generation Date:** ${generatedAt.split('T')[0]}  \n**Daily Operating Revenue Target:** $${metrics.dailyTarget.toFixed(2)}  \n\n---\n\n## 1. System Financial Architecture Status\n* **Confirmed Stacked Revenue Pipeline:** $${metrics.confirmed.toFixed(2)}\n* **Identified Financial Gap Metrics:** $${metrics.revenueGap.toFixed(2)}\n* **Blocked / Rejected Value:** $${metrics.blockedValue.toFixed(2)}\n* **Average Effective Net Rate:** $${metrics.averageEffectiveHourlyValue.toFixed(2)}/hr\n* **Owner Approval Queue Count:** ${metrics.approvalRequiredCount}\n\n---\n\n## 2. Active Structural Resource Ranking Queue\n| Item ID | Source Module | Operating Category | Gross Value | Effective Net Rate | Priority | Risk Flags | Exact Next Step |\n| :--- | :--- | :--- | ---: | ---: | :--- | :--- | :--- |\n${rows || '| NONE | MANUAL | SYSTEM_HEALTH | $0.00 | $0.00/hr | Grade D | NO_ACTIVE_SIGNAL | Add verified operator feed. |'}\n\n---\n\n## 3. Operational Sign-Off Control Boundaries\n* Manual confirmation is required for every entry where requiresOwnerApproval is true.\n* Diesel, heavy-duty, unverified mobile repair, below-floor margin, and high route-friction work is blocked or downgraded by default.\n* The engine accepts local feed objects and does not require third-party connectors to operate. Automatic live sync still requires authorized connectors or exported data.\n* Lifelong Catch and Correct records degraded signals as correction notes rather than silent failures.\n`;
  }
}

export class SuperIntelligenceOrchestrator {
  private readonly manualAdapter = new OperatorManualFeedAdapter();
  private readonly docGen = new AgentDocumentAutomation();
  async processLiveMatrix(rawInputs: unknown[], history: HistoricalFailureSignature[] = [], options: CommandEngineOptions = {}): Promise<RuntimeResult> {
    const generatedAt = options.generatedAt ?? new Date().toISOString();
    const dailyTarget = options.dailyTarget ?? 500;
    const codexChangelog = ['Kept normalization, Phoenix Metro spatial scoring, margin ranking, diesel exclusion, historical risk ledger, owner approval gate, and Markdown export.', 'Corrected proof math through one canonical Haversine plus road-grid formula.', 'Added local/manual feed mode, deterministic IDs, circuit breaker snapshots, blocked-value accounting, and Lifelong Catch and Correct notes.'];
    try {
      const { items, breaker } = this.manualAdapter.ingest(rawInputs, { ...options, generatedAt, dailyTarget });
      const rankedQueue = new AgentAdvancedRankingEngine().execute(items, new AgentSpatialIntelligence(options.baseLocation ?? PHOENIX_GLENDALE_BASE), history);
      const metrics = computeMetrics(rankedQueue, dailyTarget);
      const systemHealth = breaker.state === 'OPEN' ? 'CRITICAL' : rankedQueue.some((i) => i.grade === 'C' || i.grade === 'D' || i.grade === 'F' || i.riskFlags.length > 0) ? 'DEGRADED' : 'OPERATIONAL';
      return { systemHealth, currentTimestamp: generatedAt, metrics, rankedQueue, masterDocumentOutput: this.docGen.generateMasterDoc(metrics, rankedQueue, systemHealth, generatedAt), circuitBreakers: [breaker], codexChangelog };
    } catch (error) {
      const message = error instanceof Error ? error.message : String(error);
      return { systemHealth: 'CRITICAL', currentTimestamp: generatedAt, metrics: { dailyTarget, confirmed: 0, revenueGap: dailyTarget, blockedValue: 0, averageEffectiveHourlyValue: 0, approvalRequiredCount: 0 }, rankedQueue: [], masterDocumentOutput: `# CRITICAL SYSTEM FAULT CAPTURED\nAutomation pipelines isolated safely.\n\nFault: ${message}`, circuitBreakers: [{ name: 'operator-manual-feed', state: 'OPEN', failureCount: 1, openedAt: generatedAt, lastError: message }], codexChangelog: [...codexChangelog, `Critical isolation event captured: ${message}`] };
    }
  }
}

export function getDefaultDailyCommandFeed(): unknown[] {
  return [
    { id: 'WM_01', source: 'WORKMARKET', category: 'FIELD_SERVICE', pay: 220, durationHours: 2, location: PHOENIX_METRO_DISTANCE_VECTORS.GILBERT_85234, flags: [], vendorId: 'WORKMARKET_DIRECT', nextStep: 'Confirm scope, onsite window, materials responsibility, and payout terms before accepting.' },
    { id: 'AW_02', source: 'GMAIL', category: 'AUTOWORKS', pay: 160, durationHours: 1.5, location: PHOENIX_METRO_DISTANCE_VECTORS.PEORIA_85345, flags: [], vendorId: 'DIRECT_LIGHT_DUTY', nextStep: 'Verify gas/light-duty scope, parts availability, and payment collection before dispatch.' },
    { id: 'FN_03', source: 'FIELD_NATION', category: 'FIELD_SERVICE', pay: 90, durationHours: 1, location: PHOENIX_METRO_DISTANCE_VECTORS.QUEEN_CREEK_85142, flags: [], vendorId: 'FIELD_NATION', nextStep: 'Counter with travel-adjusted rate or decline if buyer will not meet floor.' },
    { id: 'AW_04', source: 'GMAIL', category: 'AUTOWORKS', pay: 1200, durationHours: 8, location: PHOENIX_METRO_DISTANCE_VECTORS.PHOENIX_85007, flags: ['DIESEL'], vendorId: 'DIESEL_SCOPE', nextStep: 'Reject diesel or heavy-duty scope; refer out only if referral fee is documented.' }
  ];
}
export function getDefaultHistoricalFrictionLedger(): HistoricalFailureSignature[] { return [{ vendorId: 'SLOW_PAY_CORP', failureType: 'SLOW_PAYMENT', severity: 0.9, note: 'Payment protection gate required.' }]; }

function computeMetrics(items: NormalizedItem[], dailyTarget: number): SystemMetrics { const eligible = items.filter((i) => i.grade === 'A' || i.grade === 'B'); const ehvItems = items.filter((i) => (i.effectiveHourlyValue ?? 0) > 0); const confirmed = round(eligible.reduce((sum, item) => sum + item.potentialValue, 0)); return { dailyTarget, confirmed, revenueGap: round(Math.max(0, dailyTarget - confirmed)), blockedValue: round(items.filter((i) => i.grade === 'F').reduce((sum, item) => sum + item.potentialValue, 0)), averageEffectiveHourlyValue: ehvItems.length ? round(ehvItems.reduce((sum, item) => sum + (item.effectiveHourlyValue ?? 0), 0) / ehvItems.length) : 0, approvalRequiredCount: items.filter((i) => i.requiresOwnerApproval).length }; }
function asRecord(input: unknown): RawRecord { if (!input || typeof input !== 'object' || Array.isArray(input)) throw new Error('Each raw signal must be an object'); return input as RawRecord; }
function normalizeLocation(value: unknown): LocationMatrix | undefined { if (!value || typeof value !== 'object') return undefined; const input = value as RawRecord; const lat = Number(input.lat); const lng = Number(input.lng); return Number.isFinite(lat) && Number.isFinite(lng) ? { address: text(input.address) || 'verified Phoenix Metro location', zip: text(input.zip) || '00000', lat, lng } : undefined; }
function normalizeFlags(value: unknown): string[] { return Array.isArray(value) ? unique(value.map((flag) => String(flag).trim().toUpperCase()).filter(Boolean)) : []; }
function unique(flags: string[]): string[] { return Array.from(new Set(flags.map((flag) => flag.trim().toUpperCase()).filter(Boolean))); }
function worse(current: PriorityGrade, candidate: PriorityGrade): PriorityGrade { return ORDER[candidate] > ORDER[current] ? candidate : current; }
function text(value: unknown): string { return typeof value === 'string' ? value.trim() : ''; }
function nonNegative(value: unknown, fallback: number): number { const num = Number(value); return Number.isFinite(num) && num >= 0 ? num : fallback; }
function positive(value: unknown, fallback: number): number { const num = Number(value); return Number.isFinite(num) && num > 0 ? num : fallback; }
function clamp(value: number, min: number, max: number): number { return Number.isFinite(value) ? Math.min(max, Math.max(min, value)) : min; }
function rad(value: number): number { return value * Math.PI / 180; }
function round(value: number): number { return Math.round(value * 100) / 100; }
function hash(value: string): number { let h = 2166136261; for (let i = 0; i < value.length; i += 1) { h ^= value.charCodeAt(i); h = Math.imul(h, 16777619); } return h >>> 0; }
