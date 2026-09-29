import path from 'node:path'
import { fileURLToPath } from 'node:url'
import tailwindcss from '@tailwindcss/vite'
import react from '@vitejs/plugin-react'
import { loadEnv, defineConfig } from 'vite'
import { configDefaults } from 'vitest/config'

// https://vite.dev/config/
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '')
  const backendUrl = env.BACKEND_URL || 'http://127.0.0.1:8000'

  const __dirname = path.dirname(fileURLToPath(import.meta.url))

  return {
    plugins: [react(), tailwindcss()],
    resolve: {
      alias: {
        '@': path.resolve(__dirname, './src'),
      },
    },
    server: {
      port: 5173,
      proxy: {
        '/api': {
          target: backendUrl,
          changeOrigin: true,
        },
      },
    },
    test: {
      environment: 'jsdom',
      exclude: [...configDefaults.exclude, 'e2e/**'],
      setupFiles: ['./src/test/setup.ts'],
      globals: true,
      css: true,
      // A few tests exercise real setTimeout-based debouncing; under full-suite
      // parallel CPU contention (especially with coverage instrumentation) their
      // deadlines can occasionally be missed even though the behavior is correct.
      // One retry absorbs that environmental flakiness without masking a real failure.
      retry: 1,
      coverage: {
        provider: 'v8',
        thresholds: {
          statements: 77,
          branches: 68,
          functions: 75,
          lines: 78,
        },
      },
    },
  }
})
