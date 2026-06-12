export type ASIGrade = 'A' | 'B' | 'C' | 'AVOID' | 'B_STRATEGIC';

export type ASIServiceType =
  | 'server_smart_hands'
  | 'data_center'
  | 'network_support'
  | 'ap_wireless'
  | 'pos_support'
  | 'printer_computer'
  | 'access_control'
  | 'low_voltage_cabling'
  | 'healthcare_equipment'
  | 'asset_inventory'
  | 'decommissioning'
  | 'hauling_delivery'
  | 'project_management'
  | 'field_project_lead'
  | 'municipal_procurement'
  | 'retainer_coverage'
  | 'automation_software'
  | string;

export interface ASILeadInput {
  id?: string;
  source: string;
  platformRef?: string;
  company?: string;
  contactName?: string;
  contactEmail?: string;
  title: string;
  location: string;
  serviceType: ASIServiceType;
  scheduleWindow?: string;
  listedRate?: number;
  maxHours?: number;
  fixedPay?: number;
  expectedRevenue?: number;
  estimatedTravelMinutes?: number;
  estimatedOnsiteMinutes?: number;
  description?: string;
  retainerPotential?: boolean;
  repeatPotential?: boolean;
  softwareOpportunity?: string;
  networkOpportunity?: string;
}

export interface ASILeadScore {
  grade: ASIGrade;
  expectedRevenue: number;
  targetRate: number;
  effectiveHourly: number | null;
  stackabilityScore: number;
  repeatPotential: number;
  retainerPotential: number;
  dataValueScore: number;
  riskFlags: string[];
  nextAction: string;
}

export interface ASIActionDraft {
  actionType: 'COUNTER_OR_REPLY' | 'RETAINER_CONVERSION' | 'PASS_UNLESS_REPRICED';
  approvalRequired: true;
  body: string;
}

export interface ASIScoredLead {
  input: ASILeadInput;
  score: ASILeadScore;
  action: ASIActionDraft;
}

export const ASI_REVENUE_RULES = {
  minimumDailyFieldRevenue: 500,
  minimumDispatchValue: 130,
  minimumEffectiveHourly: 65,
  preferredSmartHandsFlat: 200,
  retainerFloorMonthly: 1500,
  preferredCompletionWindow: 'by_noon'
} as const;

const premiumServiceTypes = new Set([
  'server_smart_hands',
  'data_center',
  'network_support',
  'ap_wireless',
  'pos_support',
  'access_control',
  'healthcare_equipment',
  'project_management',
  'field_project_lead',
  'retainer_coverage'
]);

const lowMarginTerms = ['helper', 'labor only', 'unknown pay', 'commission only', 'intern', 'w2', 'full-time', 'employee'];
const longTravelTerms = ['flagstaff', 'show low', 'tucson', 'yuma', 'prescott'];
const recurrenceTerms = ['retainer', 'recurring', 'vendor', 'route', 'multi-site', 'rollout', 'municipal', 'procurement'];
const retainerTerms = ['overflow', 'coverage', 'vendor list', 'municipal', 'procurement', 'msp', 'retainer', 'recurring'];
const premiumTerms = ['server', 'data center', 'hpe', 'storage', 'access control', 'pos', 'wireless', 'ap swap', 'network outage', 'project manager', 'site lead', 'field lead', 'retainer'];

function containsAny(value: string, terms: readonly string[]): boolean {
  const haystack = value.toLowerCase();
  return terms.some((term) => haystack.includes(term));
}

function clamp(value: number, min: number, max: number): number {
  return Math.max(min, Math.min(max, value));
}

function money(value: number | undefined): number {
  if (typeof value !== 'number' || Number.isNaN(value)) return 0;
  return value;
}

export function scoreASILead(input: ASILeadInput): ASILeadScore {
  const serviceType = input.serviceType.toLowerCase();
  const combined = [input.title, input.description, input.location, serviceType].filter(Boolean).join(' ');
  const listedRate = money(input.listedRate);
  const maxHours = money(input.maxHours) || 2;
  const fixedPay = money(input.fixedPay);
  const expectedRevenue = fixedPay || (listedRate ? listedRate * maxHours : money(input.expectedRevenue));
  const estimatedTravelMinutes = money(input.estimatedTravelMinutes);
  const estimatedOnsiteMinutes = money(input.estimatedOnsiteMinutes) || maxHours * 60 || 120;
  const totalHours = Math.max((estimatedTravelMinutes + estimatedOnsiteMinutes) / 60, 0.25);
  const effectiveHourly = expectedRevenue > 0 ? expectedRevenue / totalHours : null;

  const riskFlags: string[] = [];
  if (expectedRevenue < ASI_REVENUE_RULES.minimumDispatchValue) riskFlags.push('below_minimum_dispatch_value');
  if (effectiveHourly !== null && effectiveHourly < ASI_REVENUE_RULES.minimumEffectiveHourly) riskFlags.push('below_effective_hourly_floor');
  if (containsAny(combined, lowMarginTerms)) riskFlags.push('employment_or_low_margin_language');
  if (containsAny(input.location, longTravelTerms) || estimatedTravelMinutes > 90) riskFlags.push('travel_burden');
  if (combined.toLowerCase().includes('return trip') || combined.toLowerCase().includes('parts not onsite')) riskFlags.push('unpaid_return_trip_risk');
  if (!fixedPay && !listedRate && !input.expectedRevenue) riskFlags.push('pay_not_visible');

  const premium = premiumServiceTypes.has(serviceType) || containsAny(combined, premiumTerms);

  let repeatPotential = input.repeatPotential ? 2 : 0;
  if (containsAny(combined, recurrenceTerms)) repeatPotential += 3;
  if (premium) repeatPotential += 1;
  repeatPotential = clamp(repeatPotential, 0, 5);

  let retainerPotential = input.retainerPotential ? 3 : 0;
  if (containsAny(combined, retainerTerms)) retainerPotential += 2;
  if (serviceType === 'project_management' || serviceType === 'field_project_lead' || serviceType === 'retainer_coverage') retainerPotential += 2;
  retainerPotential = clamp(retainerPotential, 0, 5);

  let stackabilityScore = 5;
  if (estimatedTravelMinutes > 45) stackabilityScore -= 2;
  if (estimatedOnsiteMinutes > 180) stackabilityScore -= 1;
  if (expectedRevenue >= 250) stackabilityScore += 1;
  if (expectedRevenue >= ASI_REVENUE_RULES.minimumDailyFieldRevenue) stackabilityScore += 2;
  stackabilityScore = clamp(stackabilityScore, 0, 5);

  let dataValueScore = 1 + repeatPotential + retainerPotential;
  if (input.company || input.contactEmail) dataValueScore += 1;
  if (premium) dataValueScore += 1;
  dataValueScore = clamp(dataValueScore, 0, 10);

  let grade: ASIGrade;
  if (expectedRevenue >= ASI_REVENUE_RULES.minimumDailyFieldRevenue) {
    grade = 'A';
  } else if (expectedRevenue >= 250 && stackabilityScore >= 3) {
    grade = 'B';
  } else if (expectedRevenue >= 150 && stackabilityScore >= 4) {
    grade = 'C';
  } else if (retainerPotential >= 4 && dataValueScore >= 7) {
    grade = 'B_STRATEGIC';
  } else {
    grade = 'AVOID';
  }

  if (riskFlags.includes('travel_burden') && expectedRevenue < ASI_REVENUE_RULES.minimumDailyFieldRevenue) grade = 'AVOID';
  if (riskFlags.includes('employment_or_low_margin_language') && retainerPotential < 4) grade = 'AVOID';

  const nextAction = (() => {
    if (grade === 'A') return 'Pursue immediately as the $500 field anchor or premium project/SOW.';
    if (grade === 'B') return 'Pursue only if it stacks with another nearby job or converts into project/retainer work.';
    if (grade === 'B_STRATEGIC') return 'Treat as a database, procurement, retainer, or software-network conversion path.';
    if (grade === 'C') return 'Use only as tightly clustered filler after the premium anchor is secured.';
    return 'Pass unless the buyer approves a premium or travel-adjusted counter.';
  })();

  const minimumCounter = Math.max(
    ASI_REVENUE_RULES.minimumDispatchValue,
    premium ? ASI_REVENUE_RULES.preferredSmartHandsFlat : ASI_REVENUE_RULES.minimumDispatchValue
  );
  let targetRate = Math.max(expectedRevenue, minimumCounter);
  if (riskFlags.includes('travel_burden')) targetRate = Math.max(targetRate, 450);

  return {
    grade,
    expectedRevenue,
    targetRate,
    effectiveHourly,
    stackabilityScore,
    repeatPotential,
    retainerPotential,
    dataValueScore,
    riskFlags,
    nextAction
  };
}

export function buildASIActionDraft(input: ASILeadInput, score: ASILeadScore): ASIActionDraft {
  const company = input.company || 'Team';
  const location = input.location || 'the listed site';
  const title = input.title || 'this assignment';
  const actionType: ASIActionDraft['actionType'] = score.grade === 'AVOID' ? 'PASS_UNLESS_REPRICED' : score.retainerPotential >= 4 ? 'RETAINER_CONVERSION' : 'COUNTER_OR_REPLY';

  return {
    actionType,
    approvalRequired: true,
    body: [
      `Hello ${company},`,
      '',
      `Stephen Franklin with Already Here LLC. I can support ${title} at ${location} at a flat rate of $${score.targetRate.toLocaleString('en-US', { maximumFractionDigits: 0 })}, including standard field tools, onsite work, closeout notes, required photos, and coordination with remote support as needed.`,
      '',
      'Additional approved onsite work beyond the agreed scope is billed at $65/hr. Please confirm scope, site access, onsite contact, parts/equipment availability, and that no unpaid return trip is required.',
      '',
      'If this is recurring Phoenix metro coverage, Already Here LLC can also support a monthly retainer or priority-response arrangement.',
      '',
      'Stephen Franklin',
      'Already Here LLC',
      '602-882-2920',
      'dispatch@alreadyherellc@gmail.com'
    ].join('\n')
  };
}

export function scoreASILeads(inputs: ASILeadInput[]): ASIScoredLead[] {
  return inputs
    .map((input) => {
      const score = scoreASILead(input);
      return { input, score, action: buildASIActionDraft(input, score) };
    })
    .sort((a, b) => {
      const gradeWeight = { A: 5, B: 4, B_STRATEGIC: 3, C: 2, AVOID: 1 } satisfies Record<ASIGrade, number>;
      return gradeWeight[b.score.grade] - gradeWeight[a.score.grade] || b.score.expectedRevenue - a.score.expectedRevenue || b.score.dataValueScore - a.score.dataValueScore;
    });
}

export function summarizeASIScoredLeads(leads: ASIScoredLead[]) {
  const revenueToday = leads.filter((lead) => lead.score.grade === 'A' || lead.score.grade === 'B').reduce((sum, lead) => sum + lead.score.expectedRevenue, 0);
  const approvalQueue = leads.filter((lead) => lead.action.approvalRequired).length;
  const retainerTargets = leads.filter((lead) => lead.score.retainerPotential >= 4).length;
  const databaseValue = leads.reduce((sum, lead) => sum + lead.score.dataValueScore, 0);
  return { revenueToday, approvalQueue, retainerTargets, databaseValue };
}

export const sampleASILeads: ASILeadInput[] = [
  {
    id: 'sample-phoenix-smart-hands-500',
    source: 'direct_vendor',
    company: 'Phoenix MSP Overflow Buyer',
    title: 'Same-Day Network Outage Smart Hands',
    location: 'Phoenix, AZ',
    serviceType: 'server_smart_hands',
    scheduleWindow: 'same_day_morning',
    fixedPay: 500,
    estimatedTravelMinutes: 25,
    estimatedOnsiteMinutes: 150,
    description: 'Emergency smart hands, switch/AP validation, photos, closeout, and bridge support.',
    retainerPotential: true,
    repeatPotential: true,
    softwareOpportunity: 'missed_call_intake_and_dispatch_triage',
    networkOpportunity: 'msp_overflow_retainer'
  },
  {
    id: 'sample-flagstaff-lte-test',
    source: 'workmarket',
    platformRef: 'concert-piab-flagstaff-demo',
    company: 'Concert Technologies',
    title: 'PIAB Mount and LTE Test',
    location: 'Flagstaff, AZ',
    serviceType: 'network_support',
    scheduleWindow: 'next_day_10am',
    listedRate: 65,
    maxHours: 2,
    estimatedTravelMinutes: 240,
    estimatedOnsiteMinutes: 90,
    description: 'PIAB mount and LTE test. Max 2 hours.',
    repeatPotential: true,
    networkOpportunity: 'dispatch_buyer_database_record'
  },
  {
    id: 'sample-chandler-procurement',
    source: 'municipal_procurement',
    company: 'City Procurement Path',
    title: 'Vendor Registration for IT Field Services and Project Management',
    location: 'Chandler, AZ',
    serviceType: 'municipal_procurement',
    scheduleWindow: 'registration_path',
    expectedRevenue: 0,
    estimatedTravelMinutes: 0,
    estimatedOnsiteMinutes: 30,
    description: 'Procurement vendor list for technology, field support, access control, network support, and project management.',
    retainerPotential: true,
    repeatPotential: true,
    softwareOpportunity: 'vendor_intake_and_small_quote_tracking',
    networkOpportunity: 'municipal_vendor_database'
  }
];
