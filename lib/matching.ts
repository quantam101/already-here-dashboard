import type {
  DispatchRole,
  JobComplexity,
  MatchResult,
  SkillDepth,
  TeamBuildAction,
  TeamRecommendation,
  Technician,
  WorkOrder
} from './types';

const depthRank: Record<SkillDepth, number> = {
  basic: 1,
  intermediate: 2,
  advanced: 3,
  lead: 4
};

const complexityRank: Record<JobComplexity, number> = {
  simple: 1,
  standard: 2,
  complex: 3,
  large_project: 4
};

export function rankTechnicians(workOrder: WorkOrder, technicians: Technician[]): MatchResult[] {
  return technicians
    .map((technician) => scoreTechnician(workOrder, technician))
    .filter((result) => result.score > 0)
    .sort((a, b) => b.score - a.score);
}

export function buildTeamRecommendation(workOrder: WorkOrder, technicians: Technician[]): TeamRecommendation {
  const ranked = rankTechnicians(workOrder, technicians);
  const requiredTeamSize = Math.max(workOrder.teamSize ?? 1, 1);
  const lead = ranked.find((match) => match.recommendedRole === 'project_lead');
  const fieldTechs = ranked
    .filter((match) => match.recommendedRole === 'field_tech' || match.recommendedRole === 'specialist')
    .slice(0, requiredTeamSize);
  const supportTechs = ranked
    .filter((match) => match.recommendedRole === 'helper')
    .slice(0, Math.max(requiredTeamSize - fieldTechs.length, 0));
  const riskFlags = ranked.flatMap((match) => match.riskFlags).filter(Boolean);

  const summary = lead
    ? `Use ${lead.technician.name} as lead and combine right-fit techs underneath for scope coverage.`
    : 'Use right-fit technician matching; do not waste senior capacity on simple work unless no better fit is available.';

  return { workOrder, lead, fieldTechs, supportTechs, summary, riskFlags };
}

function scoreTechnician(workOrder: WorkOrder, technician: Technician): MatchResult {
  let score = 0;
  const reasons: string[] = [];
  const riskFlags: string[] = [];
  const complexity = workOrder.complexity ?? inferComplexity(workOrder);
  const technicianDepth = technician.skillDepth ?? inferTechnicianDepth(technician);
  const skillGap = depthRank[technicianDepth] - complexityRank[complexity];
  const matchingSkills = workOrder.requiredSkills.filter((skill) => technician.skills.includes(skill));
  const recommendedRole = recommendRole(workOrder, technician, complexity, technicianDepth);
  const teamBuildAction = recommendTeamBuildAction(workOrder, technician, complexity, technicianDepth, matchingSkills.length);

  if (matchingSkills.length > 0) {
    score += matchingSkills.length * 25;
    reasons.push(`${matchingSkills.length} required skill match(es)`);
  }

  if (matchingSkills.length === workOrder.requiredSkills.length) {
    score += 20;
    reasons.push('complete required skill coverage');
  }

  if (technician.availability === 'available') {
    score += 20;
    reasons.push('available now');
  } else if (technician.availability === 'limited') {
    score += 5;
    riskFlags.push('limited availability');
  } else {
    score -= 40;
    riskFlags.push('unavailable');
  }

  if (technician.compliance === 'ready') {
    score += 20;
    reasons.push('compliance ready');
  } else if (technician.compliance === 'needs_docs') {
    score -= 20;
    riskFlags.push('missing compliance documents');
  } else {
    score -= 100;
    riskFlags.push('compliance blocked');
  }

  if (sameMetro(workOrder.metro, technician.metro)) {
    score += 20;
    reasons.push('same metro');
  } else if (workOrder.multiStateProject && technician.multiStateLeadEligible) {
    score += 15;
    reasons.push('multi-state lead eligible');
  }

  const effectiveHourly = workOrder.budget / Math.max(workOrder.estimatedHours, 1);
  if (effectiveHourly >= technician.hourlyRate) {
    score += 15;
    reasons.push('rate fits budget');
  } else {
    score -= 15;
    riskFlags.push('rate exceeds work order budget');
  }

  score += Math.round(technician.performanceScore / 5);
  if (technician.performanceScore >= 90) reasons.push('high performance score');

  if (workOrder.urgency === 'same_day' && technician.availability !== 'available') {
    score -= 20;
    riskFlags.push('same-day urgency with weak availability');
  }

  if (skillGap === 0 || skillGap === 1) {
    score += 18;
    reasons.push('right-sized skill depth for scope');
  }

  if ((complexity === 'simple' || complexity === 'standard') && skillGap >= 2 && workOrder.preserveSeniorCapacity !== false) {
    score -= 22;
    riskFlags.push('overqualified for scope; preserve senior capacity');
  }

  if ((complexity === 'complex' || complexity === 'large_project') && skillGap < 0) {
    score -= 35;
    riskFlags.push('skill depth below job complexity');
  }

  if (workOrder.requiresLead && technician.leadEligible) {
    score += 25;
    reasons.push('lead eligible for project coordination');
  } else if (workOrder.requiresLead && !technician.leadEligible) {
    score -= 25;
    riskFlags.push('lead required but technician is not lead eligible');
  }

  if (workOrder.multiStateProject && technician.multiStateLeadEligible) {
    score += 30;
    reasons.push('fit for multi-state project lead role');
  }

  if (technician.mentorshipEligible && (complexity === 'complex' || complexity === 'large_project')) {
    score += 10;
    reasons.push('can mentor and combine techs into a stronger team');
  }

  return {
    technician,
    score: Math.max(score, 0),
    reasons,
    riskFlags,
    recommendedRole,
    teamBuildAction
  };
}

function inferComplexity(workOrder: WorkOrder): JobComplexity {
  if (workOrder.teamSize && workOrder.teamSize >= 3) return 'large_project';
  if (workOrder.requiresLead || workOrder.multiStateProject || workOrder.budget >= 2500) return 'complex';
  if (workOrder.requiredSkills.length <= 2 && workOrder.estimatedHours <= 2) return 'simple';
  return 'standard';
}

function inferTechnicianDepth(technician: Technician): SkillDepth {
  if (technician.skillDepth) return technician.skillDepth;
  if (technician.leadEligible || technician.performanceScore >= 94 || technician.skills.length >= 10) return 'lead';
  if (technician.performanceScore >= 88 || technician.skills.length >= 7) return 'advanced';
  if (technician.skills.length >= 4) return 'intermediate';
  return 'basic';
}

function recommendRole(
  workOrder: WorkOrder,
  technician: Technician,
  complexity: JobComplexity,
  technicianDepth: SkillDepth
): DispatchRole {
  if ((workOrder.requiresLead || workOrder.multiStateProject || complexity === 'large_project') && technician.leadEligible) return 'project_lead';
  if (technicianDepth === 'lead' && (complexity === 'complex' || complexity === 'large_project')) return 'project_lead';
  if (technicianDepth === 'advanced' || technicianDepth === 'lead') return 'specialist';
  if (technicianDepth === 'basic') return 'helper';
  return 'field_tech';
}

function recommendTeamBuildAction(
  workOrder: WorkOrder,
  technician: Technician,
  complexity: JobComplexity,
  technicianDepth: SkillDepth,
  matchingSkillCount: number
): TeamBuildAction {
  if ((workOrder.requiresLead || workOrder.multiStateProject || complexity === 'large_project') && technician.leadEligible) return 'build_project_team';
  if ((complexity === 'complex' || complexity === 'large_project') && matchingSkillCount > 0) return 'pair_with_lead';
  if ((complexity === 'simple' || complexity === 'standard') && (technicianDepth === 'lead' || technicianDepth === 'advanced')) return 'reserve_for_better_fit';
  return 'solo_dispatch';
}

function sameMetro(a: string, b: string): boolean {
  return a.trim().toLowerCase() === b.trim().toLowerCase();
}
