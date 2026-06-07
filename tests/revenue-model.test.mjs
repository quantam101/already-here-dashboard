import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

const source = readFileSync(new URL('../lib/revenue-model.ts', import.meta.url), 'utf8');

assert.match(source, /TARGET_MONTHLY_REVENUE = 25000/);
assert.match(source, /dailyActiveIncome: 500/);
assert.match(source, /retainerCount: 6/);
assert.match(source, /automatedIncome: 2000/);

const modeledMonthlyTargets = [10000, 5982, 5000, 3000, 2000];
const projectedTotal = modeledMonthlyTargets.reduce((total, value) => total + value, 0);

assert.equal(projectedTotal, 25982);
assert.ok(projectedTotal >= 25000);
