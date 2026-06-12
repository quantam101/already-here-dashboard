import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

const engineSource = readFileSync(new URL('../lib/asi-engine.ts', import.meta.url), 'utf8');
const panelSource = readFileSync(new URL('../components/ASIDistillationPanel.tsx', import.meta.url), 'utf8');
const routeSource = readFileSync(new URL('../app/api/asi/score/route.ts', import.meta.url), 'utf8');

assert.match(engineSource, /minimumDailyFieldRevenue:\s*500/);
assert.match(engineSource, /approvalRequired:\s*true/);
assert.match(engineSource, /scoreASILead/);
assert.match(engineSource, /project_management/);
assert.match(engineSource, /retainer_coverage/);
assert.match(panelSource, /Distillation Engine Command Layer/);
assert.match(panelSource, /approval-gated action drafts/);
assert.match(routeSource, /approvalRequired:\s*true/);
assert.doesNotMatch(engineSource, /API_KEY\s*=/i);
assert.doesNotMatch(routeSource, /send_email|sendDraft|acceptWorkOrder|submitForm/i);
