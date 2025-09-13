import { FullConfig } from '@playwright/test';

export default async function globalSetup(config: FullConfig) {
  // Set JWT tokens for test users
  const jwt_secret = 'cat-prep-2025-secure-jwt-key-sumedhprabhu18';
  
  // Mock JWT encoding (simple base64 encoding for testing)
  function createToken(user_id: string): string {
    const header = Buffer.from(JSON.stringify({alg: "HS256", typ: "JWT"})).toString('base64url');
    const payload = Buffer.from(JSON.stringify({
      sub: user_id,
      exp: Math.floor(Date.now() / 1000) + (48 * 3600) // 48 hours
    })).toString('base64url');
    
    // For testing, we'll use a simplified signature (in production, use proper HMAC)
    const signature = Buffer.from(`test-signature-${user_id}`).toString('base64url');
    
    return `${header}.${payload}.${signature}`;
  }
  
  // Set environment variables for both test users
  process.env.E2E_BEARER_COLD = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJVX0NPTERfMDEiLCJleHAiOjE3NTc5Njg0MDd9.qTb2VuSk6DBnDZTNGejwbz0oOXg8d-jdJNyyu2xsEYU';
  process.env.E2E_BEARER_ADAPT = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJVX0FEQVBUXzAxIiwiZXhwIjoxNzU3OTY4MjcwfQ.px3DsPhUIZ9JsIynQcT5IBG565M6V_Z8bq424sS1EDQ';
}