'use client';

import { useEffect, useState } from 'react';
import {
  SuperIntelligenceOrchestrator,
  getDefaultDailyCommandFeed,
  getDefaultHistoricalFrictionLedger,
  type RuntimeResult
} from '../../lib/daily-command-core';

const generatedAt = '2026-06-21T08:00:00.000-07:00';

export default function DailyCommandPanel() {
  const [report, setReport] = useState<RuntimeResult | null>(null);

  useEffect(() => {
    let active = true;
    const engine = new SuperIntelligenceOrchestrator();
    engine.processLiveMatrix(getDefaultDailyCommandFeed(), getDefaultHistoricalFrictionLedger(), { generatedAt, dailyTarget: 500 })
      .then((result) => { if (active) setReport(result); });
    return () => { active = false; };
  }, []);

  if (!report) {
    return <section className="panel asiPanel"><h2>Daily Command Engine Matrix</h2><p className="opsCopy">Loading deterministic local command matrix.</p></section>;
  }

  return (
    <section className="panel asiPanel">
      <div className="asiHeader">
        <div>
          <p className="eyebrow">Daily Command Engine Matrix</p>
          <h2>Local-First Revenue Command Queue</h2>
          <p className="opsCopy">Runs from local/manual feed data, keeps all original scoring features, and does not require third-party credentials to produce a ranked operating plan.</p>
        </div>
        <div className="decisionBox">
          <strong>{report.systemHealth}</strong>
          <span>${report.metrics.confirmed.toFixed(2)} confirmed / ${report.metrics.revenueGap.toFixed(2)} gap</span>
        </div>
      </div>

      <section className="grid stats asiStats">
        <Metric label="Target" value={`$${report.metrics.dailyTarget.toFixed(0)}`} />
        <Metric label="Confirmed" value={`$${report.metrics.confirmed.toFixed(0)}`} />
        <Metric label="Blocked" value={`$${report.metrics.blockedValue.toFixed(0)}`} />
        <Metric label="Avg EHV" value={`$${report.metrics.averageEffectiveHourlyValue.toFixed(0)}/hr`} />
        <Metric label="Approvals" value={String(report.metrics.approvalRequiredCount)} />
      </section>

      <div className="cards">
        {report.rankedQueue.map((item) => (
          <article className="match" key={item.id}>
            <div>
              <strong>{item.id} · {item.category}</strong>
              <span>{item.source} · {item.location?.address ?? 'No location'} · route {item.routeFrictionHours ?? 0} hrs</span>
            </div>
            <b>Grade {item.grade}</b>
            <p>${item.potentialValue.toFixed(2)} gross · ${item.effectiveHourlyValue?.toFixed(2) ?? '0.00'}/hr EHV · {item.exactNextStep}</p>
            <small>Risk: {item.riskFlags.length ? item.riskFlags.join(' · ') : 'NONE'}</small>
          </article>
        ))}
      </div>

      <details className="detail">
        <summary>Generated master Markdown export</summary>
        <pre>{report.masterDocumentOutput}</pre>
      </details>
    </section>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return <div className="metric"><strong>{value}</strong><span>{label}</span></div>;
}
