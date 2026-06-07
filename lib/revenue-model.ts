export const TARGET_OWNER_MONTHLY_INCOME = 25000;
export const TARGET_MONTHLY_REVENUE = TARGET_OWNER_MONTHLY_INCOME;
export const VERIFIED_SKILL_PREMIUM_MIN = 20;
export const VERIFIED_SKILL_PREMIUM_MAX = 30;

export type TechnicianContributionProfile = 'low_volume' | 'standard_market' | 'high_demand';

export interface RevenueModelInput {
  dailyActiveIncome: number;
  activeDaysPerMonth: number;
  retainerCount: number;
  averageRetainer: number;
  projectRevenue: number;
  dispatchMargin: number;
  automatedIncome: number;
}

export interface RevenueModelResult {
  activeIncome: number;
  retainerIncome: number;
  projectRevenue: number;
  dispatchMargin: number;
  automatedIncome: number;
  ownerCompanyIncome: number;
  total: number;
  gapToTarget: number;
}

export interface RevenueLine {
  label: string;
  monthlyTarget: number;
  mode: 'active' | 'recurring' | 'dispatch' | 'automated';
  nextAction: string;
}

export interface PassiveIncomeAsset {
  name: string;
  offer: string;
  firstMilestone: string;
  monthlyTarget: number;
}

export interface TechnicianContributionEstimate {
  profile: TechnicianContributionProfile;
  label: string;
  estimatedCompanyIncomeMin: number;
  estimatedCompanyIncomeMax: number;
  locationLogic: string;
  workVolumeLogic: string;
  marginLogic: string;
}

export interface TechnicianContributionScenario {
  technicianCount: number;
  profile: TechnicianContributionProfile;
}

export interface TechnicianContributionResult {
  technicianCount: number;
  profile: TechnicianContributionProfile;
  estimatedCompanyIncomeMin: number;
  estimatedCompanyIncomeMax: number;
  addedMonthlyIncomeMin: number;
  addedMonthlyIncomeMax: number;
  totalWithOwnerCompanyIncomeMin: number;
  totalWithOwnerCompanyIncomeMax: number;
}

export interface DispatchMarginInput {
  clientBillRateHourly: number;
  technicianBasePayoutHourly: number;
  verifiedSkillPremiumHourly: number;
  hoursPerJob: number;
  jobsPerMonth: number;
  nonLaborCostPerJob: number;
}

export interface DispatchMarginResult {
  effectiveTechPayoutHourly: number;
  grossMarginHourly: number;
  grossMarginPerJob: number;
  monthlyCompanyIncomeLift: number;
  marginIsViable: boolean;
}

export interface JobRatePolicy {
  label: string;
  pricingRule: string;
  techPayoutRule: string;
  locationRule: string;
}

export const defaultRevenueModel: RevenueModelInput = {
  dailyActiveIncome: 500,
  activeDaysPerMonth: 20,
  retainerCount: 6,
  averageRetainer: 997,
  projectRevenue: 5000,
  dispatchMargin: 3000,
  automatedIncome: 2000
};

export const monthlyRevenuePlan: RevenueLine[] = [
  {
    label: 'Morning small-job stack',
    monthlyTarget: 10000,
    mode: 'active',
    nextAction: 'Protect 5 AM to 1 PM for dense, fast-pay route stacking and avoid all-day blockers unless they create superior margin.'
  },
  {
    label: 'Priority support retainers',
    monthlyTarget: 5982,
    mode: 'recurring',
    nextAction: 'Convert completed jobs into six $997/month priority-response retainers with approval-gated outreach.'
  },
  {
    label: 'Project and rollout blocks',
    monthlyTarget: 5000,
    mode: 'recurring',
    nextAction: 'Package access control, POS, AV, printer, low-voltage, and smart-hands work into fixed-scope project blocks.'
  },
  {
    label: 'Owner-controlled dispatch margin',
    monthlyTarget: 3000,
    mode: 'dispatch',
    nextAction: 'Set the client/job rate first, then negotiate technician payout inside a safe margin band before dispatching work.'
  },
  {
    label: 'Automated asset income',
    monthlyTarget: 2000,
    mode: 'automated',
    nextAction: 'Sell templates, checklists, intake kits, and field-tech starter assets through automated funnels.'
  }
];

export const jobRatePolicies: JobRatePolicy[] = [
  {
    label: 'Already Here client/job rate comes first',
    pricingRule: 'Client pricing is set by job type, market, urgency, complexity, risk, travel, SLA, and whether the work is hourly, flat-rate, retainer, project, or dispatch coverage.',
    techPayoutRule: 'Technician payout is negotiated per tech and per job after the client rate is known. It is not a fixed universal band.',
    locationRule: 'Location changes the margin. Dense metros, urgent routes, and high-demand lanes can support higher payouts; thin or remote markets require tighter payout control.'
  },
  {
    label: 'Verified credential premium',
    pricingRule: 'Credentials, degrees, licenses, certifications, specialized tools, and additional verified skills can justify higher client pricing when the job requires them.',
    techPayoutRule: `A verified higher-skill technician may justify roughly ${VERIFIED_SKILL_PREMIUM_MIN} to ${VERIFIED_SKILL_PREMIUM_MAX} dollars per hour above baseline payout when margin supports it.`,
    locationRule: 'Premiums should be market-aware and tied to actual demand, not automatically paid on every ticket.'
  },
  {
    label: 'Company-income formula',
    pricingRule: 'Already Here LLC income lift equals client charge minus technician payout minus travel, admin, platform, QA, and non-labor costs, multiplied by profitable volume.',
    techPayoutRule: 'The payout must preserve company margin, quality control, client ownership, and future repeat-work potential.',
    locationRule: 'The same technician can produce different company lift in different cities because route density, demand, and client pricing change.'
  }
];

export const technicianContributionEstimates: TechnicianContributionEstimate[] = [
  {
    profile: 'low_volume',
    label: 'Low-volume / developing market estimate',
    estimatedCompanyIncomeMin: 500,
    estimatedCompanyIncomeMax: 1500,
    locationLogic: 'Secondary markets, rural routes, thin demand, low repeat volume, or markets still being proven.',
    workVolumeLogic: 'A few dispatches per month, mostly simple work or overflow coverage.',
    marginLogic: 'Company lift is lower when volume is low, even if the technician is good.'
  },
  {
    profile: 'standard_market',
    label: 'Standard metro / reliable coverage estimate',
    estimatedCompanyIncomeMin: 1500,
    estimatedCompanyIncomeMax: 4000,
    locationLogic: 'Usable planning range for normal metro coverage where there is enough recurring work to route consistently.',
    workVolumeLogic: 'Enough dispatches, retainers, and repeat-client work to create measurable monthly Already Here LLC net income.',
    marginLogic: 'Depends on client bill rate, negotiated tech payout, credential premium, closeout quality, travel friction, urgency premium, and volume.'
  },
  {
    profile: 'high_demand',
    label: 'High-demand / specialized market estimate',
    estimatedCompanyIncomeMin: 4000,
    estimatedCompanyIncomeMax: 8000,
    locationLogic: 'Dense metros, urgent coverage lanes, specialized skills, data center, healthcare, access control, low-voltage, or rollout work.',
    workVolumeLogic: 'Higher utilization, stronger repeat demand, and better client pricing can push upside above the normal planning range.',
    marginLogic: 'Only valid when Already Here LLC controls client pricing, QA, scope, negotiated payout, and dispatch reliability.'
  }
];

export const technicianContributionScenarios: TechnicianContributionScenario[] = [
  { technicianCount: 5, profile: 'low_volume' },
  { technicianCount: 5, profile: 'standard_market' },
  { technicianCount: 10, profile: 'standard_market' },
  { technicianCount: 5, profile: 'high_demand' },
  { technicianCount: 25, profile: 'standard_market' }
];

export const dispatchMarginExamples: DispatchMarginInput[] = [
  {
    clientBillRateHourly: 95,
    technicianBasePayoutHourly: 55,
    verifiedSkillPremiumHourly: 0,
    hoursPerJob: 2,
    jobsPerMonth: 20,
    nonLaborCostPerJob: 5
  },
  {
    clientBillRateHourly: 125,
    technicianBasePayoutHourly: 65,
    verifiedSkillPremiumHourly: 20,
    hoursPerJob: 2,
    jobsPerMonth: 20,
    nonLaborCostPerJob: 5
  },
  {
    clientBillRateHourly: 165,
    technicianBasePayoutHourly: 75,
    verifiedSkillPremiumHourly: 30,
    hoursPerJob: 3,
    jobsPerMonth: 16,
    nonLaborCostPerJob: 10
  }
];

export const passiveIncomeAssets: PassiveIncomeAsset[] = [
  {
    name: '1099 Field Tech Starter Kit',
    offer: 'Templates, onboarding checklist, closeout checklist, dispatch readiness guide, and pricing rules.',
    firstMilestone: 'Publish product page and attach to every technician/referral conversation.',
    monthlyTarget: 750
  },
  {
    name: 'Small Business Emergency IT Checklist',
    offer: 'Downloadable checklist plus request form for Phoenix-area emergency support.',
    firstMilestone: 'Launch as lead magnet feeding the retainer follow-up sequence.',
    monthlyTarget: 500
  },
  {
    name: 'Dispatch OS Lite',
    offer: 'Mobile-first local dashboard for tiny contractors that need intake, closeout, and opportunity decisions.',
    firstMilestone: 'Ship ZIP/download version and collect buyer feedback before adding hosted accounts.',
    monthlyTarget: 750
  }
];

export function calculateMonthlyRevenue(input: RevenueModelInput = defaultRevenueModel): RevenueModelResult {
  const activeIncome = input.dailyActiveIncome * input.activeDaysPerMonth;
  const retainerIncome = input.retainerCount * input.averageRetainer;
  const ownerCompanyIncome = activeIncome + retainerIncome + input.projectRevenue + input.dispatchMargin + input.automatedIncome;

  return {
    activeIncome,
    retainerIncome,
    projectRevenue: input.projectRevenue,
    dispatchMargin: input.dispatchMargin,
    automatedIncome: input.automatedIncome,
    ownerCompanyIncome,
    total: ownerCompanyIncome,
    gapToTarget: TARGET_OWNER_MONTHLY_INCOME - ownerCompanyIncome
  };
}

export function calculateTechnicianContribution(
  scenario: TechnicianContributionScenario,
  ownerCompanyIncome = calculateMonthlyRevenue(defaultRevenueModel).ownerCompanyIncome
): TechnicianContributionResult {
  const estimate = technicianContributionEstimates.find((item) => item.profile === scenario.profile) ?? technicianContributionEstimates[1];
  const addedMonthlyIncomeMin = scenario.technicianCount * estimate.estimatedCompanyIncomeMin;
  const addedMonthlyIncomeMax = scenario.technicianCount * estimate.estimatedCompanyIncomeMax;

  return {
    technicianCount: scenario.technicianCount,
    profile: scenario.profile,
    estimatedCompanyIncomeMin: estimate.estimatedCompanyIncomeMin,
    estimatedCompanyIncomeMax: estimate.estimatedCompanyIncomeMax,
    addedMonthlyIncomeMin,
    addedMonthlyIncomeMax,
    totalWithOwnerCompanyIncomeMin: ownerCompanyIncome + addedMonthlyIncomeMin,
    totalWithOwnerCompanyIncomeMax: ownerCompanyIncome + addedMonthlyIncomeMax
  };
}

export function calculateDispatchMargin(input: DispatchMarginInput): DispatchMarginResult {
  const safePremium = Math.max(0, input.verifiedSkillPremiumHourly);
  const effectiveTechPayoutHourly = input.technicianBasePayoutHourly + safePremium;
  const grossMarginHourly = input.clientBillRateHourly - effectiveTechPayoutHourly;
  const grossMarginPerJob = (grossMarginHourly * input.hoursPerJob) - input.nonLaborCostPerJob;
  const monthlyCompanyIncomeLift = grossMarginPerJob * input.jobsPerMonth;

  return {
    effectiveTechPayoutHourly,
    grossMarginHourly,
    grossMarginPerJob,
    monthlyCompanyIncomeLift,
    marginIsViable: grossMarginHourly > 0 && grossMarginPerJob > 0
  };
}

export function getRevenueModeLabel(mode: RevenueLine['mode']): string {
  const labels: Record<RevenueLine['mode'], string> = {
    active: 'Active cash engine',
    recurring: 'Recurring revenue',
    dispatch: 'Owner-controlled network margin',
    automated: 'Automated income'
  };
  return labels[mode];
}

export function getTechnicianContributionLabel(profile: TechnicianContributionProfile): string {
  const estimate = technicianContributionEstimates.find((item) => item.profile === profile);
  return estimate?.label ?? 'Technician contribution estimate';
}

export function formatCurrency(value: number): string {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    maximumFractionDigits: 0
  }).format(value);
}
