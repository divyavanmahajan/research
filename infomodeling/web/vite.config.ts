import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/model': 'http://localhost:8000',
      '/generate': 'http://localhost:8000',
      '/seed': 'http://localhost:8000',
    }
  }
})
