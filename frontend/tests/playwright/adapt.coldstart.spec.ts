import { test, expect } from '@playwright/test';
import { randomUUID } from 'crypto';
import { getPack, planNext, markServed, assertHardConstraints, distinctPairs, metaFlagsPresent } from './helpers';

test.describe('Cold-start flow', () => {
  test('plans and serves a cold-start pack with ≥5 distinct pairs', async ({ request }) => {
    const user = process.env.E2E_USER_COLDSTART!;
    const nextSession = randomUUID(); // Generate unique session ID

    // Plan next session for cold-start user (using last_session_id: "S0" for cold start)
    const { res: planRes, body: planBody } = await planNext(request, user, 'S0', nextSession);
    expect(planRes.ok()).toBeTruthy();
    metaFlagsPresent(planBody);

    // Get the planned pack
    const { res: packRes, body: packBody } = await getPack(request, user, nextSession);
    expect(packRes.ok()).toBeTruthy();
    expect(packBody.status).toBe('planned');
    
    // Validate hard constraints (12 questions, 3-6-3 distribution, PYQ minima)
    assertHardConstraints(packBody.pack);

    // Cold-start specific validation: ≥5 distinct pairs for diversity
    const pairs = distinctPairs(packBody.pack);
    expect(pairs).toBeGreaterThanOrEqual(5);

    // Mark pack as served to complete the flow
    const served = await markServed(request, user, nextSession);
    expect(served.ok()).toBeTruthy();
  });
});