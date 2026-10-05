// Single source of truth for the backend origin.
// Override at build time with VITE_API_URL (e.g. VITE_API_URL=https://api.example.com).
export const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';
