import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  server: {
    port: 3000,
    host: true, // Enables access via http://localhost:3000, http://assetra.localhost:3000, and local network IP
    open: true
  },
  preview: {
    port: 3000,
    host: true
  }
});
