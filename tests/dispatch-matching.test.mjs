import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

const matchingSource = readFileSync(new URL('../lib/matching.ts', import.meta.url), 'utf8');
const typesSource = readFileSync(new URL('../lib/types.ts', import.meta.url), 'utf8');
const sampleSource = readFileSync(new URL('../lib/sample-data.ts', import.meta.url), 'utf8');

assert.match(typesSource, /SkillDepth = 'basic' \| 'intermediate' \| 'advanced' \| 'lead'/);
assert.match(typesSource, /JobComplexity = 'simple' \| 'standard' \| 'complex' \| 'large_project'/);
assert.match(typesSource, /DispatchRole = 'helper' \| 'field_tech' \| 'specialist' \| 'project_lead'/);
assert.match(typesSource, /TeamBuildAction = 'solo_dispatch' \| 'pair_with_lead' \| 'build_project_team' \| 'reserve_for_better_fit'/);

assert.match(matchingSource, /overqualified for scope; preserve senior capacity/);
assert.match(matchingSource, /right-sized skill depth for scope/);
assert.match(matchingSource, /lead eligible for project coordination/);
assert.match(matchingSource, /fit for multi-state project lead role/);
assert.match(matchingSource, /buildTeamRecommendation/);
assert.match(matchingSource, /reserve_for_better_fit/);
assert.match(matchingSource, /build_project_team/);

assert.match(sampleSource, /skillDepth: 'lead'/);
assert.match(sampleSource, /multiStateLeadEligible: true/);
assert.match(sampleSource, /mentorshipEligible: true/);
assert.match(sampleSource, /complexity: 'large_project'/);
assert.match(sampleSource, /requiresLead: true/);
assert.match(sampleSource, /multiStateProject: true/);
