'use client';

import {
  TARGET_OWNER_MONTHLY_INCOME,
  VERIFIED_SKILL_PREMIUM_MAX,
  VERIFIED_SKILL_PREMIUM_MIN,
  calculateDispatchMargin,
  calculateMonthlyRevenue,
  calculateTechnicianContribution,
  defaultRevenueModel,
  dispatchMarginExamples,
  formatCurrency,
  getRevenueModeLabel,
  getTechnicianContributionLabel,
  jobRatePolicies,
  monthlyRevenuePlan,
  passiveIncomeAssets,
  technicianContributionEstimates,
  technicianContributionScenarios
} from '../lib/revenue-model';

export default function AutomatedIncomePanel() {
  const projection = calculateMonthlyRevenue(defaultRevenueModel);
  const gapLabel = projection.gapToTarget > 0
    ? `${formatCurrency(projection.gapToTarget)} owner-income gap remaining`
    : `${formatCurrency(Math.abs(projection.gapToTarget))} owner-income surplus before technician-network upside`;
  const contributionResults = technicianContributionScenarios.map((scenario) => calculateTechnicianContribution(scenario, projection.ownerCompanyIncome));
  const marginResults = dispatchMarginExamples.map((example) => ({ example, result: calculateDispatchMargin(example) }));

  return (
    <section className="grid two incomeGrid">
      <div className="panel">
        <p className="eyebrow">Automated income engine</p>
        <h2>Owner / Company Monthly Income Floor</h2>
        <p className="opsCopy">The {formatCurrency(TARGET_OWNER_MONTHLY_INCOME)} target is for Already Here LLC owner/company income before technician-network upside. Morning active work stays protected while afternoons build retainers, dispatch margin, and automated assets.</p>

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
        <p className="eyebrow">Rate and payout control</p>
        <h2>Job Rate First, Tech Payout Second</h2>
        <p className="opsCopy">Already Here LLC sets the client/job rate by job type and market first. Technician payout is then negotiated inside the margin, with verified certifications, degrees, licenses, tools, and additional skills able to justify roughly {formatCurrency(VERIFIED_SKILL_PREMIUM_MIN)}–{formatCurrency(VERIFIED_SKILL_PREMIUM_MAX)} more per hour when the job supports it.</p>

        <div className="assetList">
          {jobRatePolicies.map((policy) => (
            <article className="asset" key={policy.label}>
              <strong>{policy.label}</strong>
              <span>{policy.pricingRule}</span>
              <small>{policy.techPayoutRule}</small>
              <small>{policy.locationRule}</small>
            </article>
          ))}
        </div>
      </div>

      <div className="panel">
        <p className="eyebrow">Dispatch margin examples</p>
        <h2>Company Income = Margin × Volume</h2>
        <p className="opsCopy">These examples show the calculation structure. Actual rates stay configurable by job, location, demand, urgency, scope, and negotiated technician payout.</p>

        <div className="planList expansionScenarios">
          {marginResults.map(({ example, result }) => (
            <article className="planItem" key={`${example.clientBillRateHourly}-${example.technicianBasePayoutHourly}-${example.verifiedSkillPremiumHourly}`}>
              <div>
                <strong>{formatCurrency(example.clientBillRateHourly)}/hr client rate · {example.jobsPerMonth} jobs/month</strong>
                <span>Tech payout {formatCurrency(result.effectiveTechPayoutHourly)}/hr after premium</span>
              </div>
              <b>{formatCurrency(result.monthlyCompanyIncomeLift)}</b>
              <p>{formatCurrency(result.grossMarginHourly)}/hr margin · {formatCurrency(result.grossMarginPerJob)} per job · {result.marginIsViable ? 'viable margin' : 'not viable'}</p>
            </article>
          ))}
        </div>
      </div>

      <div className="panel">
        <p className="eyebrow">Technician network upside</p>
        <h2>Company Net Contribution Estimates</h2>
        <p className="opsCopy">These are planning estimates for Already Here LLC income lift, not technician pay rates. The actual lift depends on our client rate, negotiated tech payout, location, route density, work volume, urgency, QA, and repeat demand.</p>

        <div className="assetList">
          {technicianContributionEstimates.map((estimate) => (
            <article className="asset" key={estimate.profile}>
              <strong>{estimate.label}</strong>
              <span>{estimate.locationLogic}</span>
              <small>{estimate.workVolumeLogic}</small>
              <small>{estimate.marginLogic}</small>
              <b>{formatCurrency(estimate.estimatedCompanyIncomeMin)}–{formatCurrency(estimate.estimatedCompanyIncomeMax)} company lift / tech / month</b>
            </article>
          ))}
        </div>

        <div className="planList expansionScenarios">
          {contributionResults.map((result) => (
            <article className="planItem" key={`${result.technicianCount}-${result.profile}`}>
              <div>
                <strong>{result.technicianCount} techs · {getTechnicianContributionLabel(result.profile)}</strong>
                <span>{formatCurrency(result.estimatedCompanyIncomeMin)}–{formatCurrency(result.estimatedCompanyIncomeMax)} estimated company lift each</span>
              </div>
              <b>{formatCurrency(result.addedMonthlyIncomeMin)}–{formatCurrency(result.addedMonthlyIncomeMax)}</b>
              <p>Total with owner/company floor: {formatCurrency(result.totalWithOwnerCompanyIncomeMin)}–{formatCurrency(result.totalWithOwnerCompanyIncomeMax)}</p>
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
