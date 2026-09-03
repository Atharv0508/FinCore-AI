import { GoogleLogin } from '@react-oauth/google'
import Logo from '../components/Logo'

export default function LandingPage({ showLogin, setShowLogin, onGoogleLogin, onGoogleError, notice }) {
  return (
    <main className="min-h-screen bg-[#0a0a0f] text-slate-100 relative overflow-hidden">
      {/* Ambient gradient blob background */}
      <div
        className="pointer-events-none absolute inset-0 -z-10 opacity-70"
        style={{
          background:
            'radial-gradient(circle at 20% 15%, rgba(99,102,241,0.35), transparent 45%),' +
            'radial-gradient(circle at 80% 20%, rgba(217,70,239,0.30), transparent 45%),' +
            'radial-gradient(circle at 50% 75%, rgba(251,146,60,0.22), transparent 50%)',
          filter: 'blur(40px)',
        }}
      />
      <div className="pointer-events-none absolute inset-0 -z-10 bg-[radial-gradient(ellipse_at_top,rgba(255,255,255,0.04),transparent_60%)]" />

      {/* Header */}
      <header className="max-w-6xl mx-auto flex items-center justify-between px-6 py-6 relative z-10">
        <Logo />
        <button
          onClick={() => setShowLogin(true)}
          className="text-sm font-semibold text-slate-200 hover:text-white transition-colors px-4 py-2 rounded-lg border border-white/10 hover:border-white/20 bg-white/[0.03]"
        >
          Sign in
        </button>
      </header>

      {/* Hero */}
      <section className="relative z-10">
        <div className="max-w-3xl mx-auto text-center px-6 pt-16 pb-20">
          <span className="inline-flex items-center gap-2 rounded-full border border-indigo-400/30 bg-indigo-500/10 px-4 py-1.5 text-xs font-semibold tracking-wide text-indigo-300">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-400" />
            Finance reconciliation, reimagined
          </span>

          <h1 className="mt-6 text-5xl sm:text-6xl font-extrabold tracking-tight leading-[1.08]">
            <span className="text-white">Every transaction.</span>
            <br />
            <span className="bg-gradient-to-r from-indigo-400 via-fuchsia-400 to-orange-300 bg-clip-text text-transparent">
              Perfectly reconciled.
            </span>
          </h1>

          <p className="mt-6 text-lg text-slate-400 leading-relaxed max-w-xl mx-auto">
            FinCore AI connects your Razorpay data, applies deterministic matching across
            invoices, payments and settlements, and uses AI only where the evidence runs out —
            so every exception comes with a reason, not a guess.
          </p>

          <div className="mt-10 flex items-center justify-center gap-4">
            <button
              onClick={() => setShowLogin(true)}
              className="px-7 py-3.5 rounded-xl bg-gradient-to-r from-indigo-500 via-fuchsia-500 to-orange-400 text-white font-semibold shadow-[0_8px_30px_rgba(139,92,246,0.35)] hover:shadow-[0_8px_40px_rgba(139,92,246,0.5)] hover:scale-[1.02] transition-all"
            >
              Get started →
            </button>
          </div>
        </div>

        {/* Feature strip */}
        <div className="max-w-5xl mx-auto grid grid-cols-1 sm:grid-cols-3 gap-5 px-6 pb-28 relative z-10">
          {[
            {
              title: 'Deterministic first',
              body: 'Exact IDs, then fuzzy email + amount matching — resolved without AI wherever the evidence is clear.',
              accent: 'from-indigo-500/20 to-transparent',
            },
            {
              title: 'AI for the rest',
              body: 'Unclear cases go to an AI analyst that reasons from evidence only, and flags what it cannot resolve.',
              accent: 'from-fuchsia-500/20 to-transparent',
            },
            {
              title: 'One clear picture',
              body: 'Match rate, exceptions, and cash position in a single dashboard — no more manual spreadsheet checks.',
              accent: 'from-orange-400/20 to-transparent',
            },
          ].map((f) => (
            <div
              key={f.title}
              className={`rounded-2xl border border-white/10 bg-gradient-to-b ${f.accent} bg-white/[0.02] backdrop-blur-sm p-6 text-left hover:border-white/20 transition-colors`}
            >
              <h3 className="font-semibold text-white">{f.title}</h3>
              <p className="mt-2.5 text-sm text-slate-400 leading-relaxed">{f.body}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Login modal */}
      {showLogin && (
        <div className="fixed inset-0 z-50 grid place-items-center bg-black/70 backdrop-blur-sm px-4">
          <div className="w-full max-w-sm rounded-2xl bg-[#111116] border border-white/10 p-8 shadow-2xl">
            <div className="flex items-center justify-between">
              <Logo />
              <button
                onClick={() => setShowLogin(false)}
                className="text-slate-500 hover:text-slate-200 text-lg leading-none"
                aria-label="Close"
              >
                ×
              </button>
            </div>
            <h2 className="mt-6 text-xl font-bold text-white">Welcome to FinCore</h2>
            <p className="mt-1 text-sm text-slate-400">Sign in to create your workspace.</p>
            <div className="mt-6">
              <GoogleLogin onSuccess={onGoogleLogin} onError={onGoogleError} />
            </div>
            {notice && <p className="mt-4 text-sm text-indigo-300">{notice}</p>}
          </div>
        </div>
      )}
    </main>
  )
}