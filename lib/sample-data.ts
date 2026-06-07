import { buildLeadOpportunity } from './lead-mesh';
import type { ClientAccount, LeadOpportunity, Technician, WorkOrder } from './types';

export const initialTechnicians: Technician[] = [
  {
    id: 'tech-phx-001',
    name: 'Stephen Franklin',
    email: 'alreadyherellc@gmail.com',
    phone: 'available-on-file',
    country: 'United States',
    metro: 'Phoenix',
    postalCode: '85281',
    travelRadiusMiles: 60,
    skills: ['networking', 'pos', 'wireless', 'printer', 'computer', 'smart_hands', 'low_voltage', 'access_control', 'av', 'cabling', 'data_center', 'healthcare_device', 'procurement', 'retainer'],
    tools: ['laptop', 'console cable', 'patch cables', 'hotspot', 'hand tools', 'labeler'],
    hourlyRate: 65,
    availability: 'available',
    compliance: 'ready',
    performanceScore: 98,
    consentCapturedAt: new Date().toISOString(),
    referralCode: 'AH-PHX-001'
  }
];

export const initialClients: ClientAccount[] = [
  {
    id: 'client-ah-pipeline-001',
    company: 'Already Here LLC Revenue Pipeline',
    contactName: 'Stephen Franklin',
    email: 'alreadyherellc@gmail.com',
    phone: 'available-on-file',
    segment: 'Break/fix, retainer, procurement, and subcontractor coverage',
    retainerStatus: 'active',
    monthlyTarget: 5000
  }
];

export const initialWorkOrders: WorkOrder[] = [
  {
    id: 'wo-phx-direct-001',
    clientId: 'client-ah-pipeline-001',
    title: 'Phoenix POS and network support request',
    location: 'Phoenix Metro',
    metro: 'Phoenix',
    requiredSkills: ['networking', 'pos', 'smart_hands'],
    status: 'new',
    scheduledFor: new Date().toISOString(),
    budget: 250,
    estimatedHours: 2,
    urgency: 'same_day'
  }
];

export const initialLeadOpportunities: LeadOpportunity[] = [
  buildLeadOpportunity({
    source: 'Partner email channel',
    sourceType: 'authorized_email',
    category: 'retainer',
    organization: 'Telaid',
    title: 'Phoenix POS, cabling, and register break/fix preferred coverage',
    location: 'Phoenix Metro',
    metro: 'Phoenix',
    requiredSkills: ['pos', 'cabling', 'networking', 'smart_hands'],
    expectedValue: 3000,
    estimatedHours: 25,
    notes: 'Convert urgent one-off dispatch flow into reserved monthly Phoenix coverage.'
  }),
  buildLeadOpportunity({
    source: 'Partner email channel',
    sourceType: 'authorized_email',
    category: 'teaming',
    organization: 'Source Support / Source Techworks',
    title: 'Arizona HPE, data center, and smart-hands preferred field coverage',
    location: 'Arizona statewide with Phoenix priority',
    metro: 'Phoenix',
    requiredSkills: ['data_center', 'networking', 'smart_hands', 'computer'],
    expectedValue: 5000,
    estimatedHours: 40,
    notes: 'Position for guaranteed Arizona coverage block and urgent dispatch premium.'
  }),
  buildLeadOpportunity({
    source: 'Local procurement monitor',
    sourceType: 'public_procurement',
    category: 'procurement',
    organization: 'City and state procurement pipeline',
    title: 'Small-quote IT break/fix, low-voltage, and on-call field services roster',
    location: 'Phoenix, Mesa, Chandler, Tempe, Scottsdale, Glendale, Peoria, Surprise',
    metro: 'Phoenix',
    requiredSkills: ['procurement', 'networking', 'low_voltage', 'wireless', 'printer', 'computer'],
    expectedValue: 25000,
    estimatedHours: 120,
    deadline: 'rolling',
    notes: 'Target procurePHX, Arizona Procurement Portal, city vendor rosters, SBE/VBE recognition, and informal quote paths.'
  })
];
