import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    watch: {
      usePolling: true, // Critical for Docker on Windows/Mac to catch file changes
    },
    host: true, // This enables 0.0.0.0 binding (accessible outside container)
    strictPort: true,
    port: 3000, // Matches your docker-compose mapping
  }
})