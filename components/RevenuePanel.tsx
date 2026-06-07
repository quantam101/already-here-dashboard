'use client';

import { rankLeadOpportunities, summarizeLeadMesh } from '../lib/lead-mesh';
import type { LeadDecisionStatus, LeadOpportunity } from '../lib/types';

interface RevenuePanelProps {
  opportunities: LeadOpportunity[];
  onDecision: (opportunityId: string, decisionStatus: LeadDecisionStatus) => void;
}

export default function RevenuePanel({ opportunities, onDecision }: RevenuePanelProps) {
  const ranked = rankLeadOpportunities(opportunities);
  const summary = summarizeLeadMesh(opportunities);

  return (
    <>
      <section className="panel opsPanel">
        <div>
          <p className="eyebrow">Revenue operations</p>
          <h2>Compliant Opportunity Mesh</h2>
          <p className="opsCopy">Break/fix, retainer, teaming, procurement, and dispatch opportunities are ranked by value, source authorization, scope clarity, and actionability.</p>
        </div>
        <div className="opsMetrics">
          <span>{summary.highValueCount} A/B opportunities</span>
          <span>{summary.counterCount} counter gates</span>
          <span>${summary.retainerPipelineValue.toLocaleString()} retainer pipeline</span>
        </div>
      </section>

      <section className="panel">
        <h2>Opportunity Queue</h2>
        <div className="cards">
          {ranked.slice(0, 6).map((opportunity) => (
            <article className="leadCard" key={opportunity.id}>
              <div>
                <strong>{opportunity.title}</strong>
                <span>{opportunity.organization} · {opportunity.location}</span>
              </div>
              <b>{opportunity.grade}</b>
              <p>{opportunity.nextAction}</p>
              <small>${opportunity.expectedValue.toLocaleString()} value · ${opportunity.effectiveHourly}/hr effective · {opportunity.complianceMode}</small>
              {opportunity.riskFlags.length > 0 && <small>Risk: {opportunity.riskFlags.join(' · ')}</small>}
              <div className="leadActions">
                <button onClick={() => onDecision(opportunity.id, 'proceed')}>Proceed</button>
                <button onClick={() => onDecision(opportunity.id, 'counter')}>Counter</button>
                <button onClick={() => onDecision(opportunity.id, 'discard')}>Discard</button>
              </div>
            </article>
          ))}
        </div>
      </section>
    </>
  );
}
