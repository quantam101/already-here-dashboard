'use client';

import { useEffect, useMemo, useState } from 'react';
import ASIDistillationPanel from './ASIDistillationPanel';
import AutomatedIncomePanel from './AutomatedIncomePanel';
import PrimeNetworkPanel from './PrimeNetworkPanel';
import RevenuePanel from './RevenuePanel';
import { rankTechnicians } from '../lib/matching';
import { emptyState, loadState, saveState } from '../lib/store';
import { initialClients, initialTechnicians, initialWorkOrders } from '../lib/sample-data';
import type { AuditEvent, FieldNetworkState, Skill, Technician, WorkOrder } from '../lib/types';

const skills: Skill[] = [
  'networking', 'project_management', 'pos', 'av', 'access_control', 'cabling', 'wireless',
  'printer', 'smart_hands', 'computer', 'low_voltage', 'data_center', 'healthcare_device',
  'procurement', 'retainer'
];

const primaryModules = ['AI Web Agent', 'Customers', 'RFQs', 'Quotes', 'Dispatch', 'Technicians'];
const serviceModules = ['Field Service', 'Deployment Manager', 'Project Manager', 'Healthcare', 'Mechanic', 'Photo Quote', 'Printer Repair', 'POS Support', 'Low Voltage', 'CCTV', 'Access Control', 'Wireless'];
const quickActions = ['New Lead', 'New Quote', 'New Dispatch', 'New Customer', 'New Technician', 'New Project', 'Mechanic Intake', 'Photo Quote'];
const sidebar = ['Dashboard', 'AI Web Agent', 'CRM', 'Customers', 'Companies', 'Contacts', 'Leads', 'RFQs', 'Quotes', 'Dispatch', 'Technicians', 'Projects', 'Calendar', 'Revenue', 'Reports', 'Settings'];

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
          leadOpportunities: [],
          auditLog: [audit('system', 'seeded local AHOP operating database', 'system', 'bootstrap')],
          syncQueue: []
        };
        setState(seeded);
        void saveState(seeded);
        setSelectedWorkOrderId(initialWorkOrders[0]?.id ?? '');
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
  const activeWorkOrders = state.workOrders.filter((wo) => wo.status !== 'paid' && wo.status !== 'canceled').length;
  const openLeads = state.leadOpportunities.length;
  const availableTechs = state.technicians.filter((tech) => tech.availability === 'available').length;
  const queuedSync = state.syncQueue.filter((item) => !item.syncedAt).length;
  const projectedRevenue = state.workOrders.reduce((sum, wo) => sum + wo.budget, 0);

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
      title: selectedSkills.includes('project_management') ? 'New project/SOW field lead request' : 'New dispatch request',
      location: techMetro,
      metro: techMetro,
      requiredSkills: selectedSkills,
      status: 'new',
      scheduledFor: new Date().toISOString(),
      budget: selectedSkills.includes('project_management') ? 500 : 250,
      estimatedHours: selectedSkills.includes('project_management') ? 4 : 2,
      urgency: 'same_day'
    };
    const next = queueChange({
      ...state,
      workOrders: [workOrder, ...state.workOrders],
      auditLog: [audit('admin', 'created AHOP command center work order', 'work_order', workOrder.id), ...state.auditLog]
    }, 'create', 'work_order', workOrder.id, workOrder);
    setState(next);
    setSelectedWorkOrderId(workOrder.id);
  }

  function toggleSkill(skill: Skill) {
    setSelectedSkills((current) => current.includes(skill) ? current.filter((item) => item !== skill) : [...current, skill]);
  }

  return (
    <main className="ahopShell">
      <aside className="ahopSidebar">
        <div className="brandBlock"><span>Already Here LLC</span><strong>AHOP</strong><small>Operations Platform</small></div>
        <nav>{sidebar.map((item) => <a key={item} href={`#${item.toLowerCase().replaceAll(' ', '-')}`}>{item}</a>)}</nav>
      </aside>

      <section className="ahopMain">
        <section className="hero ahopHero">
          <div>
            <p className="eyebrow">Milestone 1 complete</p>
            <h1>AHOP Command Center</h1>
            <p className="subhead">Unified operational front door for AI Web Agent, CRM, RFQ, quotes, dispatch, technician network, field closeouts, documents, revenue, and future service modules.</p>
          </div>
          <div className="statusCard">
            <span className={online ? 'pill good' : 'pill warn'}>{online ? 'Cloud reachable' : 'Offline failover active'}</span>
            <strong>{queuedSync}</strong><small>queued sync events</small>
          </div>
        </section>

        <section className="grid stats commandStats">
          <Metric label="Projected Revenue" value={`$${projectedRevenue.toLocaleString()}`} />
          <Metric label="Open Leads" value={openLeads} />
          <Metric label="Open Dispatches" value={activeWorkOrders} />
          <Metric label="Technicians Available" value={availableTechs} />
          <Metric label="Projects / WOs" value={state.workOrders.length} />
        </section>

        <section className="panel commandPanel" id="dashboard">
          <div><h2>Command Center Modules</h2><p className="opsCopy">All core AHOP entry points are present. Backend live counts can attach to these cards without changing the operating layout.</p></div>
          <div className="moduleGrid">{primaryModules.map((module) => <ModuleCard key={module} title={module} status="Ready entry point" />)}</div>
        </section>

        <section className="grid two commandTwo">
          <div className="panel"><h2>Service Modules</h2><div className="moduleGrid small">{serviceModules.map((module) => <ModuleCard key={module} title={module} status="Module shell" />)}</div></div>
          <div className="panel"><h2>Quick Actions</h2><div className="quickGrid">{quickActions.map((action) => <button key={action} onClick={action.includes('Dispatch') ? addWorkOrder : undefined}>{`+ ${action}`}</button>)}</div></div>
        </section>

        <section className="grid two commandTwo">
          <div className="panel aiPanel" id="ai-web-agent"><h2>Lifelong Catch and Correct</h2><p className="opsCopy">Embedded AI assistant side panel placeholder for operational commands, lead routing, dispatch creation, RFQ triage, closeout QA, and proof-of-work review.</p><div className="promptList"><span>Create a dispatch for today's printer repair.</span><span>Show overdue RFQs.</span><span>Find the nearest Aruba wireless technician.</span><span>Generate a quote from an intake.</span></div></div>
          <div className="panel"><h2>Notifications</h2><div className="notificationList"><span>New Lead</span><span>New RFQ</span><span>Dispatch Assigned</span><span>Technician Checked In</span><span>Quote Accepted</span><span>Invoice Paid</span></div></div>
        </section>

        <ASIDistillationPanel state={state} />
        <RevenuePanel />
        <AutomatedIncomePanel />
        <PrimeNetworkPanel technicianCount={state.technicians.length} clientCount={state.clients.length} workOrderCount={state.workOrders.length} />

        <section className="grid two">
          <div className="panel" id="technicians">
            <h2>Opt-In Technician Intake</h2>
            <input value={techName} onChange={(event) => setTechName(event.target.value)} placeholder="Technician legal name" />
            <input value={techEmail} onChange={(event) => setTechEmail(event.target.value)} placeholder="Email" />
            <input value={techMetro} onChange={(event) => setTechMetro(event.target.value)} placeholder="Metro" />
            <input type="number" value={techRate} onChange={(event) => setTechRate(Number(event.target.value))} placeholder="Hourly rate" />
            <div className="chips">{skills.map((skill) => <button key={skill} className={selectedSkills.includes(skill) ? 'chip active' : 'chip'} onClick={() => toggleSkill(skill)}>{skill.replace('_', ' ')}</button>)}</div>
            <button className="primary" onClick={addTechnician}>Add technician and queue audit event</button>
          </div>

          <div className="panel" id="dispatch">
            <h2>Work Order Command</h2>
            <select value={selectedWorkOrder?.id ?? ''} onChange={(event) => setSelectedWorkOrderId(event.target.value)}>
              {state.workOrders.map((wo) => <option key={wo.id} value={wo.id}>{wo.title} — {wo.metro}</option>)}
            </select>
            <button className="secondary" onClick={addWorkOrder}>Create same-day work order from selected skills</button>
            {selectedWorkOrder && <div className="detail"><strong>{selectedWorkOrder.title}</strong><span>{selectedWorkOrder.location}</span><span>${selectedWorkOrder.budget} / {selectedWorkOrder.estimatedHours} hrs</span></div>}
          </div>
        </section>

        <section className="panel"><h2>Deterministic Match Results</h2><div className="cards">{matches.map((match) => <article className="match" key={match.technician.id}><div><strong>{match.technician.name}</strong><span>{match.technician.metro} · ${match.technician.hourlyRate}/hr</span></div><b>{match.score}</b><p>{match.reasons.join(' · ') || 'No positive match reason recorded'}</p>{match.riskFlags.length > 0 && <small>Risk: {match.riskFlags.join(' · ')}</small>}</article>)}</div></section>

        <section className="grid two"><div className="panel"><h2>Technician Network</h2>{state.technicians.map((tech) => <p key={tech.id} className="row"><strong>{tech.name}</strong><span>{tech.metro} · {tech.skills.length} skills · {tech.compliance}</span></p>)}</div><div className="panel"><h2>Audit Log</h2>{state.auditLog.slice(0, 8).map((event) => <p key={event.id} className="row"><strong>{event.action}</strong><span>{new Date(event.createdAt).toLocaleString()}</span></p>)}</div></section>
      </section>

      <nav className="mobileNav"><a href="#dashboard">Dashboard</a><a href="#ai-web-agent">AI</a><a href="#dispatch">Dispatch</a><a href="#revenue">Revenue</a><a href="#settings">More</a></nav>
    </main>
  );
}

function Metric({ label, value }: { label: string; value: number | string }) {
  return <div className="metric"><strong>{value}</strong><span>{label}</span></div>;
}

function ModuleCard({ title, status }: { title: string; status: string }) {
  return <article className="moduleCard"><strong>{title}</strong><span>{status}</span></article>;
}

function audit(actor: string, action: string, entityType: string, entityId: string): AuditEvent {
  return { id: crypto.randomUUID(), actor, action, entityType, entityId, createdAt: new Date().toISOString() };
}

function queueChange<T>(state: FieldNetworkState, operation: 'create' | 'update' | 'delete', entityType: string, entityId: string, payload: T): FieldNetworkState {
  return { ...state, syncQueue: [{ id: crypto.randomUUID(), operation, entityType, entityId, payload, createdAt: new Date().toISOString() }, ...state.syncQueue] };
}
