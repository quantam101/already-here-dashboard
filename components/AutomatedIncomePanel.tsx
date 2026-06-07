'use client';

import {
  TARGET_MONTHLY_REVENUE,
  calculateMonthlyRevenue,
  defaultRevenueModel,
  formatCurrency,
  getRevenueModeLabel,
  monthlyRevenuePlan,
  passiveIncomeAssets
} from '../lib/revenue-model';

export default function AutomatedIncomePanel() {
  const projection = calculateMonthlyRevenue(defaultRevenueModel);
  const gapLabel = projection.gapToTarget > 0
    ? `${formatCurrency(projection.gapToTarget)} gap remaining`
    : `${formatCurrency(Math.abs(projection.gapToTarget))} projected surplus`;

  return (
    <section className="grid two incomeGrid">
      <div className="panel">
        <p className="eyebrow">Automated income engine</p>
        <h2>Monthly Revenue Stack</h2>
        <p className="opsCopy">Protect the morning active-cash route, then use afternoons to convert completed work into retainers, dispatch margin, and repeatable automated assets.</p>

        <div className="revenueTotal">
          <span>Target {formatCurrency(TARGET_MONTHLY_REVENUE)}</span>
          <strong>{formatCurrency(projection.total)}</strong>
          <small>{gapLabel}</small>
        </div>

        <div className="planList">
          {monthlyRevenuePlan.map((line) => (
            <article className="planItem" key={line.label}>
              <div>
                <strong>{line.label}</strong>
                <span>{getRevenueModeLabel(line.mode)}</span>
              </div>
              <b>{formatCurrency(line.monthlyTarget)}</b>
              <p>{line.nextAction}</p>
            </article>
          ))}
        </div>
      </div>

      <div className="panel">
        <p className="eyebrow">Passive and semi-passive assets</p>
        <h2>Productized Income Queue</h2>
        <p className="opsCopy">These assets are designed to sell repeatedly, feed the technician network, or produce service leads without blocking field cash hours.</p>

        <div className="assetList">
          {passiveIncomeAssets.map((asset) => (
            <article className="asset" key={asset.name}>
              <strong>{asset.name}</strong>
              <span>{asset.offer}</span>
              <small>{asset.firstMilestone}</small>
              <b>{formatCurrency(asset.monthlyTarget)} target</b>
            </article>
          ))}
        </div>
      </div>
    </section>
  );
}
