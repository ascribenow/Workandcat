/**
 * Smart Polling Utility for Coverage System
 * Handles exponential backoff, server hints, and comprehensive error states
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
  }

  async poll() {
    let delay = this.baseDelay;
    const start = Date.now();
    let attempt = 0;

    while (Date.now() - start < this.budgetMs) {
      attempt++;
      
      try {
        const response = await this.api.get(this.endpoint, {
          params: this.params,
          timeout: this.timeout
        });

        // Success - return data
        if (response.status === 200) {
          return { 
            success: true, 
            data: response.data, 
            attempts: attempt,
            elapsed_ms: Date.now() - start
          };
        }

        // Still processing - respect server hint or use backoff
        if (response.status === 202) {
          const serverHint = response.data?.poll_after_ms || delay;
          console.log(`⏳ Poll ${attempt}: ${response.data?.message || 'Processing...'} (waiting ${serverHint}ms)`);
          
          await new Promise(r => setTimeout(r, serverHint));
          delay = Math.min(delay * 1.5, this.maxDelay); // Gentle exponential backoff
          continue;
        }

        // Rate limited - back off aggressively  
        if (response.status === 429 || response.status === 503) {
          const backoffDelay = Math.min(delay * 2, this.maxDelay);
          console.log(`⚠️ Poll ${attempt}: Rate limited, backing off ${backoffDelay}ms`);
          
          await new Promise(r => setTimeout(r, backoffDelay));
          delay = backoffDelay;
          continue;
        }

        // Server error - return for user decision
        if (response.status === 500) {
          const errorData = response.data;
          return {
            success: false,
            error: errorData?.error || 'Server error',
            retryAvailable: errorData?.retry_available ?? true,
            attempts: attempt,
            elapsed_ms: Date.now() - start,
            status_code: 500
          };
        }

        // Other status - treat as error
        return {
          success: false,
          error: `Unexpected response: ${response.status}`,
          retryAvailable: true,
          attempts: attempt,
          elapsed_ms: Date.now() - start,
          status_code: response.status
        };

      } catch (error) {
        // Network timeout - continue polling (expected behavior)
        if (error.code === 'ECONNABORTED' || error.message.includes('timeout')) {
          console.log(`⏳ Poll ${attempt}: Network timeout, continuing... (${delay}ms delay)`);
          await new Promise(r => setTimeout(r, delay));
          delay = Math.min(delay * 1.5, this.maxDelay);
          continue;
        }
        
        // Other network errors - return for user decision
        return {
          success: false,
          error: error.message,
          retryAvailable: true,
          attempts: attempt,
          elapsed_ms: Date.now() - start,
          error_type: 'network'
        };
      }
    }

    // Budget exceeded
    return {
      success: false,
      error: 'Preparation timeout after 75s',
      retryAvailable: true,
      attempts: attempt,
      elapsed_ms: Date.now() - start,
      error_type: 'timeout'
    };
  }
}

export default SmartPoller;