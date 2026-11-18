import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  test: {
    environment: 'jsdom',
    globals: true,
  },
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true
      },
      '/simulate': {
        target: 'http://localhost:8000',
        changeOrigin: true
      },
      '/network': {
        target: 'http://localhost:8000',
        changeOrigin: true
      },
      '/localize': {
        target: 'http://localhost:8000',
        changeOrigin: true
      },
      '/incidents': {
        target: 'http://localhost:8000',
        changeOrigin: true
      },
      '/weather': {
        target: 'http://localhost:8000',
        changeOrigin: true
      },
      '/assets': {
        target: 'http://localhost:8000',
        changeOrigin: true
      },
      '/feeders': {
        target: 'http://localhost:8000',
        changeOrigin: true
      },
      '/dashboard': {
        target: 'http://localhost:8000',
        changeOrigin: true
      },
      '/model': {
        target: 'http://localhost:8000',
        changeOrigin: true
      },
      '/ingest': {
        target: 'http://localhost:8000',
        changeOrigin: true
      }
    }
  }
})
