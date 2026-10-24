import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// Keep both local servers on loopback and fail on a busy port instead of moving.
// Root npm scripts select apps/web as Vite's root, including its local dist/ output.
export default defineConfig(({ command, mode }) => {
  const preview = mode === 'identity-preview';
  if (preview && command !== 'serve')
    throw new Error('Synthetic preview cannot be built or deployed');
  return {
    plugins: [react()],
    server: {
      host: '127.0.0.1',
      port: 5173,
      strictPort: true,
      ...(preview
        ? {
            proxy: Object.fromEntries(
              [
                '/auth/microsoft',
                '/auth/temporary',
                '/auth/session',
                '/auth/csrf',
                '/me',
                '/__identity_preview__',
              ].map((path) => [path, { target: 'http://127.0.0.1:8001', changeOrigin: false }]),
            ),
          }
        : {}),
    },
    preview: {
      host: '127.0.0.1',
      port: 4173,
      strictPort: true,
    },
  };
});
