import { test, expect } from '@playwright/test';
import { randomUUID } from 'crypto';
import { newIdemKey } from './helpers';

test('concurrency guard: only one planning job per user at a time', async ({ request }) => {
  const user = process.env.E2E_USER_ADAPTIVE!;
  const lastSession = process.env.E2E_LAST_SESSION_ID!;
  const nextSession = randomUUID() + '_CONC'; // Unique session for concurrency test

  // Fire two plan-next calls concurrently WITHOUT the same idempotency key
  const p1 = request.post('/api/adapt/plan-next', {
    headers: { 'Idempotency-Key': newIdemKey() },
    data: { user_id: user, last_session_id: lastSession, next_session_id: nextSession }
  });
  const p2 = request.post('/api/adapt/plan-next', {
    headers: { 'Idempotency-Key': newIdemKey() },
    data: { user_id: user, last_session_id: lastSession, next_session_id: nextSession }
  });

  const [r1, r2] = await Promise.all([p1, p2]);
  const okCount = Number(r1.ok()) + Number(r2.ok());
  
  // One should succeed, one should fail due to advisory lock
  expect(okCount).toBe(1); 
  
  // The loser should be 409 or 502 depending on controller implementation
  const loser = r1.ok() ? r2 : r1;
  expect([409, 502]).toContain(loser.status());
});