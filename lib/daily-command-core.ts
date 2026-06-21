export type PriorityGrade = 'A' | 'B' | 'C' | 'D' | 'F';

export function scoreDailyCommandValue(pay: number, hours: number) {
  return hours > 0 ? Math.round((pay / hours) * 100) / 100 : 0;
}
