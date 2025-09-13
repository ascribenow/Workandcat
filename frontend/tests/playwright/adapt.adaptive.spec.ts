import { test, expect } from '@playwright/test';
import { randomUUID } from 'crypto';
import { planNext, getPack, markServed, assertHardConstraints, assertLadder, metaFlagsPresent } from './helpers';

test.describe('Adaptive flow (with history)', () => {
  test('plans next session honoring hard constraints; ladder only relaxes coverage/readiness', async ({ request }) => {
    const user = process.env.E2E_USER_ADAPTIVE!;
    const lastSession = process.env.E2E_LAST_SESSION_ID!;
    const nextSession = randomUUID(); // Generate unique session ID

    // Plan next session for adaptive user (with session history)
    const { res: planRes, body: planBody } = await planNext(request, user, lastSession, nextSession);
    expect(planRes.ok()).toBeTruthy();
    metaFlagsPresent(planBody);
    
    // Validate relaxation ladder: only coverage/readiness can relax, never band/PYQ
    assertLadder(planBody);

    // Get the planned pack
    const { body: packBody } = await getPack(request, user, nextSession);
    
    // Validate hard constraints (12 questions, 3-6-3 distribution, PYQ minima) 
    assertHardConstraints(packBody.pack);

    // Structural readiness presence & pair scoping fields exist
    for (const p of packBody.pack) {
      expect(p.why).toHaveProperty('pair');
      // Readiness may be omitted only in cold-start; here we expect it present or relaxed in report
      expect(['Weak','Moderate','Strong', undefined]).toContain(p.why.readiness);
    }

    // Mark pack as served to complete the flow
    const served = await markServed(request, user, nextSession);
    expect(served.ok()).toBeTruthy();
  });
});