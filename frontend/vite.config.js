import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import { reticle } from '@reticlehq/vite-plugin'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react(), reticle()],
  server: {
    proxy: {
      '/api': {
        target: 'https://apextrade-core-trade-ai-backend.hf.space',
        changeOrigin: true,
      },
      '/ws': {
        target: 'wss://apextrade-core-trade-ai-backend.hf.space',
        ws: true,
        changeOrigin: true,
      }
    }
  },
  build: {
    rollupOptions: {
      output: {
        manualChunks(id) {
          if (id.includes('node_modules')) {
            if (id.includes('lightweight-charts')) {
              return 'lightweight-charts';
            }
            return 'vendor';
          }
        }
      }
    }
  }
})
