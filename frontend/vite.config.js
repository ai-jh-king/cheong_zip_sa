import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// 산출물: frontend/dist/ (FastAPI WEB_DIR 를 여기로 가리켜 서빙하거나 정적 호스팅).
// 환경변수 VITE_API_BASE 미설정 시 API="" → 같은 출처 상대경로(현재 동작과 동일).
export default defineConfig({
  plugins: [react()],
  build: {
    outDir: 'dist',
    sourcemap: false,
    chunkSizeWarningLimit: 1500,
    rollupOptions: {
      output: {
        // React 벤더를 별도 청크로 → 앱 코드 변경 시에도 React 청크는 캐시 유지(immutable 캐시와 결합).
        manualChunks: { react: ['react', 'react-dom'] },
      },
    },
  },
});
