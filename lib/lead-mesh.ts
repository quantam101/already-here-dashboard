import type { LeadDecisionStatus, LeadGrade, LeadOpportunity, LeadSourceType, OpportunityCategory, Skill } from './types';

export const revenueRules = {
  minimumHourly: 65,
  minimumDispatch: 130,
  preferredHourly: 95,
  preferredRetainer: 1500,
  preferredRadiusMiles: 60
} as const;

const compliantSourceTypes: LeadSourceType[] = [
  'authorized_email',
  'official_portal',
  'public_procurement',
  'partner_channel',
  'manual_public_listing'
];

export interface LeadIntake {
  source: string;
  sourceType: LeadSourceType;
  category: OpportunityCategory;
  organization: string;
  title: string;
  url?: string;
  location: string;
  metro: string;
  deadline?: string;
  requiredSkills: Skill[];
  expectedValue: number;
  estimatedHours: number;
  decisionStatus?: LeadDecisionStatus;
  notes?: string;
}

export function buildLeadOpportunity(input: LeadIntake): LeadOpportunity {
  const estimatedHours = Math.max(input.estimatedHours, 1);
  const effectiveHourly = Math.round((input.expectedValue / estimatedHours) * 100) / 100;
  const minimumAcceptableValue = getMinimumAcceptableValue(input.category, estimatedHours);
  const riskFlags = getRiskFlags(input, effectiveHourly, minimumAcceptableValue);
  const grade = gradeLead(input, effectiveHourly, riskFlags);
  const counterRequired = input.expectedValue < minimumAcceptableValue || effectiveHourly < revenueRules.minimumHourly;

  return {
    id: stableLeadId(input),
    capturedAt: new Date().toISOString(),
    source: input.source,
    sourceType: input.sourceType,
    category: input.category,
    organization: input.organization,
    title: input.title,
    url: input.url,
    location: input.location,
    metro: input.metro,
    deadline: input.deadline,
    requiredSkills: input.requiredSkills,
    expectedValue: input.expectedValue,
    estimatedHours,
    effectiveHourly,
    minimumAcceptableValue,
    grade,
    confidence: getConfidence(grade, riskFlags),
    decisionStatus: input.decisionStatus ?? 'new',
    riskFlags,
    counterRequired,
    nextAction: getNextAction(input, grade, counterRequired),
    counterMessage: getCounterMessage(input, minimumAcceptableValue),
    complianceMode: getComplianceMode(input.sourceType),
    notes: input.notes ?? ''
  };
}

export function rankLeadOpportunities(leads: LeadOpportunity[]): LeadOpportunity[] {
  const rankWeight: Record<LeadGrade, number> = { A: 4, B: 3, C: 2, Avoid: 0 };
  return dedupeLeadOpportunities(leads)
    .filter((lead) => lead.decisionStatus !== 'discard' && lead.decisionStatus !== 'lost')
    .sort((a, b) => {
      const gradeDelta = rankWeight[b.grade] - rankWeight[a.grade];
      if (gradeDelta !== 0) return gradeDelta;
      const valueDelta = b.expectedValue - a.expectedValue;
      if (valueDelta !== 0) return valueDelta;
      return new Date(b.capturedAt).getTime() - new Date(a.capturedAt).getTime();
    });
}

export function dedupeLeadOpportunities(leads: LeadOpportunity[]): LeadOpportunity[] {
  const byId = new Map<string, LeadOpportunity>();
  for (const lead of leads) {
    const existing = byId.get(lead.id);
    if (!existing || new Date(lead.capturedAt).getTime() > new Date(existing.capturedAt).getTime()) byId.set(lead.id, lead);
  }
  return Array.from(byId.values());
}

export function summarizeLeadMesh(leads: LeadOpportunity[]) {
  const active = rankLeadOpportunities(leads);
  return {
    activeCount: active.length,
    highValueCount: active.filter((lead) => lead.grade === 'A' || lead.grade === 'B').length,
    counterCount: active.filter((lead) => lead.counterRequired).length,
    retainerPipelineValue: active
      .filter((lead) => lead.category === 'retainer' || lead.category === 'teaming')
      .reduce((total, lead) => total + lead.expectedValue, 0)
  };
}

function getMinimumAcceptableValue(category: OpportunityCategory, estimatedHours: number): number {
  if (category === 'retainer' || category === 'teaming') return revenueRules.preferredRetainer;
  if (category === 'procurement') return 5000;
  if (category === 'hauling') return 150;
  return Math.max(revenueRules.minimumDispatch, estimatedHours * revenueRules.minimumHourly);
}

function getRiskFlags(input: LeadIntake, effectiveHourly: number, minimumAcceptableValue: number): string[] {
  const flags: string[] = [];
  if (!compliantSourceTypes.includes(input.sourceType)) flags.push('source not approved');
  if (input.expectedValue < minimumAcceptableValue) flags.push('below minimum value');
  if (effectiveHourly < revenueRules.minimumHourly && input.category !== 'procurement' && input.category !== 'retainer') flags.push('below hourly floor');
  if (input.category === 'procurement' && !input.deadline) flags.push('procurement deadline missing');
  if (input.requiredSkills.length === 0) flags.push('skills not mapped');
  if (input.location.toLowerCase().includes('remote') && input.category === 'field_dispatch') flags.push('location mismatch');
  return flags;
}

function gradeLead(input: LeadIntake, effectiveHourly: number, riskFlags: string[]): LeadGrade {
  if (riskFlags.includes('source not approved')) return 'Avoid';
  if (input.category === 'procurement' && input.expectedValue >= 5000 && riskFlags.length <= 1) return 'A';
  if ((input.category === 'retainer' || input.category === 'teaming') && input.expectedValue >= revenueRules.preferredRetainer) return 'A';
  if (effectiveHourly >= revenueRules.preferredHourly && riskFlags.length === 0) return 'A';
  if (effectiveHourly >= revenueRules.minimumHourly && riskFlags.length <= 1) return 'B';
  if (input.expectedValue >= revenueRules.minimumDispatch && riskFlags.length <= 2) return 'C';
  return 'Avoid';
}

function getConfidence(grade: LeadGrade, riskFlags: string[]): number {
  if (grade === 'A') return riskFlags.length === 0 ? 0.95 : 0.88;
  if (grade === 'B') return 0.8;
  if (grade === 'C') return 0.62;
  return 0.99;
}

function getNextAction(input: LeadIntake, grade: LeadGrade, counterRequired: boolean): string {
  if (grade === 'Avoid') return 'Discard unless pay, scope, source, and risk terms materially improve.';
  if (input.category === 'procurement') return 'Open the official portal, verify due date and documents, then prepare bid/no-bid decision package.';
  if (input.category === 'retainer' || input.category === 'teaming') return 'Prepare retainer coverage offer and request vendor onboarding or preferred-provider path.';
  if (counterRequired) return 'Counter before accepting. Do not commit below the minimum dispatch or hourly floor.';
  return 'Proceed to scope verification, calendar check, and approval gate.';
}

function getCounterMessage(input: LeadIntake, minimumAcceptableValue: number): string {
  if (input.category === 'retainer' || input.category === 'teaming') {
    return `Already Here LLC can support ${input.organization} as Phoenix metro on-call field coverage. Recommended structure: $1,500/month reserved support block, $95/hr after included hours, $130 minimum dispatch, materials and return trips billed separately.`;
  }
  if (input.category === 'procurement') {
    return `Already Here LLC is available for small-quote, on-call, and emergency field technology support. Please confirm vendor roster path, SBE/VBE recognition, required documents, due date, and whether informal quote submission is accepted.`;
  }
  return `I can support this work at $${minimumAcceptableValue} minimum for the scoped dispatch, or $${revenueRules.minimumHourly}/hr after the included time. Materials, parking, access delays, return trips, and expanded scope must be approved separately.`;
}

function getComplianceMode(sourceType: LeadSourceType): string {
  const modes: Record<LeadSourceType, string> = {
    authorized_email: 'Authorized inbound email or user-connected mailbox signal.',
    official_portal: 'Official portal or vendor account requiring manual approval before submission.',
    public_procurement: 'Public agency procurement notice; no automated bid submission.',
    partner_channel: 'Partner or prime-contractor relationship channel.',
    manual_public_listing: 'Manual public listing review; no bypass, impersonation, or prohibited automation.'
  };
  return modes[sourceType];
}

function stableLeadId(input: LeadIntake): string {
  const raw = `${input.source}|${input.organization}|${input.title}|${input.location}|${input.deadline ?? ''}`.toLowerCase().replace(/[^a-z0-9]+/g, '-');
  let hash = 0;
  for (let index = 0; index < raw.length; index += 1) hash = ((hash << 5) - hash + raw.charCodeAt(index)) | 0;
  return `lead-${Math.abs(hash).toString(36)}`;
}
