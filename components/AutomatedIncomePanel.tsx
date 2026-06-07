'use client';

import {
  TARGET_OWNER_MONTHLY_INCOME,
  calculateMonthlyRevenue,
  calculateTechnicianExpansion,
  defaultRevenueModel,
  formatCurrency,
  getRevenueModeLabel,
  getTechnicianBandLabel,
  monthlyRevenuePlan,
  passiveIncomeAssets,
  technicianExpansionBands,
  technicianExpansionScenarios
} from '../lib/revenue-model';

export default function AutomatedIncomePanel() {
  const projection = calculateMonthlyRevenue(defaultRevenueModel);
  const gapLabel = projection.gapToTarget > 0
    ? `${formatCurrency(projection.gapToTarget)} owner-income gap remaining`
    : `${formatCurrency(Math.abs(projection.gapToTarget))} owner-income surplus before technician expansion`;
  const expansionResults = technicianExpansionScenarios.map((scenario) => calculateTechnicianExpansion(scenario, projection.ownerCompanyIncome));

  return (
    <section className="grid two incomeGrid">
      <div className="panel">
        <p className="eyebrow">Automated income engine</p>
        <h2>Owner / Company Monthly Income Floor</h2>
        <p className="opsCopy">The {formatCurrency(TARGET_OWNER_MONTHLY_INCOME)} target is for Already Here LLC income before technician expansion upside. Morning active work stays protected while afternoons build retainers, dispatch margin, and automated assets.</p>

        <div className="revenueTotal">
          <span>Owner/company target {formatCurrency(TARGET_OWNER_MONTHLY_INCOME)}</span>
          <strong>{formatCurrency(projection.ownerCompanyIncome)}</strong>
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
        <p className="eyebrow">Technician capacity upside</p>
        <h2>Per-Tech Monthly Lift</h2>
        <p className="opsCopy">Each qualified technician should increase monthly upside by roughly {formatCurrency(1500)} to {formatCurrency(4000)}, depending on experience, reliability, skill level, and how much QA-controlled work can be routed through them.</p>

        <div className="assetList">
          {technicianExpansionBands.map((band) => (
            <article className="asset" key={band.level}>
              <strong>{band.label}</strong>
              <span>{band.profile}</span>
              <small>{band.operatingRule}</small>
              <b>{formatCurrency(band.monthlyUpsidePerTech)} / tech / month</b>
            </article>
          ))}
        </div>

        <div className="planList expansionScenarios">
          {expansionResults.map((result) => (
            <article className="planItem" key={`${result.technicianCount}-${result.level}`}>
              <div>
                <strong>{result.technicianCount} {getTechnicianBandLabel(result.level)}</strong>
                <span>{formatCurrency(result.monthlyUpsidePerTech)} each</span>
              </div>
              <b>{formatCurrency(result.addedMonthlyUpside)}</b>
              <p>Total with owner/company floor: {formatCurrency(result.totalWithOwnerCompanyIncome)}</p>
            </article>
          ))}
        </div>
      </div>

      <div className="panel fullWidthPanel">
        <p className="eyebrow">Passive and semi-passive assets</p>
        <h2>Productized Income Queue</h2>
        <p className="opsCopy">These assets are designed to sell repeatedly, feed the technician network, or produce service leads without blocking field cash hours.</p>

        <div className="assetList threeColumnAssets">
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
