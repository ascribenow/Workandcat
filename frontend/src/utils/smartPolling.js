/**
 * Smart Polling Utility for Coverage System
 * Handles exponential backoff, server hints, and comprehensive error states
 * Enhanced for 404 race condition handling
 */

export class SmartPoller {
  constructor(api, endpoint, params, options = {}) {
    this.api = api;
    this.endpoint = endpoint;
    this.params = params;
    this.budgetMs = options.budgetMs || 75000; // 75s budget (60s backend + 15s buffer)
    this.baseDelay = options.baseDelay || 1000;
    this.maxDelay = options.maxDelay || 8000;
    this.timeout = options.timeout || 8000;
    this.treat404AsPreparingMs = options.treat404AsPreparingMs || 65000; // NEW: 404 grace window
  }

  // Add jitter to prevent thundering herd
  addJitter(ms) {
    return Math.round(ms * (0.85 + Math.random() * 0.3));
  }

  async poll() {
    let delay = this.baseDelay;
    const start = Date.now();
    let attempt = 0;

    while (Date.now() - start < this.budgetMs) {
      attempt++;
      const elapsed = Date.now() - start;
      
      try {
        const response = await this.api.get(this.endpoint, {
          params: this.params,
          timeout: this.timeout,
          validateStatus: () => true // Don't throw on non-2xx status
        });

        // Success - return data
        if (response.status === 200) {
          console.log(`✅ Poll success after ${attempt} attempts (${elapsed}ms)`);
          return { 
            success: true, 
            data: response.data, 
            attempts: attempt,
            elapsed_ms: elapsed
          };
        }

        // Still processing - respect server hint or use backoff
        if (response.status === 202) {
          const serverHint = response.data?.poll_after_ms || delay;
          const waitTime = this.addJitter(serverHint);
          console.log(`⏳ Poll ${attempt}: ${response.data?.message || 'Processing...'} (waiting ${waitTime}ms)`);
          
          await new Promise(r => setTimeout(r, waitTime));
          delay = Math.min(delay * 1.5, this.maxDelay); // Gentle exponential backoff
          continue;
        }

        // NEW: Handle early 404 as "still preparing" within grace window
        if (response.status === 404 && elapsed < this.treat404AsPreparingMs) {
          const waitTime = this.addJitter(delay);
          console.log(`🕐 Poll ${attempt}: Early 404 (${elapsed}ms < ${this.treat404AsPreparingMs}ms), treating as preparing. Waiting ${waitTime}ms`);
          
          await new Promise(r => setTimeout(r, waitTime));
          delay = Math.min(delay * 1.5, this.maxDelay);
          continue;
        }

        // Rate limited - back off aggressively  
        if (response.status === 429 || response.status === 503) {
          const backoffDelay = Math.min(delay * 2, this.maxDelay);
          const waitTime = this.addJitter(backoffDelay);
          console.log(`🚦 Poll ${attempt}: Rate limited (${response.status}), backing off ${waitTime}ms`);
          
          await new Promise(r => setTimeout(r, waitTime));
          delay = backoffDelay;
          continue;
        }

        // Server error - return for user decision
        if (response.status === 500) {
          const errorData = response.data;
          return {
            success: false,
            error: errorData?.error || 'Server error during pack preparation',
            retryAvailable: errorData?.retry_available ?? true,
            attempts: attempt,
            elapsed_ms: elapsed,
            status_code: 500
          };
        }

        // Other status (including 404 after grace period) - treat as error
        console.log(`❌ Poll ${attempt}: Unexpected response ${response.status} after ${elapsed}ms`);
        return {
          success: false,
          error: `Pack retrieval failed with status ${response.status}`,
          retryAvailable: response.status !== 403, // Don't retry auth errors
          attempts: attempt,
          elapsed_ms: elapsed,
          status_code: response.status
        };

      } catch (error) {
        // Network timeout - continue polling (CRITICAL FIX: Don't fail on timeout)
        if (error.code === 'ECONNABORTED' || error.message.includes('timeout')) {
          const waitTime = this.addJitter(delay);
          console.log(`⏳ Poll ${attempt}: Network timeout (${this.timeout}ms), continuing... (${waitTime}ms delay)`);
          await new Promise(r => setTimeout(r, waitTime));
          delay = Math.min(delay * 1.5, this.maxDelay);
          continue;
        }
        
        // Other network errors - continue with backoff
        console.error(`🌐 Poll ${attempt}: Network error:`, error.message);
        const waitTime = this.addJitter(delay);
        await new Promise(r => setTimeout(r, waitTime));
        delay = Math.min(delay * 1.5, this.maxDelay);
        continue;
      }
    }

    // Budget exceeded
    console.log(`⏰ Polling budget exhausted after ${attempt} attempts (${Date.now() - start}ms)`);
    return {
      success: false,
      error: 'Session preparation timeout - please try again',
      retryAvailable: true,
      attempts: attempt,
      elapsed_ms: Date.now() - start,
      error_type: 'timeout'
    };
  }
}

/**
 * Enhanced session planning with backend session ID authority
 * Includes retry logic for plan-next timeouts (ECONNABORTED)
 */
export async function planSessionWithPolling({
  api,
  userId,
  lastSessionId = null,
  idempotencyKey,
  planTimeout = 8000,
  maxPlanRetries = 1,  // NEW: Retry plan-next once on timeout
  ...pollOptions
}) {
  console.log(`🚀 Planning session with idempotency key: ${idempotencyKey}`);
  
  for (let attempt = 0; attempt <= maxPlanRetries; attempt++) {
    try {
      const isRetry = attempt > 0;
      if (isRetry) {
        console.log(`🔄 Retrying plan-next (attempt ${attempt + 1}/${maxPlanRetries + 1})`);
      }
      
      // Step 1: Trigger session planning (with retry support)
      const planResp = await api.post('/adapt/plan-next', {
        user_id: userId,
        last_session_id: lastSessionId,
        next_session_id: null // Let backend generate canonical ID
      }, {
        headers: { 'Idempotency-Key': idempotencyKey }, // Same key for retries (safe)
        timeout: planTimeout
      });

      if (planResp.status !== 202) {
        throw new Error(`Unexpected plan response: ${planResp.status}`);
      }

      const { session_id: canonicalSessionId } = planResp.data;
      
      if (!canonicalSessionId) {
        throw new Error('Backend did not return session_id');
      }

      console.log(`✅ Session planning ${isRetry ? 'retry ' : ''}succeeded, canonical ID: ${canonicalSessionId.substring(0, 8)}...`);

      // Step 2: Poll for pack using backend's canonical session ID
      const poller = new SmartPoller(
        api, 
        '/adapt/pack', 
        { user_id: userId, session_id: canonicalSessionId },
        pollOptions
      );
      
      const pollResult = await poller.poll();

      if (pollResult.success) {
        return {
          ok: true,
          sessionId: canonicalSessionId,
          pack: pollResult.data.pack,
          meta: pollResult.data
        };
      } else {
        return {
          ok: false,
          sessionId: canonicalSessionId,
          error: pollResult.error,
          retryAvailable: pollResult.retryAvailable
        };
      }

    } catch (planError) {
      const isTimeout = planError.code === 'ECONNABORTED' || planError.message.includes('timeout');
      
      if (isTimeout && attempt < maxPlanRetries) {
        console.log(`⏰ Plan-next timeout (${planError.message}), will retry with same idempotency key...`);
        // Wait before retry (jitter)
        await new Promise(r => setTimeout(r, 1000 + Math.random() * 1000));
        continue; // Retry the planning step
      }
      
      // Final failure or non-timeout error
      console.log(`💥 Planning failed (attempt ${attempt + 1}):`, planError);
      const error = new Error(`Failed to start session: ${planError.message}`);
      return { ok: false, error, retryAvailable: isTimeout };
    }
  }
}

export default SmartPoller;