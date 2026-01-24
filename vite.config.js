import { defineConfig } from 'vite';
import { resolve } from 'path';

export default defineConfig({
  build: {
    rollupOptions: {
      input: {
        main: resolve(__dirname, 'index.html'),
        dashboard: resolve(__dirname, 'dashboard.html'),
        contact: resolve(__dirname, 'contact.html'),
        work: resolve(__dirname, 'work.html'),
        'spring-mass-damper': resolve(__dirname, 'spring-mass-damper.html'),
        'bernoulli-wing': resolve(__dirname, 'bernoulli-wing.html'),
        'stock-dashboard': resolve(__dirname, 'stock-dashboard.html'),
      },
    },
  },
});
