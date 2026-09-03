import { useEffect, useState } from 'react'
import {
  PieChart, Pie, Cell, Tooltip, ResponsiveContainer, Legend,
  BarChart, Bar, XAxis, YAxis, CartesianGrid,
} from 'recharts'
import Logo from '../components/Logo'
import KpiCard from '../components/KpiCard'
import { rupees, count } from '../lib/api'

const CLASS_COLORS = { Paid: '#34d399', Partial: '#fbbf24', Unpaid: '#fb7185', Exception: '#94a3b8' }
const SEVERITY_TONE = { low: 'text-emerald-300 bg-emerald-500/10', medium: 'text-amber-300 bg-amber-500/10', high: 'text-rose-300 bg-rose-500/10' }
const TOOLTIP_STYLE = { background: '#111116', border: '1px solid rgba(255,255,255,0.1)', borderRadius: 10, color: '#e2e8f0', fontSize: 12 }
const GRID_STROKE = 'rgba(255,255,255,0.06)'
const AXIS_TICK = { fontSize: 12, fill: '#94a3b8' }

function fmtDate(value) {
  return value ? new Date(value).toLocaleString('en-IN', { day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit' }) : '—'
}

function ProgressBar({ label, valuePct, tone = 'indigo', hint }) {
  const barColor = { indigo: 'bg-gradient-to-r from-indigo-500 to-fuchsia-500', emerald: 'bg-gradient-to-r from-emerald-500 to-teal-400', amber: 'bg-gradient-to-r from-amber-500 to-orange-400' }[tone]
  return (
    <div>
      <div className="flex items-center justify-between text-sm">
        <span className="font-medium text-slate-300">{label}</span>
        <span className="font-bold text-white tabular-nums">{valuePct}%</span>
      </div>
      <div className="mt-2 h-2.5 w-full rounded-full bg-white/[0.06] overflow-hidden">
        <div className={`h-full rounded-full ${barColor} transition-all`} style={{ width: `${Math.min(valuePct, 100)}%` }} />
      </div>
      {hint && <p className="mt-1 text-xs text-slate-500">{hint}</p>}
    </div>
  )
}

function Section({ title, subtitle, children, right }) {
  return (
    <div className="rounded-2xl bg-white/[0.03] border border-white/10 backdrop-blur-sm p-5">
      <div className="flex items-start justify-between mb-4">
        <div>
          <h2 className="text-sm font-bold text-white">{title}</h2>
          {subtitle && <p className="text-xs text-slate-500 mt-0.5">{subtitle}</p>}
        </div>
        {right}
      </div>
      {children}
    </div>
  )
}

export default function DashboardPage({ user, stats, notice, onSync, onConnect, onLogout, onSearch, onChat }) {
  const [tab, setTab] = useState('Overview')
  const [menu, setMenu] = useState(false)
  const [query, setQuery] = useState('')
  const [results, setResults] = useState([])
  const [selected, setSelected] = useState()
  const [answer, setAnswer] = useState('')
  const [pendingQuestion, setPendingQuestion] = useState(null)
  const [asking, setAsking] = useState(false)

  const counts = stats?.counts || {}
  const amounts = stats?.amounts || {}
  const recon = stats?.reconciliation || {}
  const risk = stats?.risk || {}
  const throughput = stats?.throughput || {}
  const classification = stats?.classification || {}
  const activity = stats?.activity || { invoices: [0, 0, 0], payments: [0, 0, 0] }
  const today = stats?.today || { invoices: [], payments: [] }
  const exceptions = stats?.exceptions || []
  const recent = stats?.recent || {}

  const classData = Object.entries(classification)
    .map(([name, value]) => ({ name, value }))
    .filter((d) => d.value > 0)

  const resolutionData = [
    { name: 'Auto-reconciled', value: recon.auto_reconciled || 0, fill: '#818cf8' },
    { name: 'AI-resolved', value: recon.ai_resolved || 0, fill: '#22d3ee' },
    { name: 'Unresolved', value: recon.unresolved_exceptions || 0, fill: '#fb7185' },
  ]

  const amountsData = [
    { name: 'Outstanding', value: (amounts.total_outstanding || 0) / 100, fill: '#fbbf24' },
    { name: 'Collected', value: (amounts.total_collected || 0) / 100, fill: '#34d399' },
    { name: 'Settled', value: (amounts.total_settled || 0) / 100, fill: '#818cf8' },
  ]

  const activityData = [
    { period: 'Today', Invoices: activity.invoices?.[0] || 0, Payments: activity.payments?.[0] || 0 },
    { period: 'This week', Invoices: activity.invoices?.[1] || 0, Payments: activity.payments?.[1] || 0 },
    { period: 'This month', Invoices: activity.invoices?.[2] || 0, Payments: activity.payments?.[2] || 0 },
  ]

  const todayLabel = new Date().toLocaleDateString('en-IN', { weekday: 'long', day: 'numeric', month: 'long' })

  async function search(e) {
    const value = e.target.value
    setQuery(value)
    setResults(value.length > 1 ? await onSearch(value) : [])
  }

  async function submitChat(e, forcedQuestion) {
    if (e) e.preventDefault()
    const q = forcedQuestion ?? query
    if (!q?.trim()) return
    setAsking(true)
    try {
      setAnswer(await onChat(q))
    } catch (error) {
      setAnswer(error.message)
    } finally {
      setAsking(false)
    }
  }

  function askAiAbout(promptText) {
    setSelected()
    setQuery(promptText)
    setTab('Chat')
    setPendingQuestion(promptText)
  }

  useEffect(() => {
    if (tab === 'Chat' && pendingQuestion) {
      submitChat(null, pendingQuestion)
      setPendingQuestion(null)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [tab, pendingQuestion])

  return (
    <main className="min-h-screen bg-[#0a0a0f] text-slate-100 pb-20 relative">
      {/* Ambient background, subtler than landing page */}
      <div
        className="pointer-events-none fixed inset-0 -z-10 opacity-40"
        style={{
          background:
            'radial-gradient(circle at 10% 0%, rgba(99,102,241,0.20), transparent 40%),' +
            'radial-gradient(circle at 90% 10%, rgba(217,70,239,0.15), transparent 40%)',
          filter: 'blur(60px)',
        }}
      />

      {/* Header */}
      <header className="sticky top-0 z-20 bg-[#0a0a0f]/80 backdrop-blur-xl border-b border-white/10">
        <div className="max-w-7xl mx-auto flex items-center justify-between px-6 h-[72px]">
          <Logo />
          <div className="relative">
            <button
              onClick={() => setMenu(!menu)}
              className="flex items-center gap-2 text-sm font-medium text-slate-300 hover:text-white"
            >
              {user.avatar_url && <img src={user.avatar_url} className="w-7 h-7 rounded-full" alt="" />}
              {user.email} <span className="text-slate-500">⌄</span>
            </button>
            {menu && (
              <div className="absolute right-0 top-10 w-52 rounded-lg bg-[#111116] border border-white/10 shadow-2xl py-1 z-30">
                <button onClick={onConnect} className="block w-full text-left px-4 py-2.5 text-sm text-slate-300 hover:bg-white/5">
                  Change merchant key
                </button>
                <button onClick={onLogout} className="block w-full text-left px-4 py-2.5 text-sm text-rose-400 hover:bg-rose-500/10">
                  Log out
                </button>
              </div>
            )}
          </div>
        </div>
        <nav className="max-w-7xl mx-auto flex items-center gap-1 px-6 h-12">
          {['Overview', 'Search', 'Chat'].map((name) => (
            <button
              key={name}
              onClick={() => setTab(name)}
              className={`px-3.5 py-1.5 rounded-md text-sm font-semibold transition-colors ${
                tab === name ? 'bg-indigo-500/15 text-indigo-300' : 'text-slate-500 hover:text-slate-200'
              }`}
            >
              {name}
            </button>
          ))}
          <button
            onClick={onSync}
            className="ml-auto px-4 py-1.5 rounded-md text-sm font-semibold bg-gradient-to-r from-indigo-500 to-fuchsia-500 text-white hover:opacity-90 transition-opacity"
          >
            ↻ Sync data
          </button>
        </nav>
      </header>

      {notice && (
        <p className="max-w-7xl mx-auto px-6 pt-3 text-sm text-indigo-300 relative z-10">{notice}</p>
      )}

      {/* ─────────────────────────── Overview tab ─────────────────────────── */}
      {tab === 'Overview' && (
        <div className="max-w-7xl mx-auto px-6 pt-6 space-y-6 relative z-10">
          <div>
            <h1 className="text-2xl font-bold text-white">Analytics overview</h1>
            <p className="text-sm text-slate-500 mt-1">
              {throughput.records_processed ? count(throughput.records_processed) : 0} records processed
              {throughput.last_reconciled_at && <> · last reconciled {fmtDate(throughput.last_reconciled_at)}</>}
            </p>
          </div>

          {/* Today strip */}
          <Section title={`Today — ${todayLabel}`} subtitle="Invoices and payments recorded today only">
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
              <KpiCard tone="indigo" label="Invoices today" value={count(today.invoices?.length)} />
              <KpiCard tone="cyan" label="Payments today" value={count(today.payments?.length)} />
              <KpiCard tone="emerald" label="Invoices this month" value={count(activity.invoices?.[2])} />
              <KpiCard tone="emerald" label="Payments this month" value={count(activity.payments?.[2])} />
            </div>
          </Section>

          {/* Volume */}
          <Section title="Volume">
            <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-4">
              <KpiCard label="Total invoices" value={count(counts.total_invoices)} />
              <KpiCard label="Total payments" value={count(counts.total_payments)} />
              <KpiCard label="Total settlements" value={count(counts.total_settlements)} />
              <KpiCard tone="emerald" label="Fully paid" value={count(counts.fully_paid)} />
              <KpiCard tone="amber" label="Partially paid" value={count(counts.partially_paid)} />
              <KpiCard tone="rose" label="Unpaid" value={count(counts.unpaid)} />
            </div>
          </Section>

          {/* Financials + classification pie */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            <Section title="Financial position" subtitle="Outstanding vs collected vs settled">
              <div className="space-y-3 mb-4">
                <KpiCard tone="amber" label="Total outstanding" value={rupees(amounts.total_outstanding)} />
                <KpiCard tone="emerald" label="Total collected" value={rupees(amounts.total_collected)} />
                <KpiCard tone="indigo" label="Total settled" value={rupees(amounts.total_settled)} />
                <KpiCard label="Payment → settlement difference" value={rupees(amounts.payment_settlement_difference)} hint="Fees, tax and rounding" />
              </div>
            </Section>

            <Section title="Amounts, visualized" subtitle="₹ (in rupees)">
              <ResponsiveContainer width="100%" height={230}>
                <BarChart data={amountsData} margin={{ left: 0, right: 10 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke={GRID_STROKE} vertical={false} />
                  <XAxis dataKey="name" tick={AXIS_TICK} axisLine={false} tickLine={false} />
                  <YAxis tick={{ fontSize: 11, fill: '#64748b' }} axisLine={false} tickLine={false} />
                  <Tooltip contentStyle={TOOLTIP_STYLE} formatter={(v) => `₹${Number(v).toLocaleString('en-IN')}`} />
                  <Bar dataKey="value" radius={[6, 6, 0, 0]}>
                    {amountsData.map((d, i) => <Cell key={i} fill={d.fill} />)}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </Section>

            <Section title="Invoice status split" subtitle="Paid / Partial / Unpaid / Exception">
              {classData.length ? (
                <ResponsiveContainer width="100%" height={230}>
                  <PieChart>
                    <Pie data={classData} dataKey="value" nameKey="name" innerRadius={50} outerRadius={80} paddingAngle={2}>
                      {classData.map((d, i) => <Cell key={i} fill={CLASS_COLORS[d.name] || '#94a3b8'} />)}
                    </Pie>
                    <Tooltip contentStyle={TOOLTIP_STYLE} />
                    <Legend iconType="circle" wrapperStyle={{ fontSize: 12, color: '#94a3b8' }} />
                  </PieChart>
                </ResponsiveContainer>
              ) : (
                <p className="text-sm text-slate-500 py-16 text-center">No reconciled records yet — run Sync data.</p>
              )}
            </Section>
          </div>

          {/* Reconciliation health */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            <Section title="Reconciliation health" subtitle="Match rate & AI confidence">
              <div className="space-y-5">
                <ProgressBar label="Match rate" valuePct={recon.match_rate || 0} tone="indigo" hint={`${count(recon.total_matched_records)} matched records`} />
                <ProgressBar label="Avg. AI confidence" valuePct={recon.avg_confidence || 0} tone="emerald" hint="Across AI-resolved matches" />
              </div>
              <div className="grid grid-cols-3 gap-3 mt-5">
                <KpiCard label="Auto-reconciled" value={count(recon.auto_reconciled)} tone="indigo" />
                <KpiCard label="AI-resolved" value={count(recon.ai_resolved)} tone="cyan" />
                <KpiCard label="Unresolved" value={count(recon.unresolved_exceptions)} tone="rose" />
              </div>
            </Section>

            <Section title="Resolution breakdown" subtitle="How records got reconciled">
              <ResponsiveContainer width="100%" height={230}>
                <BarChart data={resolutionData} layout="vertical" margin={{ left: 10 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke={GRID_STROKE} horizontal={false} />
                  <XAxis type="number" tick={{ fontSize: 11, fill: '#64748b' }} axisLine={false} tickLine={false} allowDecimals={false} />
                  <YAxis type="category" dataKey="name" tick={AXIS_TICK} axisLine={false} tickLine={false} width={110} />
                  <Tooltip contentStyle={TOOLTIP_STYLE} />
                  <Bar dataKey="value" radius={[0, 6, 6, 0]}>
                    {resolutionData.map((d, i) => <Cell key={i} fill={d.fill} />)}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </Section>

            <Section title="Activity" subtitle="Invoices vs payments over time">
              <ResponsiveContainer width="100%" height={230}>
                <BarChart data={activityData} margin={{ left: 0, right: 10 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke={GRID_STROKE} vertical={false} />
                  <XAxis dataKey="period" tick={AXIS_TICK} axisLine={false} tickLine={false} />
                  <YAxis tick={{ fontSize: 11, fill: '#64748b' }} axisLine={false} tickLine={false} allowDecimals={false} />
                  <Tooltip contentStyle={TOOLTIP_STYLE} />
                  <Legend wrapperStyle={{ fontSize: 12, color: '#94a3b8' }} />
                  <Bar dataKey="Invoices" fill="#818cf8" radius={[6, 6, 0, 0]} />
                  <Bar dataKey="Payments" fill="#22d3ee" radius={[6, 6, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </Section>
          </div>

          {/* Risk + accuracy */}
          <Section title="Risk & data quality">
            <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-4">
              <KpiCard tone="rose" label="Duplicate / suspicious payments" value={count(risk.duplicate_payments)} />
              <KpiCard tone="rose" label="Unmatched payments" value={count(risk.unmatched_payments)} />
              <KpiCard tone="amber" label="Pending / authorized" value={count(risk.pending_payments)} />
              <KpiCard tone="rose" label="Settlement exceptions" value={count(risk.settlement_exceptions)} />
              <KpiCard label="Records processed" value={count(throughput.records_processed)} />
              <KpiCard
                label="Accuracy vs ground truth"
                value={stats?.ground_truth_accuracy != null ? `${stats.ground_truth_accuracy}%` : '—'}
                hint={stats?.ground_truth_accuracy != null ? 'Against labeled synthetic set' : 'Needs a labeled synthetic dataset'}
              />
            </div>
          </Section>

          {/* Exceptions with AI reasoning */}
          <Section title="Exceptions" subtitle="Unresolved cases with AI reasoning, where available">
            {exceptions.length === 0 ? (
              <p className="text-sm text-slate-500 py-6 text-center">No open exceptions. Everything is reconciled.</p>
            ) : (
              <div className="divide-y divide-white/5">
                {exceptions.map((ex) => (
                  <div key={ex._id || ex.invoice_id} className="py-4 flex items-start justify-between gap-4">
                    <div className="min-w-0">
                      <div className="flex items-center gap-2 flex-wrap">
                        <span className="font-semibold text-slate-100 text-sm">{ex.invoice_id || ex.payment_id || 'Exception'}</span>
                        <span className={`text-xs font-semibold px-2 py-0.5 rounded-full ${SEVERITY_TONE[ex.severity] || SEVERITY_TONE.medium}`}>
                          {ex.severity || 'medium'}
                        </span>
                        <span className="text-xs text-slate-500">{ex.category?.replaceAll('_', ' ')}</span>
                      </div>
                      {ex.ai_reasoning?.likely_cause ? (
                        <p className="mt-1.5 text-sm text-slate-400 leading-relaxed">{ex.ai_reasoning.likely_cause}</p>
                      ) : (
                        <p className="mt-1.5 text-sm text-slate-600 italic">No AI explanation generated yet for this case.</p>
                      )}
                    </div>
                    <button
                      onClick={() =>
                        askAiAbout(
                          `Explain in detail why ${ex.invoice_id || ex.payment_id || 'this record'} (${ex.category?.replaceAll('_', ' ') || 'exception'}) is unresolved and what I should do next.`
                        )
                      }
                      className="shrink-0 text-xs font-semibold px-3 py-1.5 rounded-md border border-indigo-400/30 text-indigo-300 hover:bg-indigo-500/10 whitespace-nowrap"
                    >
                      Ask AI →
                    </button>
                  </div>
                ))}
              </div>
            )}
          </Section>

          {/* Recent transactions */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {[
              ['Recent invoices', recent.invoices],
              ['Recent payments', recent.payments],
              ['Recent settlements', recent.settlements],
            ].map(([title, records]) => (
              <Section key={title} title={title}>
                {(records || []).length === 0 && <p className="text-sm text-slate-500 py-4">No records yet.</p>}
                {(records || []).map((record) => (
                  <button
                    key={record._id}
                    onClick={() => setSelected(record)}
                    className="block w-full text-left py-3 border-t border-white/5 first:border-t-0 hover:bg-white/[0.03] -mx-1 px-1 rounded"
                  >
                    <span className="text-sm font-medium text-slate-200 truncate block">
                      {record.customer_name || record.invoice_number || record.email || record.razorpay_invoice_id || record.razorpay_payment_id || record.razorpay_settlement_id}
                    </span>
                    <span className="text-xs text-slate-500 mt-0.5 block">
                      {rupees(record.amount)} · {fmtDate(record.created_at)}
                    </span>
                  </button>
                ))}
              </Section>
            ))}
          </div>
        </div>
      )}

      {/* ─────────────────────────── Search tab ─────────────────────────── */}
      {tab === 'Search' && (
        <div className="max-w-3xl mx-auto px-6 pt-6 relative z-10">
          <h1 className="text-2xl font-bold text-white">Search transactions</h1>
          <input
            value={query}
            placeholder="Name, invoice ID, payment ID…"
            onChange={search}
            className="w-full mt-4 rounded-lg bg-white/[0.03] border border-white/10 px-4 py-3 text-sm text-slate-100 placeholder:text-slate-500 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
          />
          <div className="mt-4 space-y-2">
            {results.map((item) => (
              <button
                key={item.record._id}
                onClick={() => setSelected(item.record)}
                className="block w-full text-left rounded-lg border border-white/10 bg-white/[0.02] px-4 py-3 hover:border-indigo-400/30 hover:bg-indigo-500/5"
              >
                <span className="text-xs font-semibold uppercase tracking-wide text-indigo-300">{item.type}</span>
                <span className="block text-sm font-medium text-slate-200 mt-0.5">
                  {item.record.razorpay_invoice_id || item.record.razorpay_payment_id || item.record.razorpay_settlement_id}
                </span>
                <span className="block text-xs text-slate-500 mt-0.5">{rupees(item.record.amount)}</span>
              </button>
            ))}
          </div>
        </div>
      )}

      {/* ─────────────────────────── Chat tab ─────────────────────────── */}
      {tab === 'Chat' && (
        <div className="max-w-2xl mx-auto px-6 pt-6 relative z-10">
          <h1 className="text-2xl font-bold text-white">Exception analyst</h1>
          <p className="text-sm text-slate-500 mt-1">Ask anything about a transaction or exception — answers are grounded only in your reconciled evidence.</p>
          <div className="mt-5 min-h-[120px] rounded-xl border border-white/10 bg-white/[0.03] p-4 text-sm text-slate-300 leading-relaxed">
            {asking ? <span className="text-slate-500">Thinking…</span> : answer || <span className="text-slate-500">Ask a question to get started.</span>}
          </div>
          <form onSubmit={submitChat} className="mt-4 flex gap-2">
            <input
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Why is this invoice unresolved?"
              className="flex-1 rounded-lg bg-white/[0.03] border border-white/10 px-4 py-2.5 text-sm text-slate-100 placeholder:text-slate-500 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
            />
            <button className="rounded-lg bg-gradient-to-r from-indigo-500 to-fuchsia-500 px-4 py-2.5 text-sm font-semibold text-white hover:opacity-90 transition-opacity whitespace-nowrap">
              Ask AI
            </button>
          </form>
        </div>
      )}

      {/* ─────────────────────────── Detail drawer ─────────────────────────── */}
      {selected && (
        <aside className="fixed right-0 top-0 h-screen w-full max-w-[460px] bg-[#0d0d12] border-l border-white/10 shadow-2xl z-40 p-6 overflow-y-auto">
          <button onClick={() => setSelected()} className="text-slate-500 hover:text-slate-200 text-lg">×</button>
          <h2 className="text-lg font-bold text-white mt-3">Transaction details</h2>
          <pre className="mt-4 max-h-[60vh] overflow-auto rounded-lg bg-black/40 border border-white/10 p-3 text-[11px] leading-relaxed text-slate-400">
            {JSON.stringify(selected, null, 2)}
          </pre>
          <button
            onClick={() =>
              askAiAbout(
                `Explain this transaction in detail: ${selected.razorpay_invoice_id || selected.razorpay_payment_id || selected.razorpay_settlement_id || selected._id}.`
              )
            }
            className="mt-4 w-full rounded-lg bg-gradient-to-r from-indigo-500 to-fuchsia-500 py-2.5 text-sm font-semibold text-white hover:opacity-90 transition-opacity"
          >
            Ask AI →
          </button>
        </aside>
      )}
    </main>
  )
}