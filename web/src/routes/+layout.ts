// Disable SSR for SPA mode - all rendering happens client-side
// This fixes direct URL navigation issues (e.g., /login, /notes)
export const ssr = false;

// Disable prerendering
export const prerender = false;
