import type { Config } from 'tailwindcss';

export default {
  content: [
    './src/**/*.{html,js,svelte,ts}',
    './src/routes/**/*.{svelte,ts}',
    './src/lib/**/*.{svelte,ts}'
  ],
  theme: {
    extend: {
      fontSize: {
        // Balanced sizes for readability
        'xs': ['0.75rem', { lineHeight: '1.4' }],     // 12px
        'sm': ['0.875rem', { lineHeight: '1.4' }],    // 14px
        'base': ['1rem', { lineHeight: '1.5' }],      // 16px
        'lg': ['1.125rem', { lineHeight: '1.5' }],    // 18px
        'xl': ['1.25rem', { lineHeight: '1.4' }],     // 20px
        '2xl': ['1.5rem', { lineHeight: '1.3' }],     // 24px
        '3xl': ['1.875rem', { lineHeight: '1.2' }],   // 30px
        '4xl': ['2.25rem', { lineHeight: '1.1' }],    // 36px
      },
      maxWidth: {
        '8xl': '88rem',  // 1408px for ultra-wide screens
        '9xl': '96rem',  // 1536px
      }
    }
  }
} satisfies Config;
