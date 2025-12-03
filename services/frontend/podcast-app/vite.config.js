import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 3000,
    open: true,
    // Add headers for WASM files
    headers: {
      'Cross-Origin-Embedder-Policy': 'require-corp',
      'Cross-Origin-Opener-Policy': 'same-origin'
    }
  },
  // Only exclude ONNX Runtime from pre-bundling
  // VAD packages need to be pre-bundled to convert CommonJS to ESM
  optimizeDeps: {
    exclude: ['onnxruntime-web']
  },
  // Handle WASM files correctly
  assetsInclude: ['**/*.wasm', '**/*.onnx']
})
