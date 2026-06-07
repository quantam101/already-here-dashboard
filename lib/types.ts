export type Skill =
  | 'networking'
  | 'project_management'
  | 'pos'
  | 'av'
  | 'access_control'
  | 'cabling'
  | 'wireless'
  | 'printer'
  | 'smart_hands'
  | 'computer'
  | 'low_voltage'
  | 'data_center'
  | 'healthcare_device'
  | 'procurement'
  | 'retainer';

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

export type OpportunityCategory =
  | 'break_fix'
  | 'retainer'
  | 'procurement'
  | 'project_management'
  | 'teaming'
  | 'field_dispatch'
  | 'hauling'
  | 'admin';

export type LeadSourceType =
  | 'authorized_email'
  | 'official_portal'
  | 'public_procurement'
  | 'partner_channel'
  | 'manual_public_listing';

export type LeadDecisionStatus =
  | 'new'
  | 'review'
  | 'proceed'
  | 'counter'
  | 'discard'
  | 'submitted'
  | 'won'
  | 'lost';

export type LeadGrade = 'A' | 'B' | 'C' | 'Avoid';
export type SkillDepth = 'basic' | 'intermediate' | 'advanced' | 'lead';
export type JobComplexity = 'simple' | 'standard' | 'complex' | 'large_project';
export type DispatchRole = 'helper' | 'field_tech' | 'specialist' | 'project_lead';
export type TeamBuildAction = 'solo_dispatch' | 'pair_with_lead' | 'build_project_team' | 'reserve_for_better_fit';

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
  skillDepth?: SkillDepth;
  preferredDispatchRole?: DispatchRole;
  leadEligible?: boolean;
  multiStateLeadEligible?: boolean;
  mentorshipEligible?: boolean;
  certifications?: string[];
  degrees?: string[];
  additionalSkills?: string[];
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
  complexity?: JobComplexity;
  teamSize?: number;
  requiresLead?: boolean;
  multiStateProject?: boolean;
  preserveSeniorCapacity?: boolean;
  status: WorkOrderStatus;
  scheduledFor: string;
  budget: number;
  estimatedHours: number;
  urgency: 'same_day' | 'next_day' | 'scheduled';
}

export interface LeadOpportunity {
  id: string;
  capturedAt: string;
  source: string;
  sourceType: LeadSourceType;
  category: OpportunityCategory;
  organization: string;
  title: string;
  url?: string;
  location: string;
  metro: string;
  deadline?: string;
  requiredSkills: Skill[];
  expectedValue: number;
  estimatedHours: number;
  effectiveHourly: number;
  minimumAcceptableValue: number;
  grade: LeadGrade;
  confidence: number;
  decisionStatus: LeadDecisionStatus;
  riskFlags: string[];
  counterRequired: boolean;
  nextAction: string;
  counterMessage: string;
  complianceMode: string;
  notes: string;
}

export interface MatchResult {
  technician: Technician;
  score: number;
  reasons: string[];
  riskFlags: string[];
  recommendedRole: DispatchRole;
  teamBuildAction: TeamBuildAction;
}

export interface TeamRecommendation {
  workOrder: WorkOrder;
  lead?: MatchResult;
  fieldTechs: MatchResult[];
  supportTechs: MatchResult[];
  summary: string;
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
  leadOpportunities?: LeadOpportunity[];
  auditLog: AuditEvent[];
  syncQueue: SyncEvent[];
}
