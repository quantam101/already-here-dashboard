import type { ClientAccount, Technician, WorkOrder } from './types';

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
    skills: ['networking', 'pos', 'wireless', 'printer', 'computer', 'smart_hands', 'low_voltage', 'access_control', 'av', 'cabling'],
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
    id: 'client-direct-001',
    company: 'Direct Dispatch Target',
    contactName: 'Vendor Manager',
    email: 'vendor@example.invalid',
    phone: 'pending',
    segment: 'MSP / Dispatch / Integrator',
    retainerStatus: 'target',
    monthlyTarget: 2500
  }
];

export const initialWorkOrders: WorkOrder[] = [
  {
    id: 'wo-sample-001',
    clientId: 'client-direct-001',
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
