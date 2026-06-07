import { NextResponse } from 'next/server';

export const runtime = 'nodejs';
export const dynamic = 'force-dynamic';

interface TaylorLearningRecord {
  callOutcome: string;
  customerIntent: string;
  serviceCategory?: string;
  schedulingStatus?: string;
  paymentStatus?: string;
  depositStatus?: string;
  questionsTaylorCouldNotAnswer?: string[];
  recommendedFollowUp?: string;
  recommendedKnowledgeBaseUpdate?: string;
  recommendedScriptUpdate?: string;
  riskFlags?: string[];
  operatorReviewRequired?: boolean;
}

const highRiskTerms = [
  'pricing',
  'refund',
  'contract',
  'legal',
  'payment terms',
  'technician assignment',
  'public claim',
  'account status'
];

export async function POST(request: Request) {
  try {
    const body = await request.json() as Partial<TaylorLearningRecord>;
    const record = sanitizeLearningRecord(body);
    const operatorReviewRequired = Boolean(record.operatorReviewRequired) || requiresOperatorReview(record);

    return NextResponse.json({
      ok: true,
      stored: false,
      queuedForReview: operatorReviewRequired,
      record: {
        ...record,
        operatorReviewRequired
      },
      taylorOperationalNote: operatorReviewRequired
        ? 'This call produced a high-impact learning item. Owner or operator review is required before Taylor changes behavior.'
        : 'This call produced a low-risk operational learning item. It can be queued for knowledge-base improvement.'
    });
  } catch (error) {
    const message = error instanceof Error ? error.message : 'Unable to process learning record';
    return NextResponse.json({ ok: false, error: message }, { status: 400 });
  }
}

function sanitizeLearningRecord(input: Partial<TaylorLearningRecord>): TaylorLearningRecord {
  return {
    callOutcome: sanitizeText(input.callOutcome ?? 'unknown'),
    customerIntent: sanitizeText(input.customerIntent ?? 'unknown'),
    serviceCategory: sanitizeOptional(input.serviceCategory),
    schedulingStatus: sanitizeOptional(input.schedulingStatus),
    paymentStatus: sanitizeOptional(input.paymentStatus),
    depositStatus: sanitizeOptional(input.depositStatus),
    questionsTaylorCouldNotAnswer: sanitizeList(input.questionsTaylorCouldNotAnswer),
    recommendedFollowUp: sanitizeOptional(input.recommendedFollowUp),
    recommendedKnowledgeBaseUpdate: sanitizeOptional(input.recommendedKnowledgeBaseUpdate),
    recommendedScriptUpdate: sanitizeOptional(input.recommendedScriptUpdate),
    riskFlags: sanitizeList(input.riskFlags),
    operatorReviewRequired: Boolean(input.operatorReviewRequired)
  };
}

function requiresOperatorReview(record: TaylorLearningRecord): boolean {
  const reviewText = [
    record.recommendedKnowledgeBaseUpdate,
    record.recommendedScriptUpdate,
    record.recommendedFollowUp,
    ...(record.riskFlags ?? [])
  ].filter(Boolean).join(' ').toLowerCase();

  return highRiskTerms.some((term) => reviewText.includes(term));
}

function sanitizeOptional(value: unknown): string | undefined {
  if (typeof value !== 'string') return undefined;
  const clean = sanitizeText(value);
  return clean.length > 0 ? clean : undefined;
}

function sanitizeList(values: unknown): string[] {
  if (!Array.isArray(values)) return [];
  return values.filter((value): value is string => typeof value === 'string').map(sanitizeText).filter(Boolean).slice(0, 20);
}

function sanitizeText(value: string): string {
  return value
    .replace(/\b\d{12,19}\b/g, '[redacted-number]')
    .replace(/\b\d{3,4}\b/g, '[redacted-code]')
    .replace(/[\r\n\t]+/g, ' ')
    .replace(/\s+/g, ' ')
    .trim()
    .slice(0, 1000);
}
