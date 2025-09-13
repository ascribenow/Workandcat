declare namespace NodeJS {
  interface ProcessEnv {
    API_BASE: string;
    E2E_USER_COLDSTART: string;
    E2E_USER_ADAPTIVE: string;
    E2E_LAST_SESSION_ID: string;
    E2E_NEXT_SESSION_ID: string;
    E2E_BEARER?: string;
  }
}