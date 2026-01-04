import { sveltekit } from '@sveltejs/kit/vite';
import tailwindcss from '@tailwindcss/vite';
import { defineConfig } from 'vite';

export default defineConfig({
	plugins: [tailwindcss(), sveltekit()],
	server: {
		proxy: {
			// Proxy API calls to the FastAPI backend
			'/api': {
				target: 'http://localhost:8000',
				changeOrigin: true
			}
		}
	}
});
