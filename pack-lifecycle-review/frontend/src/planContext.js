/**
 * Plan Context Storage Utility
 * Manages user plan selection context across authentication flow
 */

const PLAN_CONTEXT_KEY = 'twelvr_plan_context';
const CONTEXT_DURATION_MS = 15 * 60 * 1000; // 15 minutes

export const PLAN_TYPES = {
  FREE_TRIAL: 'free_trial',
  PRO_REGULAR: 'pro_regular',
  PRO_EXCLUSIVE: 'pro_exclusive'
};

export const PLAN_CONFIG = {
  [PLAN_TYPES.FREE_TRIAL]: {
    name: 'Free Trial',
    amount: 0,
    description: 'Perfect for testing the waters'
  },
  [PLAN_TYPES.PRO_REGULAR]: {
    name: 'Pro Regular',
    amount: 149500, // ₹1,495 in paise
    description: 'For long-term prep spaced across months'
  },
  [PLAN_TYPES.PRO_EXCLUSIVE]: {
    name: 'Pro Exclusive',
    amount: 256500, // ₹2,565 in paise
    description: 'Access till Dec 31, 2025 with Ask Twelvr'
  }
};

/**
 * Store plan selection context with timestamp
 * @param {string} planType - The selected plan type
 * @param {string} source - Where the selection came from (landing_page, pricing, etc.)
 */
export const storePlanContext = (planType, source = 'unknown') => {
  const context = {
    planType,
    source,
    timestamp: Date.now(),
    expiresAt: Date.now() + CONTEXT_DURATION_MS
  };
  
  try {
    sessionStorage.setItem(PLAN_CONTEXT_KEY, JSON.stringify(context));
    console.log(`📋 Plan context stored: ${planType} from ${source}`);
  } catch (error) {
    console.error('Failed to store plan context:', error);
  }
};

/**
 * Retrieve plan selection context if still valid
 * @returns {Object|null} Plan context object or null if expired/not found
 */
export const getPlanContext = () => {
  try {
    const stored = sessionStorage.getItem(PLAN_CONTEXT_KEY);
    if (!stored) return null;
    
    const context = JSON.parse(stored);
    const now = Date.now();
    
    // Check if context has expired
    if (now > context.expiresAt) {
      clearPlanContext();
      console.log('📋 Plan context expired, cleared');
      return null;
    }
    
    console.log(`📋 Plan context retrieved: ${context.planType} from ${context.source}`);
    return context;
  } catch (error) {
    console.error('Failed to retrieve plan context:', error);
    clearPlanContext();
    return null;
  }
};

/**
 * Clear plan selection context
 */
export const clearPlanContext = () => {
  try {
    sessionStorage.removeItem(PLAN_CONTEXT_KEY);
    console.log('📋 Plan context cleared');
  } catch (error) {
    console.error('Failed to clear plan context:', error);
  }
};

/**
 * Check if there's a valid plan context
 * @returns {boolean} True if valid context exists
 */
export const hasPlanContext = () => {
  const context = getPlanContext();
  return context !== null;
};

/**
 * Get remaining time for plan context in minutes
 * @returns {number} Minutes remaining or 0 if expired/not found
 */
export const getPlanContextTimeRemaining = () => {
  const context = getPlanContext();
  if (!context) return 0;
  
  const remaining = context.expiresAt - Date.now();
  return Math.max(0, Math.floor(remaining / (60 * 1000))); // Convert to minutes
};

/**
 * Update plan context without changing timestamp (extend validity)
 * @param {Object} updates - Updates to apply to context
 */
export const updatePlanContext = (updates) => {
  const context = getPlanContext();
  if (!context) return false;
  
  const updatedContext = {
    ...context,
    ...updates,
    expiresAt: Date.now() + CONTEXT_DURATION_MS // Reset expiry
  };
  
  try {
    sessionStorage.setItem(PLAN_CONTEXT_KEY, JSON.stringify(updatedContext));
    console.log(`📋 Plan context updated:`, updates);
    return true;
  } catch (error) {
    console.error('Failed to update plan context:', error);
    return false;
  }
};