import { test, expect } from '@playwright/test';
import { randomUUID } from 'crypto';
import { planNext, getPack, assertHardConstraints, assertLadder, metaFlagsPresent } from './helpers';

test('planner contract: hard constraints and meta flags are enforced', async ({ request }) => {
  const user = process.env.E2E_USER_ADAPTIVE!;
  const lastSession = process.env.E2E_LAST_SESSION_ID!;
  const nextSession = randomUUID() + '_CONTRACT'; // Unique session for contract test

  // Plan next session
  const { body: planBody } = await planNext(request, user, lastSession, nextSession);
  
  // Validate meta flags are present in constraint report
  metaFlagsPresent(planBody);
  
  // Validate relaxation ladder rules
  assertLadder(planBody);

  // Get the planned pack
  const { body: packBody } = await getPack(request, user, nextSession);
  
  // Validate hard constraints are enforced
  assertHardConstraints(packBody.pack);

  // Ensure "why" payload contains semantic_concepts and pyq_frequency_score for each question
  for (const p of packBody.pack) {
    expect(Array.isArray(p?.why?.semantic_concepts)).toBeTruthy();
    expect(typeof p?.why?.pyq_frequency_score).toBe('number');
  }
});