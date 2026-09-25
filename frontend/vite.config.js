import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// Vite dev server on http://localhost:5173 (must be listed in the backend CORS_ORIGINS).
export default defineConfig({
  plugins: [react()],
  server: { port: 5173 },
  preview: { port: 4173 },
});
