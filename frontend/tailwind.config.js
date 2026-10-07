/** GovInnovate Maharashtra — Stitch design tokens.
 *  Secretariat Navy primary, Ashoka Gold secondary, Evidence Emerald tertiary.
 *  Level-1 soft geometry (2px radius, 8px outer), low-contrast borders, no pills. */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      colors: {
        primary: '#0F2942',
        'primary-hover': '#0A1C2E',
        'primary-soft': '#EBF1FF',
        gold: '#D69E2E',
        'gold-soft': '#FDF3DC',
        emerald: '#276749',
        'emerald-soft': '#E6F4EA',
        crimson: '#9B2C2C',
        'crimson-soft': '#FED7D7',
        azure: '#2B6CB0',
        'azure-soft': '#EBF8FF',
        canvas: '#F7FAFC',
        surface: '#FFFFFF',
        'surface-2': '#EDF2F7',
        line: '#CBD5E0',
        hairline: '#E2E8F0',
        ink: '#1A202C',
        'ink-2': '#4A5568',
      },
      fontFamily: {
        sans: ['"Public Sans"', 'system-ui', 'sans-serif'],
        mono: ['"JetBrains Mono"', 'monospace'],
      },
      fontSize: {
        'display-lg': ['40px', { lineHeight: '48px', letterSpacing: '-0.02em', fontWeight: '700' }],
        'headline-lg': ['28px', { lineHeight: '36px', letterSpacing: '-0.01em', fontWeight: '700' }],
        'headline-sm': ['18px', { lineHeight: '26px', fontWeight: '600' }],
        'title-md': ['16px', { lineHeight: '24px', fontWeight: '600' }],
        'label-lg': ['14px', { lineHeight: '20px', fontWeight: '600' }],
        'label-sm': ['11px', { lineHeight: '14px', letterSpacing: '0.04em', fontWeight: '700' }],
      },
      borderRadius: {
        DEFAULT: '2px',
        md: '4px',
        lg: '8px',
      },
      boxShadow: {
        card: '0 1px 3px 0 rgba(15,41,66,0.05), 0 1px 2px 0 rgba(15,41,66,0.03)',
        overlay: '0 10px 15px -3px rgba(15,41,66,0.12), 0 4px 6px -2px rgba(15,41,66,0.05)',
      },
      minHeight: {
        22: '22px',
      },
    },
  },
  plugins: [],
};
