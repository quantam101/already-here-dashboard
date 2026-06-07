'use client';

interface PrimeNetworkPanelProps {
  technicianCount: number;
  clientCount: number;
  workOrderCount: number;
}

const readinessItems = [
  {
    label: 'Client intake and work-order command',
    status: 'Live in dashboard',
    owner: 'Operations'
  },
  {
    label: 'Opt-in technician onboarding',
    status: 'Live local-first',
    owner: 'Network'
  },
  {
    label: 'Proceed / Counter / Discard queue',
    status: 'Live with suppression logic',
    owner: 'Revenue'
  },
  {
    label: 'W-9 / MSA / COI vendor packet',
    status: 'Next signature workflow',
    owner: 'Compliance'
  },
  {
    label: 'Prime-contractor capability packet',
    status: 'Prepare from completed work evidence',
    owner: 'Business development'
  },
  {
    label: 'Oracle backend sync',
    status: 'Queued for hardened backend phase',
    owner: 'Platform'
  }
];

const primeTargets = [
  {
    market: 'Phoenix proof market',
    target: '10 vetted technicians and 5 repeat clients',
    progressBase: 10
  },
  {
    market: 'Southwest expansion',
    target: 'Arizona, Las Vegas, San Diego, Albuquerque, El Paso',
    progressBase: 5
  },
  {
    market: 'Nationwide dispatch layer',
    target: '250 opted-in technicians across priority metros',
    progressBase: 1
  }
];

export default function PrimeNetworkPanel({ technicianCount, clientCount, workOrderCount }: PrimeNetworkPanelProps) {
  const proofScore = Math.min(100, Math.round(((technicianCount * 7) + (clientCount * 10) + (workOrderCount * 5))));

  return (
    <section className="grid two primeGrid">
      <div className="panel">
        <p className="eyebrow">Prime network control</p>
        <h2>Prime Contractor Readiness</h2>
        <p className="opsCopy">The target is not just more field work. The target is becoming the trusted field-technology capacity layer that clients, MSPs, vendors, and primes call when they need qualified technicians.</p>

        <div className="readinessScore">
          <span>Proof score</span>
          <strong>{proofScore}%</strong>
          <small>Based on technician count, client count, and work-order history captured in the local operating system.</small>
        </div>

        <div className="readinessList">
          {readinessItems.map((item) => (
            <article className="readinessItem" key={item.label}>
              <strong>{item.label}</strong>
              <span>{item.status}</span>
              <small>{item.owner}</small>
            </article>
          ))}
        </div>
      </div>

      <div className="panel">
        <p className="eyebrow">Nationwide capacity path</p>
        <h2>Coverage Milestones</h2>
        <p className="opsCopy">Build local proof first, then add regional and national coverage only where dispatch quality, compliance, and margin can be controlled.</p>

        <div className="coverageList">
          {primeTargets.map((target) => {
            const progress = Math.min(100, target.progressBase * Math.max(technicianCount, 1));
            return (
              <article className="coverageItem" key={target.market}>
                <div>
                  <strong>{target.market}</strong>
                  <span>{target.target}</span>
                </div>
                <div className="coverageBar" aria-label={`${target.market} progress`}>
                  <span style={{ width: `${progress}%` }} />
                </div>
                <small>{progress}% network maturity estimate</small>
              </article>
            );
          })}
        </div>

        <div className="decisionBox">
          <strong>Operating rule</strong>
          <span>Morning work funds the system. The system removes Stephen as the bottleneck by capturing technician capacity, QA evidence, repeat clients, and dispatch margin.</span>
        </div>
      </div>
    </section>
  );
}
