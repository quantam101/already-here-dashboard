export const TARGET_MONTHLY_REVENUE = 25000;

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
    label: 'Nationwide dispatch margin',
    monthlyTarget: 3000,
    mode: 'dispatch',
    nextAction: 'Use the technician network to accept work outside Stephen’s route and capture margin through QA-controlled dispatch.'
  },
  {
    label: 'Automated asset income',
    monthlyTarget: 2000,
    mode: 'automated',
    nextAction: 'Sell templates, checklists, intake kits, and field-tech starter assets through automated funnels.'
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
  const total = activeIncome + retainerIncome + input.projectRevenue + input.dispatchMargin + input.automatedIncome;

  return {
    activeIncome,
    retainerIncome,
    projectRevenue: input.projectRevenue,
    dispatchMargin: input.dispatchMargin,
    automatedIncome: input.automatedIncome,
    total,
    gapToTarget: TARGET_MONTHLY_REVENUE - total
  };
}

export function getRevenueModeLabel(mode: RevenueLine['mode']): string {
  const labels: Record<RevenueLine['mode'], string> = {
    active: 'Active cash engine',
    recurring: 'Recurring revenue',
    dispatch: 'Network margin',
    automated: 'Automated income'
  };
  return labels[mode];
}

export function formatCurrency(value: number): string {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    maximumFractionDigits: 0
  }).format(value);
}
