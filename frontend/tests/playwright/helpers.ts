import crypto from 'node:crypto';
import { APIRequestContext, expect } from '@playwright/test';

export const newIdemKey = () => crypto.randomUUID();

export function hashPack(pack: any[]): string {
  const minimal = pack.map(p => [p.item_id, p.bucket]);
  return crypto.createHash('sha1').update(JSON.stringify(minimal)).digest('hex');
}

export function countBands(pack: any[]) {
  const counts = { Easy: 0, Medium: 0, Hard: 0 };
  for (const p of pack) counts[p.bucket as 'Easy'|'Medium'|'Hard']++;
  return counts;
}

export function countPYQ(pack: any[]) {
  let pyq10 = 0, pyq15 = 0;
  for (const p of pack) {
    const s = Number(p?.why?.pyq_frequency_score ?? 0);
    if (s === 1.0) pyq10++;
    if (s === 1.5) pyq15++;
  }
  return { pyq10, pyq15 };
}

export function distinctPairs(pack: any[]) {
  return new Set(pack.map(p => p?.why?.pair)).size;
}

export async function planNext(
  request: APIRequestContext,
  user_id: string,
  last_session_id: string,
  next_session_id: string,
  idemKey?: string
) {
  // Use different auth tokens for different users
  const token = user_id === 'U_COLD_01' ? 
    'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJVX0NPTERfMDEiLCJleHAiOjE3NTc5Njg0MDd9.qTb2VuSk6DBnDZTNGejwbz0oOXg8d-jdJNyyu2xsEYU' :
    'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJVX0FEQVBUXzAxIiwiZXhwIjoxNzU3OTY4MjcwfQ.px3DsPhUIZ9JsIynQcT5IBG565M6V_Z8bq424sS1EDQ';
  
  const res = await request.post('/api/adapt/plan-next', {
    headers: { 
      'Idempotency-Key': idemKey ?? newIdemKey(),
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json'
    },
    data: { user_id, last_session_id, next_session_id }
  });
  const body = await res.json();
  return { res, body };
}

export async function getPack(request: APIRequestContext, user_id: string, session_id: string) {
  // Use different auth tokens for different users
  const token = user_id === 'U_COLD_01' ? 
    'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJVX0NPTERfMDEiLCJleHAiOjE3NTc5Njg0MDd9.qTb2VuSk6DBnDZTNGejwbz0oOXg8d-jdJNyyu2xsEYU' :
    'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJVX0FEQVBUXzAxIiwiZXhwIjoxNzU3OTY4MjcwfQ.px3DsPhUIZ9JsIynQcT5IBG565M6V_Z8bq424sS1EDQ';
    
  const res = await request.get('/api/adapt/pack', { 
    params: { user_id, session_id },
    headers: {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json'
    }
  });
  const body = await res.json();
  return { res, body };
}

export async function markServed(request: APIRequestContext, user_id: string, session_id: string) {
  // Use different auth tokens for different users
  const token = user_id === 'U_COLD_01' ? 
    'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJVX0NPTERfMDEiLCJleHAiOjE3NTc5Njg0MDd9.qTb2VuSk6DBnDZTNGejwbz0oOXg8d-jdJNyyu2xsEYU' :
    'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJVX0FEQVBUXzAxIiwiZXhwIjoxNzU3OTY4MjcwfQ.px3DsPhUIZ9JsIynQcT5IBG565M6V_Z8bq424sS1EDQ';
    
  const res = await request.post('/api/adapt/mark-served', { 
    data: { user_id, session_id },
    headers: {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json'
    }
  });
  return res;
}

export function assertHardConstraints(pack: any[]) {
  const bands = countBands(pack);
  const { pyq10, pyq15 } = countPYQ(pack);
  expect(pack).toHaveLength(12);
  expect(bands).toEqual({ Easy: 3, Medium: 6, Hard: 3 });
  expect(pyq10).toBeGreaterThanOrEqual(2);
  expect(pyq15).toBeGreaterThanOrEqual(2);
}

export function assertLadder(resBody: any) {
  const relaxed = resBody?.constraint_report?.relaxed ?? [];
  // Only coverage/readiness may relax; band/PYQ must never relax
  const forbidden = relaxed.filter((r: any) =>
    /band_shape|pyq_1\.0|pyq_1\.5/i.test(String(r?.name ?? ''))
  );
  expect(forbidden).toHaveLength(0);
}

export function metaFlagsPresent(resBody: any) {
  const meta = resBody?.constraint_report?.meta ?? {};
  // Both keys should exist (boolean)
  expect(meta).toHaveProperty('pool_expanded');
  expect(meta).toHaveProperty('retry_used');
}