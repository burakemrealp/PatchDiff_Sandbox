import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import tailwindcss from '@tailwindcss/vite';

export default defineConfig({
  plugins: [react(), tailwindcss()],
  build: {
    rolldownOptions: {
      output: {
        codeSplitting: {
          groups: [
            {
              name: 'react-vendor',
              test: /[\\/]node_modules[\\/](react|react-dom|scheduler)[\\/]/,
            },
            {
              name: 'charts-vendor',
              test: /[\\/]node_modules[\\/](recharts|d3-|victory-vendor)[\\/]/,
            },
            {
              name: 'icons-vendor',
              test: /[\\/]node_modules[\\/]lucide-react[\\/]/,
            },
            {
              name: 'i18n-bundles',
              test: /[\\/]src[\\/]i18n[\\/]translations/,
            },
          ],
        },
      },
    },
  },
});
