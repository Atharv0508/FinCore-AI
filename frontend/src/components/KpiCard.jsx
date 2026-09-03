const TONES = {
  neutral: 'border-l-slate-600',
  indigo: 'border-l-indigo-400',
  emerald: 'border-l-emerald-400',
  amber: 'border-l-amber-400',
  rose: 'border-l-rose-400',
  cyan: 'border-l-cyan-400',
}

export default function KpiCard({ label, value, tone = 'neutral', hint }) {
  return (
    <article
      className={`rounded-xl bg-white/[0.03] border border-white/10 border-l-4 ${TONES[tone] || TONES.neutral} p-4 backdrop-blur-sm hover:bg-white/[0.05] transition-colors`}
    >
      <small className="block text-xs font-medium text-slate-400">{label}</small>
      <b className="block mt-1.5 text-2xl font-bold text-white tabular-nums">{value}</b>
      {hint && <span className="block mt-1 text-xs text-slate-500">{hint}</span>}
    </article>
  )
}