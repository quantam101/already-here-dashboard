import type { MatchResult, Technician, WorkOrder } from './types';

export function rankTechnicians(workOrder: WorkOrder, technicians: Technician[]): MatchResult[] {
  return technicians
    .map((technician) => scoreTechnician(workOrder, technician))
    .filter((result) => result.score > 0)
    .sort((a, b) => b.score - a.score);
}

function scoreTechnician(workOrder: WorkOrder, technician: Technician): MatchResult {
  let score = 0;
  const reasons: string[] = [];
  const riskFlags: string[] = [];

  const matchingSkills = workOrder.requiredSkills.filter((skill) => technician.skills.includes(skill));
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

  return { technician, score: Math.max(score, 0), reasons, riskFlags };
}

function sameMetro(a: string, b: string): boolean {
  return a.trim().toLowerCase() === b.trim().toLowerCase();
}
