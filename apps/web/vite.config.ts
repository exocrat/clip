import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// Keep both local servers on loopback and fail on a busy port instead of moving.
// Root npm scripts select apps/web as Vite's root, including its local dist/ output.
export default defineConfig({
  plugins: [react()],
  server: {
    host: '127.0.0.1',
    port: 5173,
    strictPort: true,
    // Development only: keep browser calls same-origin and target the local API.
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8000',
        rewrite: (path) => path.replace(/^\/api/, ''),
      },
    },
  },
  preview: {
    host: '127.0.0.1',
    port: 4173,
    strictPort: true,
  },
});
