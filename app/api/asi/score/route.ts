import { NextResponse } from 'next/server';
import { buildASIActionDraft, scoreASILead, type ASILeadInput } from '../../../../lib/asi-engine';

export const dynamic = 'force-dynamic';

export async function POST(request: Request) {
  const payload = (await request.json()) as Partial<ASILeadInput>;
  if (!payload.source || !payload.title || !payload.location || !payload.serviceType) {
    return NextResponse.json(
      { error: 'source, title, location, and serviceType are required.' },
      { status: 400 }
    );
  }

  const input = payload as ASILeadInput;
  const score = scoreASILead(input);
  const action = buildASIActionDraft(input, score);
  return NextResponse.json({ score, action, approvalRequired: true });
}
