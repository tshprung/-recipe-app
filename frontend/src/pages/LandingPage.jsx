import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'

const COLORS = {
  bg: '#111111',
  card: '#1c1c1c',
  text: '#F8F8F6',
  accent: '#8FAF8F',
  secondary: '#C96A4A',
}

const FOOD_IMAGES = [
  'https://images.unsplash.com/photo-1473093226795-af9932fe5856?auto=format&fit=crop&w=900&q=70',
  'https://images.unsplash.com/photo-1543353071-087092ec393a?auto=format&fit=crop&w=900&q=70',
  'https://images.unsplash.com/photo-1490645935967-10de6ba17061?auto=format&fit=crop&w=900&q=70',
]

function cn(...xs) {
  return xs.filter(Boolean).join(' ')
}

function Anchor({ id }) {
  return <span id={id} className="block scroll-mt-24" />
}

export default function LandingPage() {
  const [mobileOpen, setMobileOpen] = useState(false)
  const year = useMemo(() => new Date().getFullYear(), [])

  useEffect(() => {
    document.documentElement.style.scrollBehavior = 'smooth'
  }, [])

  return (
    <div
      className="min-h-screen"
      style={{ backgroundColor: COLORS.bg, color: COLORS.text }}
    >
      {/* Background */}
      <div aria-hidden="true" className="fixed inset-0 -z-10 overflow-hidden">
        <div
          className="absolute -top-40 left-1/2 h-[520px] w-[520px] -translate-x-1/2 rounded-full blur-3xl"
          style={{ backgroundColor: COLORS.accent, opacity: 0.22 }}
        />
        <div
          className="absolute top-[35%] -left-48 h-[560px] w-[560px] rounded-full blur-3xl"
          style={{ backgroundColor: COLORS.secondary, opacity: 0.16 }}
        />
        <div
          className="absolute -bottom-56 right-[-180px] h-[640px] w-[640px] rounded-full blur-3xl"
          style={{ backgroundColor: COLORS.accent, opacity: 0.14 }}
        />
        <div className="absolute inset-0 bg-gradient-to-b from-black/30 via-black/60 to-black" />
      </div>

      {/* Navbar */}
      <header className="sticky top-0 z-50 backdrop-blur bg-black/45 border-b border-white/5">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
          <div className="h-16 flex items-center justify-between gap-4">
            <Link to="/" className="flex items-center gap-2 min-w-0">
              <span
                className="inline-flex h-9 w-9 items-center justify-center rounded-xl ring-1 ring-white/10 shadow"
                style={{ backgroundColor: 'rgba(255,255,255,0.05)' }}
              >
                <span className="text-lg">🍽️</span>
              </span>
              <span className="font-extrabold tracking-tight truncate">
                myrecipes<span style={{ color: COLORS.accent }}>.cloud</span>
              </span>
            </Link>

            <nav className="hidden md:flex items-center gap-6 text-sm text-white/75">
              <a href="#features" className="hover:text-white transition-colors">Features</a>
              <a href="#pricing" className="hover:text-white transition-colors">Pricing</a>
              <Link to="/login" className="hover:text-white transition-colors">Sign In</Link>
            </nav>

            <div className="flex items-center gap-2">
              <Link
                to="/login?tab=register"
                className="hidden sm:inline-flex items-center justify-center rounded-xl px-4 py-2 text-sm font-semibold text-black shadow transition hover:opacity-95"
                style={{ backgroundColor: COLORS.accent }}
              >
                Start Free
              </Link>
              <button
                type="button"
                onClick={() => setMobileOpen(v => !v)}
                className="md:hidden inline-flex items-center justify-center rounded-xl px-3 py-2 ring-1 ring-white/10 hover:bg-white/10 transition"
                style={{ backgroundColor: 'rgba(255,255,255,0.05)' }}
                aria-label="Open menu"
                aria-expanded={mobileOpen ? 'true' : 'false'}
              >
                <svg className="h-5 w-5" viewBox="0 0 24 24" fill="none">
                  <path d="M4 6h16M4 12h16M4 18h16" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
                </svg>
              </button>
            </div>
          </div>

          {mobileOpen && (
            <div className="md:hidden pb-4">
              <div
                className="mt-2 grid gap-2 rounded-2xl ring-1 ring-white/10 p-3"
                style={{ backgroundColor: 'rgba(28,28,28,0.65)' }}
              >
                <a onClick={() => setMobileOpen(false)} href="#features" className="rounded-xl px-3 py-2 text-sm text-white/80 hover:bg-white/5 hover:text-white transition">Features</a>
                <a onClick={() => setMobileOpen(false)} href="#pricing" className="rounded-xl px-3 py-2 text-sm text-white/80 hover:bg-white/5 hover:text-white transition">Pricing</a>
                <Link onClick={() => setMobileOpen(false)} to="/login" className="rounded-xl px-3 py-2 text-sm text-white/80 hover:bg-white/5 hover:text-white transition">Sign In</Link>
                <Link
                  onClick={() => setMobileOpen(false)}
                  to="/login?tab=register"
                  className="mt-1 inline-flex items-center justify-center rounded-xl px-4 py-2 text-sm font-semibold text-black shadow"
                  style={{ backgroundColor: COLORS.accent }}
                >
                  Start Free
                </Link>
              </div>
            </div>
          )}
        </div>
      </header>

      {/* Hero */}
      <section className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 pt-14 sm:pt-20">
        <div className="grid lg:grid-cols-2 gap-10 items-center">
          <div>
            <div
              className="inline-flex items-center gap-2 rounded-full px-3 py-1 text-xs text-white/80 ring-1 ring-white/10"
              style={{ backgroundColor: 'rgba(255,255,255,0.05)' }}
            >
              <span className="h-2 w-2 rounded-full" style={{ backgroundColor: COLORS.accent }} />
              AI adapts recipes to your diet + location
            </div>

            <h1 className="mt-5 text-4xl sm:text-5xl lg:text-6xl font-extrabold tracking-tight">
              Turn Any Recipe Into One That <span style={{ color: COLORS.accent }}>Works for You</span>
            </h1>

            <p className="mt-5 text-base sm:text-lg text-white/75 max-w-xl">
              Import recipes from any website or language and let AI adapt them to your diet, ingredients, and location.
            </p>

            <div className="mt-7 flex flex-col sm:flex-row gap-3 sm:items-center">
              <Link
                to="/login?tab=register"
                className="inline-flex items-center justify-center rounded-xl px-5 py-3 text-sm font-extrabold text-black shadow-soft transition hover:opacity-95"
                style={{ backgroundColor: COLORS.accent }}
              >
                Start Your Recipe Book Today
              </Link>
              <a
                href="#how"
                className="inline-flex items-center justify-center rounded-xl px-5 py-3 text-sm font-semibold ring-1 ring-white/10 hover:bg-white/10 transition"
                style={{ backgroundColor: 'rgba(255,255,255,0.05)' }}
              >
                See How It Works
              </a>
            </div>

            <p className="mt-3 text-xs text-white/60">
              Free to start — includes <span className="text-white font-semibold">5 AI recipe adaptations</span>
            </p>

            <div className="mt-8 grid grid-cols-2 sm:grid-cols-4 gap-2 text-xs text-white/70">
              {[
                '✓ Any website',
                '✓ Vegan / GF / Kosher',
                '✓ Local ingredient swaps',
                '✓ Unified shopping list',
              ].map((s) => (
                <div key={s} className="rounded-xl px-3 py-2 ring-1 ring-white/10" style={{ backgroundColor: 'rgba(255,255,255,0.04)' }}>
                  {s}
                </div>
              ))}
            </div>
          </div>

          {/* Hero demo */}
          <div className="relative">
            <div
              className="absolute -inset-6 rounded-[28px] blur-2xl"
              style={{
                background: `linear-gradient(135deg, rgba(143,175,143,0.22), rgba(255,255,255,0), rgba(201,106,74,0.22))`,
              }}
            />
            <div className="relative rounded-2xl ring-1 ring-white/10 shadow-soft2 overflow-hidden" style={{ backgroundColor: COLORS.card }}>
              <div className="p-5 sm:p-6 border-b border-white/5 flex items-center justify-between">
                <div className="text-sm font-semibold">Recipe URL → AI Adaptation → Shopping List</div>
                <div className="text-xs text-white/55">Live demo</div>
              </div>

              <div className="p-5 sm:p-6 grid gap-4">
                <div className="rounded-2xl p-4 ring-1 ring-white/10 hover:ring-white/20 transition" style={{ backgroundColor: 'rgba(17,17,17,0.55)' }}>
                  <div className="flex items-center justify-between">
                    <div className="text-xs font-semibold text-white/70 uppercase tracking-wide">Input</div>
                    <span className="text-xs text-white/50">Recipe URL</span>
                  </div>
                  <div className="mt-3 flex items-center gap-2">
                    <div className="flex-1 rounded-xl px-3 py-2 text-xs text-white/70 ring-1 ring-white/10 overflow-hidden" style={{ backgroundColor: 'rgba(255,255,255,0.04)' }}>
                      italian-recipe.com/carbonara
                    </div>
                    <div className="rounded-xl px-3 py-2 text-xs font-extrabold text-black shadow" style={{ backgroundColor: COLORS.accent }}>
                      Adapt Recipe
                    </div>
                  </div>
                </div>

                <div className="flex items-center justify-center text-white/60">
                  <div className="inline-flex items-center gap-2 rounded-full px-3 py-1 text-xs ring-1 ring-white/10" style={{ backgroundColor: 'rgba(255,255,255,0.05)' }}>
                    <span className="inline-block h-2 w-2 rounded-full animate-pulse" style={{ backgroundColor: COLORS.secondary }} />
                    AI adapts to your choices…
                    <svg className="h-4 w-4" viewBox="0 0 24 24" fill="none">
                      <path d="M13 5l7 7-7 7M4 12h15" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
                    </svg>
                  </div>
                </div>

                <div className="rounded-2xl p-4 ring-1 ring-white/10 hover:ring-white/20 transition" style={{ backgroundColor: 'rgba(17,17,17,0.55)' }}>
                  <div className="flex items-center justify-between gap-3">
                    <div className="text-xs font-semibold text-white/70 uppercase tracking-wide">Output</div>
                    <div className="text-xs text-white/60">
                      Diet: <span className="text-white font-semibold">Gluten-Free</span> · Location:{' '}
                      <span className="text-white font-semibold">Poland</span>
                    </div>
                  </div>

                  <div className="mt-4 grid gap-2 text-sm">
                    {[
                      ['Pancetta', 'Smoked turkey'],
                      ['Pasta', 'Gluten-free pasta'],
                      ['Parmesan', 'Local hard cheese'],
                    ].map(([from, to]) => (
                      <div key={from} className="flex items-center justify-between rounded-xl px-3 py-2 ring-1 ring-white/10" style={{ backgroundColor: 'rgba(255,255,255,0.04)' }}>
                        <span className="text-white/80">{from}</span>
                        <span className="font-semibold" style={{ color: COLORS.secondary }}>→ {to}</span>
                      </div>
                    ))}
                  </div>

                  <div className="mt-4 flex items-center justify-between">
                    <div className="text-xs text-white/55">Shopping list gets merged automatically</div>
                    <div className="rounded-xl px-3 py-2 text-xs font-semibold ring-1 ring-white/10 hover:bg-white/10 transition" style={{ backgroundColor: 'rgba(255,255,255,0.05)' }}>
                      Generate shopping list
                    </div>
                  </div>
                </div>

                <div className="grid grid-cols-3 gap-3 pt-2">
                  {FOOD_IMAGES.map((src) => (
                    <img
                      key={src}
                      src={src}
                      alt="Food placeholder"
                      className="h-20 w-full rounded-2xl object-cover ring-1 ring-white/10 hover:ring-white/20 transition"
                      loading="lazy"
                    />
                  ))}
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Problem */}
      <section className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 mt-16 sm:mt-24">
        <Anchor id="how" />
        <div className="max-w-2xl">
          <h2 className="text-2xl sm:text-3xl font-extrabold tracking-tight">
            Most Recipes Weren’t Written for Your Kitchen
          </h2>
          <p className="mt-3 text-white/70">
            Great recipes can still fail when ingredients, language, or dietary needs don’t match your reality.
          </p>
        </div>

        <div className="mt-8 grid md:grid-cols-3 gap-5">
          {[
            {
              icon: '🛒',
              title: 'Ingredients not available locally',
              body: 'AI swaps ingredients with local equivalents you can actually buy.',
            },
            {
              icon: '🥗',
              title: 'Diet restrictions break recipes',
              body: 'Vegan, gluten‑free, kosher, and more — adapted without losing flavor.',
            },
            {
              icon: '🧾',
              title: 'Recipes scattered everywhere',
              body: 'Build one clean recipe book you can search, revisit, and share.',
            },
          ].map((c) => (
            <div
              key={c.title}
              className="rounded-2xl p-6 ring-1 ring-white/10 shadow-soft hover:shadow-soft2 transition"
              style={{ backgroundColor: COLORS.card }}
            >
              <div className="flex items-center gap-3">
                <span className="inline-flex h-10 w-10 items-center justify-center rounded-xl ring-1 ring-white/10" style={{ backgroundColor: 'rgba(255,255,255,0.05)' }}>
                  {c.icon}
                </span>
                <div className="font-semibold">{c.title}</div>
              </div>
              <p className="mt-3 text-sm text-white/70">{c.body}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Solution */}
      <section id="features" className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 mt-16 sm:mt-24">
        <div className="flex flex-col lg:flex-row lg:items-end lg:justify-between gap-6">
          <div className="max-w-2xl">
            <h2 className="text-2xl sm:text-3xl font-extrabold tracking-tight">Your Smart Recipe Book</h2>
            <p className="mt-3 text-white/70">
              Import any recipe, adapt it to your diet and location, and generate a unified shopping list across recipes.
            </p>
          </div>
          <Link
            to="/login?tab=register"
            className="inline-flex items-center justify-center rounded-xl px-5 py-3 text-sm font-extrabold text-black shadow-soft transition hover:opacity-95 w-full sm:w-auto"
            style={{ backgroundColor: COLORS.accent }}
          >
            Start Free
          </Link>
        </div>

        <div className="mt-8 grid md:grid-cols-3 gap-5">
          {[
            {
              icon: '🔗',
              title: 'Import Recipe',
              body: 'Paste a URL or text. We extract ingredients + instructions automatically.',
            },
            {
              icon: '✨',
              title: 'Adapt Recipe',
              body: 'Vegan / gluten-free / kosher — plus ingredient swaps you actually want.',
            },
            {
              icon: '🧺',
              title: 'Shopping List',
              body: 'Combine many recipes into one list you can print or email.',
            },
          ].map((c) => (
            <div
              key={c.title}
              className="rounded-2xl p-6 ring-1 ring-white/10 shadow-soft hover:shadow-soft2 transition"
              style={{ backgroundColor: COLORS.card }}
            >
              <div className="text-sm font-semibold flex items-center gap-2">
                <span className="inline-flex h-9 w-9 items-center justify-center rounded-xl ring-1 ring-white/10" style={{ backgroundColor: 'rgba(255,255,255,0.05)' }}>
                  {c.icon}
                </span>
                {c.title}
              </div>
              <p className="mt-3 text-sm text-white/70">{c.body}</p>
            </div>
          ))}
        </div>

        <div className="mt-10 grid sm:grid-cols-2 lg:grid-cols-3 gap-5">
          {[
            ['🌍', 'Translate Recipes', 'Automatically translate recipes to your language.'],
            ['🔁', 'Ingredient Substitution', 'Get substitutes for missing ingredients (clearly marked).'],
            ['📍', 'Local Ingredient Swap', 'Replace unavailable items with local equivalents.'],
            ['🍳', 'Cook From What You Have', 'Find recipes based on ingredients already in your kitchen.'],
            ['🗂️', 'Organize Recipe Book', 'Keep favorites in one searchable place.'],
            ['🤖', 'Smart Recipe Suggestions', 'AI generates ideas that match your diet and pantry.'],
          ].map(([icon, title, body]) => (
            <div
              key={title}
              className="rounded-2xl p-6 ring-1 ring-white/10 shadow-soft hover:ring-white/20 transition"
              style={{ backgroundColor: COLORS.card }}
            >
              <div className="flex items-center gap-3">
                <span className="text-xl">{icon}</span>
                <div className="font-semibold">{title}</div>
              </div>
              <p className="mt-2 text-sm text-white/70">{body}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Example */}
      <section className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 mt-16 sm:mt-24">
        <div className="rounded-2xl p-6 sm:p-8 ring-1 ring-white/10 shadow-soft" style={{ backgroundColor: COLORS.card }}>
          <div className="flex flex-col md:flex-row md:items-end md:justify-between gap-4">
            <div>
              <h2 className="text-2xl sm:text-3xl font-extrabold tracking-tight">Example Recipe Adaptation</h2>
              <p className="mt-2 text-white/70">Recipes automatically adapt to your diet and location.</p>
            </div>
            <div className="inline-flex items-center gap-2 rounded-full px-3 py-1 text-xs text-white/75 ring-1 ring-white/10" style={{ backgroundColor: 'rgba(255,255,255,0.05)' }}>
              <span className="h-2 w-2 rounded-full" style={{ backgroundColor: COLORS.secondary }} />
              Before → After
            </div>
          </div>

          <div className="mt-7 grid lg:grid-cols-2 gap-5">
            <div className="rounded-2xl p-5 ring-1 ring-white/10" style={{ backgroundColor: 'rgba(17,17,17,0.55)' }}>
              <div className="text-xs font-semibold text-white/70 uppercase tracking-wide">Original</div>
              <ul className="mt-4 space-y-2 text-sm text-white/80">
                {['Sour cream', 'All-purpose flour', 'Pancetta'].map((x) => (
                  <li key={x} className="flex items-center justify-between rounded-xl px-3 py-2 ring-1 ring-white/10" style={{ backgroundColor: 'rgba(255,255,255,0.04)' }}>
                    <span>{x}</span><span className="text-white/40">—</span>
                  </li>
                ))}
              </ul>
            </div>
            <div className="rounded-2xl p-5 ring-1 ring-white/10" style={{ backgroundColor: 'rgba(17,17,17,0.55)' }}>
              <div className="text-xs font-semibold text-white/70 uppercase tracking-wide">Adapted</div>
              <ul className="mt-4 space-y-2 text-sm text-white/80">
                {[
                  ['Greek yogurt', '✓'],
                  ['Gluten-free flour', '✓'],
                  ['Smoked turkey', '✓'],
                ].map(([x, mark]) => (
                  <li key={x} className="flex items-center justify-between rounded-xl px-3 py-2 ring-1 ring-white/10" style={{ backgroundColor: 'rgba(255,255,255,0.04)' }}>
                    <span>{x}</span><span className="font-semibold" style={{ color: COLORS.secondary }}>{mark}</span>
                  </li>
                ))}
              </ul>
            </div>
          </div>

          <p className="mt-5 text-xs text-white/55">“Most recipes weren’t written for your kitchen.” Now they are.</p>
        </div>
      </section>

      {/* Who it's for */}
      <section className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 mt-16 sm:mt-24">
        <div className="max-w-2xl">
          <h2 className="text-2xl sm:text-3xl font-extrabold tracking-tight">Who It’s For</h2>
          <p className="mt-3 text-white/70">Built for real life cooking—fast, healthy, and flexible.</p>
        </div>
        <div className="mt-8 grid md:grid-cols-3 gap-5">
          {[
            ['🍲', 'Home cooks', 'Keep all your favorite recipes organized in one place.'],
            ['🥦', 'Diet restricted', 'Convert recipes to match your diet without guesswork.'],
            ['👨‍👩‍👧', 'Parents', 'Make meals healthier and kid-friendly with smart swaps.'],
          ].map(([icon, title, body]) => (
            <div key={title} className="rounded-2xl p-6 ring-1 ring-white/10 shadow-soft hover:shadow-soft2 transition" style={{ backgroundColor: COLORS.card }}>
              <div className="text-lg font-semibold flex items-center gap-2">{icon} {title}</div>
              <p className="mt-2 text-sm text-white/70">{body}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Pricing */}
      <section id="pricing" className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 mt-16 sm:mt-24">
        <div className="max-w-2xl">
          <h2 className="text-2xl sm:text-3xl font-extrabold tracking-tight">Pricing</h2>
          <p className="mt-3 text-white/70">Start free. Upgrade when you want unlimited AI features.</p>
        </div>

        <div className="mt-8 grid lg:grid-cols-2 gap-5">
          <div className="rounded-2xl p-7 ring-1 ring-white/10 shadow-soft hover:shadow-soft2 transition" style={{ backgroundColor: COLORS.card }}>
            <div className="flex items-center justify-between">
              <div>
                <div className="text-lg font-bold">Free</div>
                <div className="mt-1 text-sm text-white/70">Perfect to try it out</div>
              </div>
              <div className="text-2xl font-extrabold">$0</div>
            </div>
            <ul className="mt-6 space-y-3 text-sm text-white/75">
              <li className="flex items-start gap-2"><span style={{ color: COLORS.accent }}>✓</span> Save recipes</li>
              <li className="flex items-start gap-2"><span style={{ color: COLORS.accent }}>✓</span> <span className="text-white font-semibold">5 AI adaptations</span></li>
              <li className="flex items-start gap-2"><span style={{ color: COLORS.accent }}>✓</span> Unified shopping list</li>
            </ul>
            <Link
              to="/login?tab=register"
              className="mt-7 inline-flex w-full items-center justify-center rounded-xl px-5 py-3 text-sm font-extrabold text-black shadow-soft transition hover:opacity-95"
              style={{ backgroundColor: COLORS.accent }}
            >
              Start Free
            </Link>
            <p className="mt-3 text-xs text-white/55 text-center">No credit card required.</p>
          </div>

          <div className="relative overflow-hidden rounded-2xl p-7 ring-1 ring-white/10 shadow-soft hover:shadow-soft2 transition" style={{ backgroundColor: COLORS.card }}>
            <div className="absolute -top-24 -right-24 h-64 w-64 rounded-full blur-3xl" style={{ backgroundColor: COLORS.secondary, opacity: 0.18 }} />
            <div className="relative flex items-center justify-between">
              <div>
                <div className="inline-flex items-center gap-2">
                  <div className="text-lg font-bold">Pro</div>
                  <span className="rounded-full px-2 py-0.5 text-xs font-semibold ring-1" style={{ backgroundColor: 'rgba(201,106,74,0.18)', color: COLORS.secondary, borderColor: 'rgba(201,106,74,0.35)' }}>
                    Unlimited
                  </span>
                </div>
                <div className="mt-1 text-sm text-white/70">For power users and families</div>
              </div>
              <div className="text-2xl font-extrabold">∞</div>
            </div>
            <ul className="relative mt-6 space-y-3 text-sm text-white/75">
              <li className="flex items-start gap-2"><span style={{ color: COLORS.secondary }}>✓</span> Unlimited AI adaptations</li>
              <li className="flex items-start gap-2"><span style={{ color: COLORS.secondary }}>✓</span> Advanced ingredient substitutions</li>
              <li className="flex items-start gap-2"><span style={{ color: COLORS.secondary }}>✓</span> Faster AI processing</li>
            </ul>
            <Link
              to="/login?tab=register"
              className="relative mt-7 inline-flex w-full items-center justify-center rounded-xl px-5 py-3 text-sm font-extrabold ring-1 ring-white/10 hover:bg-white/10 transition"
              style={{ backgroundColor: 'rgba(255,255,255,0.05)' }}
            >
              Upgrade to Pro
            </Link>
            <p className="mt-3 text-xs text-white/55 text-center">Cancel anytime.</p>
          </div>
        </div>
      </section>

      {/* Final CTA */}
      <section className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 mt-16 sm:mt-24 pb-16 sm:pb-24">
        <div
          className="rounded-2xl p-7 sm:p-10 ring-1 ring-white/10 shadow-soft"
          style={{ background: `linear-gradient(90deg, rgba(143,175,143,0.16), rgba(28,28,28,1), rgba(201,106,74,0.16))` }}
        >
          <div className="grid lg:grid-cols-2 gap-8 items-center">
            <div>
              <h2 className="text-2xl sm:text-3xl font-extrabold tracking-tight">Build Your Personal Recipe Book</h2>
              <p className="mt-3 text-white/70">Stop fighting recipes that don’t work for your kitchen.</p>
              <p className="mt-2 text-xs text-white/60">No credit card required.</p>
            </div>
            <div className="flex flex-col sm:flex-row gap-3 sm:justify-end">
              <Link
                to="/login?tab=register"
                className="inline-flex items-center justify-center rounded-xl px-5 py-3 text-sm font-extrabold text-black shadow-soft transition hover:opacity-95"
                style={{ backgroundColor: COLORS.accent }}
              >
                Start Free
              </Link>
              <Link
                to="/login"
                className="inline-flex items-center justify-center rounded-xl px-5 py-3 text-sm font-semibold ring-1 ring-white/10 hover:bg-white/10 transition"
                style={{ backgroundColor: 'rgba(255,255,255,0.05)' }}
              >
                Sign In
              </Link>
            </div>
          </div>
          <div className="mt-6 text-xs text-white/55">
            Credits: Free includes 5 AI adaptations. Some AI actions use credits, clearly marked. Pro includes unlimited AI features.
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-white/5 bg-black/40">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 py-10">
          <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-6">
            <div className="flex items-center gap-2">
              <span className="inline-flex h-9 w-9 items-center justify-center rounded-xl ring-1 ring-white/10" style={{ backgroundColor: 'rgba(255,255,255,0.05)' }}>
                🍽️
              </span>
              <div>
                <div className="font-extrabold">
                  myrecipes<span style={{ color: COLORS.accent }}>.cloud</span>
                </div>
                <div className="text-xs text-white/55">AI recipe adaptation for real kitchens.</div>
              </div>
            </div>
            <div className="flex flex-wrap gap-x-6 gap-y-2 text-sm text-white/70">
              <a href="#features" className="hover:text-white transition-colors">Features</a>
              <a href="#pricing" className="hover:text-white transition-colors">Pricing</a>
              <a href="#privacy" className="hover:text-white transition-colors">Privacy</a>
              <a href="#contact" className="hover:text-white transition-colors">Contact</a>
            </div>
          </div>
          <div className="mt-8 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 text-xs text-white/55">
            <div id="privacy">Privacy: we don’t sell your data or recipes.</div>
            <div id="contact">Contact: tshprung@gmail.com</div>
          </div>
          <div className="mt-6 text-xs text-white/45">© {year} myrecipes.cloud. All rights reserved.</div>
        </div>
      </footer>
    </div>
  )
}

