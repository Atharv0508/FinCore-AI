import Logo from '../components/Logo'

export default function ConnectRazorpayPage({ user, credentials, setCredentials, onConnect, notice }) {
  return (
    <main className="min-h-screen bg-slate-50">
      <header className="max-w-6xl mx-auto flex items-center justify-between px-6 py-5">
        <Logo />
        <span className="text-sm text-slate-500">{user.email}</span>
      </header>

      <section className="max-w-md mx-auto mt-16 rounded-2xl bg-white border border-slate-200 shadow-sm p-8">
        <p className="text-xs font-bold tracking-[0.16em] text-indigo-600 uppercase">
          Secure connection
        </p>
        <h1 className="mt-2 text-2xl font-bold text-slate-900">Connect Razorpay</h1>
        <p className="mt-2 text-sm text-slate-500 leading-relaxed">
          Test-mode credentials are Fernet-encrypted before storage and are only ever used
          server-side to pull your invoices, payments and settlements.
        </p>

        <form onSubmit={onConnect} className="mt-6 space-y-4">
          <div>
            <label className="block text-xs font-semibold text-slate-600 mb-1">Test Key ID</label>
            <input
              required
              placeholder="rzp_test_…"
              value={credentials.key_id}
              onChange={(e) => setCredentials({ ...credentials, key_id: e.target.value })}
              className="w-full rounded-lg border border-slate-300 px-3 py-2.5 text-sm text-slate-900 placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
            />
          </div>
          <div>
            <label className="block text-xs font-semibold text-slate-600 mb-1">Test Key Secret</label>
            <input
              required
              type="password"
              placeholder="Test Key Secret"
              value={credentials.key_secret}
              onChange={(e) => setCredentials({ ...credentials, key_secret: e.target.value })}
              className="w-full rounded-lg border border-slate-300 px-3 py-2.5 text-sm text-slate-900 placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
            />
          </div>
          <button className="w-full rounded-lg bg-indigo-600 py-2.5 text-sm font-semibold text-white shadow-sm hover:bg-indigo-700 transition-colors">
            Connect securely →
          </button>
        </form>

        {notice && <p className="mt-4 text-sm text-indigo-600">{notice}</p>}

        <div className="mt-6 flex items-start gap-2 rounded-lg bg-slate-50 border border-slate-200 px-3 py-2.5">
          <span className="text-slate-400 text-sm">ⓘ</span>
          <p className="text-xs text-slate-500 leading-relaxed">
            Use your Razorpay <span className="font-medium text-slate-700">test-mode</span> keys
            (Dashboard → Settings → API Keys → Generate Test Key). No live data is ever touched.
          </p>
        </div>
      </section>
    </main>
  )
}