export type Skill =
  | 'networking'
  | 'pos'
  | 'av'
  | 'access_control'
  | 'cabling'
  | 'wireless'
  | 'printer'
  | 'smart_hands'
  | 'computer'
  | 'low_voltage';

export type WorkOrderStatus =
  | 'new'
  | 'reviewing'
  | 'quoted'
  | 'approved'
  | 'assigned'
  | 'en_route'
  | 'onsite'
  | 'blocked'
  | 'complete'
  | 'closeout_pending'
  | 'invoiced'
  | 'paid'
  | 'canceled';

export interface Technician {
  id: string;
  name: string;
  email: string;
  phone: string;
  country: string;
  metro: string;
  postalCode: string;
  travelRadiusMiles: number;
  skills: Skill[];
  tools: string[];
  hourlyRate: number;
  availability: 'available' | 'limited' | 'unavailable';
  compliance: 'ready' | 'needs_docs' | 'blocked';
  performanceScore: number;
  consentCapturedAt: string;
  referralCode?: string;
}

export interface ClientAccount {
  id: string;
  company: string;
  contactName: string;
  email: string;
  phone: string;
  segment: string;
  retainerStatus: 'target' | 'proposed' | 'active' | 'paused';
  monthlyTarget: number;
}

export interface WorkOrder {
  id: string;
  clientId: string;
  title: string;
  location: string;
  metro: string;
  requiredSkills: Skill[];
  status: WorkOrderStatus;
  scheduledFor: string;
  budget: number;
  estimatedHours: number;
  urgency: 'same_day' | 'next_day' | 'scheduled';
}

export interface MatchResult {
  technician: Technician;
  score: number;
  reasons: string[];
  riskFlags: string[];
}

export interface AuditEvent {
  id: string;
  actor: string;
  action: string;
  entityType: string;
  entityId: string;
  createdAt: string;
}

export interface SyncEvent {
  id: string;
  operation: 'create' | 'update' | 'delete';
  entityType: string;
  entityId: string;
  payload: unknown;
  createdAt: string;
  syncedAt?: string;
}

export interface FieldNetworkState {
  technicians: Technician[];
  clients: ClientAccount[];
  workOrders: WorkOrder[];
  auditLog: AuditEvent[];
  syncQueue: SyncEvent[];
}
