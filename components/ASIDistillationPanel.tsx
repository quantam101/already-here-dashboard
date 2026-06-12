'use client';

import { useMemo } from 'react';
import { ASI_REVENUE_RULES, sampleASILeads, scoreASILeads, summarizeASIScoredLeads, type ASILeadInput } from '../lib/asi-engine';
import type { FieldNetworkState } from '../lib/types';

function workOrdersToLeads(state: FieldNetworkState): ASILeadInput[] {
  return state.workOrders.slice(0, 8).map((workOrder) => ({
    id: workOrder.id,
    source: 'field_network_os',
    platformRef: workOrder.id,
    company: state.clients.find((client) => client.id === workOrder.clientId)?.company,
    title: workOrder.title,
    location: workOrder.location,
    serviceType: workOrder.requiredSkills.includes('project_management')
      ? 'project_management'
      : workOrder.requiredSkills.includes('data_center') || workOrder.requiredSkills.includes('smart_hands')
        ? 'server_smart_hands'
        : workOrder.requiredSkills.includes('access_control')
          ? 'access_control'
          : 'network_support',
    scheduleWindow: workOrder.urgency,
    expectedRevenue: workOrder.budget,
    estimatedTravelMinutes: workOrder.metro.toLowerCase().includes('phoenix') ? 25 : 45,
    estimatedOnsiteMinutes: workOrder.estimatedHours * 60,
    description: [workOrder.requiredSkills.join(' '), workOrder.complexity, workOrder.requiresLead ? 'field lead required' : ''].filter(Boolean).join(' '),
    retainerPotential: workOrder.requiredSkills.includes('retainer') || workOrder.requiredSkills.includes('project_management'),
    repeatPotential: workOrder.urgency !== 'scheduled',
    softwareOpportunity: 'field_intake_dispatch_triage',
    networkOpportunity: 'already_here_field_network_os'
  }));
}

function storedLeadsToInputs(state: FieldNetworkState): ASILeadInput[] {
  return (state.leadOpportunities ?? []).slice(0, 8).map((lead) => ({
    id: lead.id,
    source: lead.source,
    platformRef: lead.id,
    company: lead.organization,
    title: lead.title,
    location: lead.location,
    serviceType: lead.category === 'project_management' ? 'project_management' : lead.category === 'retainer' ? 'retainer_coverage' : 'network_support',
    scheduleWindow: lead.deadline,
    expectedRevenue: lead.expectedValue,
    estimatedTravelMinutes: lead.metro.toLowerCase().includes('phoenix') ? 25 : 45,
    estimatedOnsiteMinutes: lead.estimatedHours * 60,
    description: lead.notes,
    retainerPotential: lead.category === 'retainer' || lead.category === 'procurement' || lead.category === 'project_management',
    repeatPotential: lead.sourceType === 'partner_channel' || lead.sourceType === 'public_procurement',
    softwareOpportunity: 'lead_intelligence_database',
    networkOpportunity: lead.complianceMode
  }));
}

export default function ASIDistillationPanel({ state }: { state: FieldNetworkState }) {
  const scored = useMemo(() => {
    const operationalInputs = [...workOrdersToLeads(state), ...storedLeadsToInputs(state)];
    const inputs = operationalInputs.length > 0 ? operationalInputs : sampleASILeads;
    return scoreASILeads(inputs);
  }, [state]);

  const summary = summarizeASIScoredLeads(scored);
  const bestLead = scored[0];

  return (
    <section className="panel asiPanel">
      <div className="asiHeader">
        <div>
          <p className="eyebrow">ASI Revenue Intelligence Core</p>
          <h2>Distillation Engine Command Layer</h2>
          <p className="opsCopy">
            Local-first scoring for $500 minimum field days, retainer conversion, project/SOW routing, company intelligence, and approval-gated action drafts.
          </p>
        </div>
        <div className="decisionBox">
          <span>Daily field floor</span>
          <strong>${ASI_REVENUE_RULES.minimumDailyFieldRevenue}</strong>
          <span>{ASI_REVENUE_RULES.preferredCompletionWindow.replace('_', ' ')}</span>
        </div>
      </div>

      <div className="grid stats asiStats">
        <div className="metric"><strong>${summary.revenueToday.toLocaleString()}</strong><span>qualified field revenue</span></div>
        <div className="metric"><strong>{summary.retainerTargets}</strong><span>retainer targets</span></div>
        <div className="metric"><strong>{summary.approvalQueue}</strong><span>approval-gated drafts</span></div>
        <div className="metric"><strong>{summary.databaseValue}</strong><span>database value score</span></div>
        <div className="metric"><strong>{scored.length}</strong><span>normalized signals</span></div>
      </div>

      {bestLead && (
        <div className="decisionBox">
          <span>Best current action</span>
          <strong>{bestLead.score.grade} — {bestLead.input.title}</strong>
          <span>{bestLead.score.nextAction}</span>
        </div>
      )}

      <div className="cards">
        {scored.slice(0, 5).map((lead) => (
          <article className="leadCard asiLead" key={lead.input.id ?? `${lead.input.source}-${lead.input.title}`}>
            <div>
              <strong>{lead.input.title}</strong>
              <span>{lead.input.company ?? lead.input.source} · {lead.input.location}</span>
            </div>
            <b>{lead.score.grade}</b>
            <p>
              ${lead.score.expectedRevenue.toLocaleString()} expected · ${lead.score.targetRate.toLocaleString()} target · {lead.score.effectiveHourly ? `$${Math.round(lead.score.effectiveHourly)}/hr effective` : 'rate not visible'}
            </p>
            <small>
              Stack {lead.score.stackabilityScore}/5 · Repeat {lead.score.repeatPotential}/5 · Retainer {lead.score.retainerPotential}/5 · Data {lead.score.dataValueScore}/10
            </small>
            <small>{lead.score.riskFlags.length > 0 ? `Risk: ${lead.score.riskFlags.join(' · ')}` : 'No major risk flags recorded'}</small>
          </article>
        ))}
      </div>
    </section>
  );
}
