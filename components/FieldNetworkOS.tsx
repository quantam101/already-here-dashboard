'use client';

import { useEffect, useMemo, useState } from 'react';
import { rankTechnicians } from '../lib/matching';
import { emptyState, loadState, saveState } from '../lib/store';
import { initialClients, initialTechnicians, initialWorkOrders } from '../lib/sample-data';
import type { AuditEvent, FieldNetworkState, Skill, Technician, WorkOrder } from '../lib/types';

const skills: Skill[] = ['networking', 'pos', 'av', 'access_control', 'cabling', 'wireless', 'printer', 'smart_hands', 'computer', 'low_voltage'];

export default function FieldNetworkOS() {
  const [state, setState] = useState<FieldNetworkState>(emptyState);
  const [online, setOnline] = useState(true);
  const [selectedWorkOrderId, setSelectedWorkOrderId] = useState('');
  const [techName, setTechName] = useState('');
  const [techMetro, setTechMetro] = useState('Phoenix');
  const [techEmail, setTechEmail] = useState('');
  const [techRate, setTechRate] = useState(65);
  const [selectedSkills, setSelectedSkills] = useState<Skill[]>(['networking', 'smart_hands']);

  useEffect(() => {
    setOnline(navigator.onLine);
    const onOnline = () => setOnline(true);
    const onOffline = () => setOnline(false);
    window.addEventListener('online', onOnline);
    window.addEventListener('offline', onOffline);
    loadState().then((saved) => {
      if (saved.technicians.length === 0 && saved.clients.length === 0 && saved.workOrders.length === 0) {
        const seeded: FieldNetworkState = {
          technicians: initialTechnicians,
          clients: initialClients,
          workOrders: initialWorkOrders,
          auditLog: [audit('system', 'seeded local operating database', 'system', 'bootstrap')],
          syncQueue: []
        };
        setState(seeded);
        void saveState(seeded);
        setSelectedWorkOrderId(initialWorkOrders[0].id);
      } else {
        setState(saved);
        setSelectedWorkOrderId(saved.workOrders[0]?.id ?? '');
      }
    });
    return () => {
      window.removeEventListener('online', onOnline);
      window.removeEventListener('offline', onOffline);
    };
  }, []);

  useEffect(() => {
    if (state !== emptyState) void saveState(state);
  }, [state]);

  const selectedWorkOrder = state.workOrders.find((wo) => wo.id === selectedWorkOrderId) ?? state.workOrders[0];
  const matches = useMemo(() => (selectedWorkOrder ? rankTechnicians(selectedWorkOrder, state.technicians) : []), [selectedWorkOrder, state.technicians]);

  function addTechnician() {
    if (!techName.trim() || !techEmail.trim()) return;
    const technician: Technician = {
      id: `tech-${crypto.randomUUID()}`,
      name: techName.trim(),
      email: techEmail.trim(),
      phone: 'pending',
      country: 'United States',
      metro: techMetro.trim(),
      postalCode: 'pending',
      travelRadiusMiles: 60,
      skills: selectedSkills,
      tools: ['laptop', 'mobile phone', 'standard field kit'],
      hourlyRate: techRate,
      availability: 'available',
      compliance: 'needs_docs',
      performanceScore: 75,
      consentCapturedAt: new Date().toISOString(),
      referralCode: `AH-${techMetro.slice(0, 3).toUpperCase()}-${state.technicians.length + 1}`
    };
    const next = queueChange({
      ...state,
      technicians: [...state.technicians, technician],
      auditLog: [audit('admin', 'added technician with opt-in consent record', 'technician', technician.id), ...state.auditLog]
    }, 'create', 'technician', technician.id, technician);
    setState(next);
    setTechName('');
    setTechEmail('');
  }

  function addWorkOrder() {
    const workOrder: WorkOrder = {
      id: `wo-${crypto.randomUUID()}`,
      clientId: state.clients[0]?.id ?? 'client-direct-001',
      title: 'New dispatch request',
      location: techMetro,
      metro: techMetro,
      requiredSkills: selectedSkills,
      status: 'new',
      scheduledFor: new Date().toISOString(),
      budget: 250,
      estimatedHours: 2,
      urgency: 'same_day'
    };
    const next = queueChange({
      ...state,
      workOrders: [workOrder, ...state.workOrders],
      auditLog: [audit('admin', 'created work order', 'work_order', workOrder.id), ...state.auditLog]
    }, 'create', 'work_order', workOrder.id, workOrder);
    setState(next);
    setSelectedWorkOrderId(workOrder.id);
  }

  function toggleSkill(skill: Skill) {
    setSelectedSkills((current) => current.includes(skill) ? current.filter((item) => item !== skill) : [...current, skill]);
  }

  return (
    <main className="shell">
      <section className="hero">
        <div>
          <p className="eyebrow">Already Here LLC</p>
          <h1>Field Network OS</h1>
          <p className="subhead">Technician network, dispatch matching, retainer tracking, offline queue, and audit control.</p>
        </div>
        <div className="statusCard">
          <span className={online ? 'pill good' : 'pill warn'}>{online ? 'Cloud reachable' : 'Offline failover active'}</span>
          <strong>{state.syncQueue.filter((item) => !item.syncedAt).length}</strong>
          <small>queued sync events</small>
        </div>
      </section>

      <section className="grid stats">
        <Metric label="Technicians" value={state.technicians.length} />
        <Metric label="Clients" value={state.clients.length} />
        <Metric label="Work Orders" value={state.workOrders.length} />
        <Metric label="Retainer Targets" value={state.clients.filter((c) => c.retainerStatus !== 'active').length} />
      </section>

      <section className="panel opsPanel">
        <div>
          <p className="eyebrow">ProfitEngine backbone</p>
          <h2>Production Agent Mesh</h2>
          <p className="opsCopy">Live proof-first revenue ops, signed edge failover, mesh readiness, and profitability gates.</p>
        </div>
        <div className="opsLinks">
          <a href="https://profitenginev5.vercel.app/api/health" target="_blank" rel="noreferrer">Health</a>
          <a href="https://profitenginev5.vercel.app/api/enterprise-mesh" target="_blank" rel="noreferrer">Mesh</a>
          <a href="https://profitenginev5.vercel.app/api/edge-failover" target="_blank" rel="noreferrer">Failover</a>
          <a href="https://profitenginev5.vercel.app/api/profitability" target="_blank" rel="noreferrer">Profitability</a>
        </div>
      </section>

      <section className="grid two">
        <div className="panel">
          <h2>Opt-In Technician Intake</h2>
          <input value={techName} onChange={(event) => setTechName(event.target.value)} placeholder="Technician legal name" />
          <input value={techEmail} onChange={(event) => setTechEmail(event.target.value)} placeholder="Email" />
          <input value={techMetro} onChange={(event) => setTechMetro(event.target.value)} placeholder="Metro" />
          <input type="number" value={techRate} onChange={(event) => setTechRate(Number(event.target.value))} placeholder="Hourly rate" />
          <div className="chips">
            {skills.map((skill) => <button key={skill} className={selectedSkills.includes(skill) ? 'chip active' : 'chip'} onClick={() => toggleSkill(skill)}>{skill.replace('_', ' ')}</button>)}
          </div>
          <button className="primary" onClick={addTechnician}>Add technician and queue audit event</button>
        </div>

        <div className="panel">
          <h2>Work Order Command</h2>
          <select value={selectedWorkOrder?.id ?? ''} onChange={(event) => setSelectedWorkOrderId(event.target.value)}>
            {state.workOrders.map((wo) => <option key={wo.id} value={wo.id}>{wo.title} — {wo.metro}</option>)}
          </select>
          <button className="secondary" onClick={addWorkOrder}>Create same-day work order from selected skills</button>
          {selectedWorkOrder && <div className="detail"><strong>{selectedWorkOrder.title}</strong><span>{selectedWorkOrder.location}</span><span>${selectedWorkOrder.budget} / {selectedWorkOrder.estimatedHours} hrs</span></div>}
        </div>
      </section>

      <section className="panel">
        <h2>Deterministic Match Results</h2>
        <div className="cards">
          {matches.map((match) => (
            <article className="match" key={match.technician.id}>
              <div><strong>{match.technician.name}</strong><span>{match.technician.metro} · ${match.technician.hourlyRate}/hr</span></div>
              <b>{match.score}</b>
              <p>{match.reasons.join(' · ') || 'No positive match reason recorded'}</p>
              {match.riskFlags.length > 0 && <small>Risk: {match.riskFlags.join(' · ')}</small>}
            </article>
          ))}
        </div>
      </section>

      <section className="grid two">
        <div className="panel">
          <h2>Technician Network</h2>
          {state.technicians.map((tech) => <p key={tech.id} className="row"><strong>{tech.name}</strong><span>{tech.metro} · {tech.skills.length} skills · {tech.compliance}</span></p>)}
        </div>
        <div className="panel">
          <h2>Audit Log</h2>
          {state.auditLog.slice(0, 8).map((event) => <p key={event.id} className="row"><strong>{event.action}</strong><span>{new Date(event.createdAt).toLocaleString()}</span></p>)}
        </div>
      </section>
    </main>
  );
}

function Metric({ label, value }: { label: string; value: number }) {
  return <div className="metric"><strong>{value}</strong><span>{label}</span></div>;
}

function audit(actor: string, action: string, entityType: string, entityId: string): AuditEvent {
  return { id: crypto.randomUUID(), actor, action, entityType, entityId, createdAt: new Date().toISOString() };
}

function queueChange<T>(state: FieldNetworkState, operation: 'create' | 'update' | 'delete', entityType: string, entityId: string, payload: T): FieldNetworkState {
  return {
    ...state,
    syncQueue: [
      { id: crypto.randomUUID(), operation, entityType, entityId, payload, createdAt: new Date().toISOString() },
      ...state.syncQueue
    ]
  };
}
