'use client';

import { useEffect, useState } from 'react';
import { rankLeadOpportunities, summarizeLeadMesh } from '../lib/lead-mesh';
import { initialLeadOpportunities } from '../lib/sample-data';
import type { LeadDecisionStatus, LeadOpportunity } from '../lib/types';

const STORE_KEY = 'already_here_revenue_opportunities';

export default function RevenuePanel() {
  const [opportunities, setOpportunities] = useState<LeadOpportunity[]>(initialLeadOpportunities);

  useEffect(() => {
    const saved = window.localStorage.getItem(STORE_KEY);
    if (!saved) return;
    try {
      const parsed = JSON.parse(saved) as LeadOpportunity[];
      if (Array.isArray(parsed)) setOpportunities(parsed);
    } catch {
      setOpportunities(initialLeadOpportunities);
    }
  }, []);

  useEffect(() => {
    window.localStorage.setItem(STORE_KEY, JSON.stringify(opportunities));
  }, [opportunities]);

  const ranked = rankLeadOpportunities(opportunities);
  const summary = summarizeLeadMesh(opportunities);

  function decide(opportunityId: string, decisionStatus: LeadDecisionStatus) {
    setOpportunities((current) => current.map((item) => item.id === opportunityId ? { ...item, decisionStatus } : item));
  }

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
                <button onClick={() => decide(opportunity.id, 'proceed')}>Proceed</button>
                <button onClick={() => decide(opportunity.id, 'counter')}>Counter</button>
                <button onClick={() => decide(opportunity.id, 'discard')}>Discard</button>
              </div>
            </article>
          ))}
        </div>
      </section>
    </>
  );
}
