import type { Config } from 'tailwindcss'

const config: Config = {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        // Paleta industrial oscura (mismo estilo que AuditBoard)
        surface: {
          DEFAULT: '#0a0a0f',
          50: '#12121a',
          100: '#1a1a26',
          200: '#222233',
          300: '#2a2a40',
        },
        accent: {
          DEFAULT: '#6366f1',  // indigo-500
          hover: '#4f46e5',
          light: '#818cf8',
        },
        success: '#22c55e',
        warning: '#f59e0b',
        danger: '#ef4444',
        info: '#3b82f6',
        // Status del pipeline de reuniones
        status: {
          uploaded:    '#94a3b8',
          queued:      '#f59e0b',
          processing:  '#3b82f6',
          transcribed: '#8b5cf6',
          analyzed:    '#22c55e',
          failed:      '#ef4444',
        },
        // Status de action items (Kanban)
        kanban: {
          pending:     '#94a3b8',
          in_progress: '#3b82f6',
          in_review:   '#f59e0b',
          completed:   '#22c55e',
          overdue:     '#ef4444',
          cancelled:   '#475569',
        },
        // Tipos de action items
        item_type: {
          action_item: '#6366f1',
          decision:    '#22c55e',
          commitment:  '#f59e0b',
          risk:        '#ef4444',
        },
      },
      fontFamily: {
        mono: ['JetBrains Mono', 'Fira Code', 'Consolas', 'monospace'],
        sans: ['Inter', 'system-ui', 'sans-serif'],
      },
      boxShadow: {
        card: '0 0 0 1px rgba(255,255,255,0.06), 0 4px 16px rgba(0,0,0,0.4)',
        glow: '0 0 20px rgba(99,102,241,0.3)',
      },
    },
  },
  plugins: [],
}

export default config
