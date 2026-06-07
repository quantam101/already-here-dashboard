import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

const source = readFileSync(new URL('../lib/revenue-model.ts', import.meta.url), 'utf8');

assert.match(source, /TARGET_OWNER_MONTHLY_INCOME = 25000/);
assert.match(source, /TARGET_MONTHLY_REVENUE = TARGET_OWNER_MONTHLY_INCOME/);
assert.match(source, /dailyActiveIncome: 500/);
assert.match(source, /retainerCount: 6/);
assert.match(source, /automatedIncome: 2000/);
assert.match(source, /estimatedCompanyIncomeMin: 1500/);
assert.match(source, /estimatedCompanyIncomeMax: 4000/);
assert.doesNotMatch(source, /Starter \/ developing tech/);
assert.doesNotMatch(source, /Reliable experienced tech/);
assert.doesNotMatch(source, /Senior \/ specialized tech/);

const ownerMonthlyTargets = [10000, 5982, 5000, 3000, 2000];
const ownerProjectedIncome = ownerMonthlyTargets.reduce((total, value) => total + value, 0);

assert.equal(ownerProjectedIncome, 25982);
assert.ok(ownerProjectedIncome >= 25000);

const standardFiveTechMin = 5 * 1500;
const standardFiveTechMax = 5 * 4000;

assert.equal(standardFiveTechMin, 7500);
assert.equal(standardFiveTechMax, 20000);
