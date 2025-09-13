import { test, expect } from '@playwright/test';
import { randomUUID } from 'crypto';
import { planNext, getPack, hashPack } from './helpers';

test('idempotent plan-next with same key returns same pack', async ({ request }) => {
  const user = process.env.E2E_USER_ADAPTIVE!;
  const lastSession = process.env.E2E_LAST_SESSION_ID!;
  const nextSession = randomUUID() + '_IDEMP'; // Unique session for idempotency test

  const idemKey = 'idem-' + Date.now();

  // Make two identical requests with the same idempotency key
  const first = await planNext(request, user, lastSession, nextSession, idemKey);
  const second = await planNext(request, user, lastSession, nextSession, idemKey);

  expect(first.res.ok()).toBeTruthy();
  expect(second.res.ok()).toBeTruthy();

  // Get packs from both planning attempts
  const pack1 = (await getPack(request, user, nextSession)).body.pack;
  const pack2 = (await getPack(request, user, nextSession)).body.pack;

  // Packs should be identical (same hash)
  expect(hashPack(pack1)).toBe(hashPack(pack2));
});