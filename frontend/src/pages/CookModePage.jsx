import { useEffect, useMemo, useRef, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { api } from '../api/client'
import { useLanguage } from '../context/LanguageContext'

const IS_TEST = typeof import.meta !== 'undefined'
  && import.meta.env
  && import.meta.env.MODE === 'test'

function formatRemaining(totalSec) {
  const sec = Math.max(0, Math.floor(totalSec))
  const m = Math.floor(sec / 60)
  const s = sec % 60
  return `${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`
}

export default function CookModePage() {
  const { id } = useParams()
  const navigate = useNavigate()
  const { t, lang } = useLanguage()

  const [recipe, setRecipe] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [stepIndex, setStepIndex] = useState(0)
  const [finished, setFinished] = useState(false)
  const [timerMinutes, setTimerMinutes] = useState('5')
  const [activeTimers, setActiveTimers] = useState({})
  const [nowMs, setNowMs] = useState(Date.now())

  const [voiceSupported, setVoiceSupported] = useState(false)
  const [voiceListening, setVoiceListening] = useState(false)
  const [voiceEnabled, setVoiceEnabled] = useState(true)
  const [voiceStatus, setVoiceStatus] = useState('off') // off | listening | unavailable | error

  const recognitionRef = useRef(null)
  const keepListeningRef = useRef(false)
  const stepIndexRef = useRef(0)
  const stepsRef = useRef([])
  const currentTimerRef = useRef(null)

  const voiceEnabledRef = useRef(true)
  const voiceStatusRef = useRef('off')

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    setError('')

    api.get(`/recipes/${id}`)
      .then((data) => {
        if (cancelled) return
        setRecipe(data)
        setStepIndex(0)
        setFinished(false)
      })
      .catch((err) => {
        if (cancelled) return
        setError(err?.message || t('recipeNotFound'))
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })

    return () => { cancelled = true }
  }, [id, t])

  useEffect(() => {
    stepIndexRef.current = stepIndex
  }, [stepIndex])

  useEffect(() => {
    stepsRef.current = recipe?.steps_pl ?? []
  }, [recipe])

  useEffect(() => {
    const hasRunning = Object.values(activeTimers).some(timer => timer.status === 'running')
    if (!hasRunning) return

    const handle = setInterval(() => setNowMs(Date.now()), 1000)
    return () => clearInterval(handle)
  }, [activeTimers])

  useEffect(() => {
    const onKeyDown = (e) => {
      if (loading || finished) return
      if (e.key === 'ArrowRight') handleNext()
      if (e.key === 'ArrowLeft') handleBack()
      if (e.key === 'Escape') handleExit()
    }
    window.addEventListener('keydown', onKeyDown)
    return () => window.removeEventListener('keydown', onKeyDown)
  }, [loading, finished, id])

  const steps = recipe?.steps_pl ?? []
  const hasSteps = steps.length > 0
  const currentStep = hasSteps ? steps[stepIndex] : ''

  const timersList = useMemo(() => {
    return Object.entries(activeTimers)
      .map(([stepKey, timer]) => {
        let remaining = timer.remainingSec
        if (timer.status === 'running') {
          remaining = Math.max(0, Math.ceil((timer.endAt - nowMs) / 1000))
        }
        return { stepKey, ...timer, remainingSec: remaining }
      })
      .sort((a, b) => Number(a.stepKey) - Number(b.stepKey))
  }, [activeTimers, nowMs])

  useEffect(() => {
    const updates = {}
    for (const timer of timersList) {
      if (timer.status === 'running' && timer.remainingSec <= 0) {
        updates[timer.stepKey] = {
          ...timer,
          status: 'done',
          remainingSec: 0,
          endAt: null,
        }
      }
    }
    if (Object.keys(updates).length > 0) {
      setActiveTimers(prev => ({ ...prev, ...updates }))
    }
  }, [timersList])

  function speakText(text) {
    try {
      const synth = typeof window !== 'undefined' ? window.speechSynthesis : null
      const Utterance = typeof window !== 'undefined' ? window.SpeechSynthesisUtterance : null
      if (!synth || !Utterance) return false

      synth.cancel()
      const u = new Utterance(text)
      if (lang) u.lang = lang
      u.rate = 1
      u.pitch = 1
      synth.speak(u)
      return true
    } catch (_) {
      return false
    }
  }

  function speakCurrentStep() {
    const stepsNow = stepsRef.current
    const idx = stepIndexRef.current
    const step = stepsNow?.[idx]
    if (!step) return
    speakText(step)
  }

  function normalizeTranscript(s) {
    return String(s || '')
      .trim()
      .toLowerCase()
      .replace(/[.,!?;:]/g, '')
      .replace(/\s+/g, ' ')
  }

  function parseHelperCommand(transcript) {
    const txt = normalizeTranscript(transcript)
    if (!txt) return null
    if (!txt.startsWith('helper ')) return null
    const rest = txt.slice('helper '.length).trim()
    if (!rest) return null
    const first = rest.split(' ')[0]
    if (first === 'next') return { type: 'next' }
    if (first === 'back' || first === 'previous' || first === 'prev') return { type: 'back' }
    if (first === 'pause') return { type: 'pause' }
    if (first === 'repeat' || first === 'again') return { type: 'repeat' }
    return null
  }

  function applyVoiceCommand(cmd) {
    if (!cmd) return
    const stepsNow = stepsRef.current
    const idx = stepIndexRef.current

    if (cmd.type === 'next') {
      if (idx >= stepsNow.length - 1) return
      setStepIndex(i => Math.min(stepsNow.length - 1, i + 1))
      return
    }
    if (cmd.type === 'back') {
      if (idx <= 0) return
      setStepIndex(i => Math.max(0, i - 1))
      return
    }
    if (cmd.type === 'pause') {
      const timer = currentTimerRef.current
      if (!timer || timer.status !== 'running') return
      handlePauseTimer(idx)
      return
    }
    if (cmd.type === 'repeat') {
      speakCurrentStep()
    }
  }

  function stopRecognition() {
    keepListeningRef.current = false
    try {
      recognitionRef.current?.stop?.()
    } catch (_) {}
    setVoiceListening(false)
    setVoiceStatus(voiceSupported ? 'off' : 'unavailable')
  }

  function startRecognition() {
    if (!voiceSupported) {
      setVoiceStatus('unavailable')
      return
    }
    keepListeningRef.current = true
    try {
      recognitionRef.current?.start?.()
      setVoiceListening(true)
      setVoiceStatus('listening')
    } catch (_) {
      // start() can throw if called too quickly or without permission; keep UI safe.
      setVoiceListening(false)
      setVoiceStatus('error')
    }
  }

  useEffect(() => {
    voiceEnabledRef.current = voiceEnabled
    voiceStatusRef.current = voiceStatus
  }, [voiceEnabled, voiceStatus])

  useEffect(() => {
    const SR = typeof window !== 'undefined'
      ? (window.SpeechRecognition || window.webkitSpeechRecognition)
      : null
    const supported = Boolean(SR)
    setVoiceSupported(supported)

    if (!supported) {
      setVoiceStatus('unavailable')
      return
    }

    const rec = new SR()
    rec.continuous = true
    rec.interimResults = false
    if (lang) rec.lang = lang

    rec.onresult = (event) => {
      try {
        for (let i = event.resultIndex; i < event.results.length; i++) {
          const res = event.results[i]
          if (!res.isFinal) continue
          const transcript = res[0]?.transcript ?? ''
          const cmd = parseHelperCommand(transcript)
          if (cmd) applyVoiceCommand(cmd)
        }
      } catch (_) {}
    }

    rec.onerror = () => {
      if (!keepListeningRef.current) return
      setVoiceStatus('error')
      setVoiceListening(false)
    }

    rec.onend = () => {
      if (!keepListeningRef.current) return
      if (IS_TEST) return
      // Try to keep hands-free mode alive.
      try {
        rec.start()
        setVoiceListening(true)
        setVoiceStatus('listening')
      } catch (_) {
        setVoiceListening(false)
        setVoiceStatus('error')
      }
    }

    recognitionRef.current = rec

    // Auto-start if enabled (hands-free).
    if (!IS_TEST && voiceEnabledRef.current) startRecognition()
    else setVoiceStatus('off')

    return () => {
      keepListeningRef.current = false
      try { rec.stop() } catch (_) {}
      recognitionRef.current = null
    }
  }, [lang])

  useEffect(() => {
    if (IS_TEST) return
    if (!voiceSupported) {
      setVoiceStatus('unavailable')
      return
    }
    if (voiceEnabled) startRecognition()
    else stopRecognition()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [voiceEnabled])

  useEffect(() => {
    // Auto-read on step changes.
    if (loading || finished) return
    speakCurrentStep()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [stepIndex, loading, finished])

  useEffect(() => {
    // Cleanup TTS when leaving Cook Mode.
    return () => {
      try { window.speechSynthesis?.cancel?.() } catch (_) {}
    }
  }, [])

  function handleExit() {
    stopRecognition()
    navigate(`/recipes/${id}`)
  }

  function handleBack() {
    setStepIndex(i => Math.max(0, i - 1))
  }

  function handleNext() {
    setStepIndex(i => Math.min(steps.length - 1, i + 1))
  }

  function handleFinishCooking() {
    stopRecognition()
    setFinished(true)
  }

  function handleStartTimer() {
    const mins = Number(timerMinutes)
    if (!Number.isFinite(mins) || mins <= 0 || mins > 180) return
    const totalSec = Math.round(mins * 60)
    setActiveTimers(prev => ({
      ...prev,
      [stepIndex]: {
        stepIndex,
        durationSec: totalSec,
        remainingSec: totalSec,
        endAt: Date.now() + totalSec * 1000,
        status: 'running',
      },
    }))
  }

  function handlePauseTimer(key) {
    setActiveTimers(prev => {
      const timer = prev[key]
      if (!timer || timer.status !== 'running') return prev
      const remainingSec = Math.max(0, Math.ceil((timer.endAt - Date.now()) / 1000))
      return {
        ...prev,
        [key]: {
          ...timer,
          remainingSec,
          endAt: null,
          status: 'paused',
        },
      }
    })
  }

  function handleResumeTimer(key) {
    setActiveTimers(prev => {
      const timer = prev[key]
      if (!timer || timer.status !== 'paused') return prev
      return {
        ...prev,
        [key]: {
          ...timer,
          endAt: Date.now() + timer.remainingSec * 1000,
          status: 'running',
        },
      }
    })
  }

  function handleCancelTimer(key) {
    setActiveTimers(prev => {
      const next = { ...prev }
      delete next[key]
      return next
    })
  }

  if (loading) {
    return (
      <div className="min-h-[60vh] flex items-center justify-center">
        <div className="flex items-center gap-3 text-stone-200">
          <span className="w-6 h-6 border-2 border-amber-300 border-t-transparent rounded-full animate-spin" />
          <span>{t('loading')}</span>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="max-w-xl mx-auto py-16 text-center">
        <p className="text-red-300 mb-4">{error}</p>
        <button
          type="button"
          onClick={handleExit}
          className="px-4 py-2 rounded-xl bg-white/10 hover:bg-white/20 text-white"
        >
          {t('backToRecipe')}
        </button>
      </div>
    )
  }

  if (!hasSteps) {
    return (
      <div className="max-w-xl mx-auto py-16 text-center">
        <p className="text-stone-200 mb-4">{t('noStepsToCook')}</p>
        <button
          type="button"
          onClick={handleExit}
          className="px-4 py-2 rounded-xl bg-amber-500 hover:bg-amber-600 text-white font-semibold"
        >
          {t('backToRecipe')}
        </button>
      </div>
    )
  }

  if (finished) {
    return (
      <div className="min-h-[75vh] flex items-center justify-center px-4">
        <div className="w-full max-w-xl rounded-2xl border border-white/15 bg-white/5 p-8 text-center">
          <h1 className="text-3xl font-bold text-white mb-3">{t('finishCooking')}</h1>
          <p className="text-stone-200 mb-6">{recipe?.title_pl}</p>
          <button
            type="button"
            onClick={handleExit}
            className="px-5 py-3 rounded-xl bg-amber-500 hover:bg-amber-600 text-white font-semibold"
          >
            {t('backToRecipe')}
          </button>
        </div>
      </div>
    )
  }

  const currentTimer = activeTimers[stepIndex]
  currentTimerRef.current = currentTimer
  const currentTimerRemainingSec = currentTimer?.status === 'running'
    ? Math.max(0, Math.ceil((currentTimer.endAt - nowMs) / 1000))
    : currentTimer?.remainingSec ?? null

  return (
    <div className="fixed inset-0 z-40 bg-[#111111] text-stone-50 flex flex-col">
      <header className="px-4 sm:px-6 py-4 border-b border-white/10 flex items-start justify-between gap-4">
        <div className="min-w-0">
          <h1 className="text-lg sm:text-xl font-bold truncate">{recipe?.title_pl}</h1>
          <p className="text-sm text-stone-300 mt-1">
            {t('step')} {stepIndex + 1} {t('of')} {steps.length}
          </p>
          <div className="mt-2 flex flex-wrap items-center gap-2">
            <span className="text-xs px-2 py-1 rounded-full bg-white/10 border border-white/10 text-stone-200">
              {voiceStatus === 'listening'
                ? t('voiceListening')
                : voiceStatus === 'unavailable'
                  ? t('voiceUnavailable')
                  : voiceStatus === 'error'
                    ? t('voiceError')
                    : t('voiceOff')}
            </span>
            {voiceSupported && (
              <button
                type="button"
                onClick={() => setVoiceEnabled(v => !v)}
                className="text-xs px-2 py-1 rounded-full bg-white/5 hover:bg-white/10 border border-white/10 text-stone-200"
              >
                {voiceEnabled ? t('voiceOn') : t('voiceOff')}
              </button>
            )}
          </div>
        </div>
        <button
          type="button"
          onClick={handleExit}
          className="px-3 py-2 rounded-xl border border-white/20 hover:bg-white/10 text-sm"
        >
          {t('exitCooking')}
        </button>
      </header>

      <main className="flex-1 overflow-y-auto px-4 sm:px-6 py-6">
        <section className="max-w-3xl mx-auto">
          <div className="rounded-2xl border border-white/10 bg-white/5 p-6 sm:p-8">
            <p className="text-lg sm:text-2xl leading-relaxed">{currentStep}</p>
            <div className="mt-4 flex flex-wrap items-center gap-2">
              <button
                type="button"
                onClick={speakCurrentStep}
                className="px-3 py-2 rounded-lg bg-white/10 hover:bg-white/20 border border-white/10 text-sm font-semibold"
              >
                {t('readStep')}
              </button>
              <p className="text-xs text-stone-300">
                {t('voiceCommandsHint')}
              </p>
            </div>
          </div>

          <div className="mt-6 rounded-2xl border border-white/10 bg-white/5 p-4">
            <h2 className="font-semibold mb-3">{t('startTimer')}</h2>
            <div className="flex flex-wrap items-center gap-2">
              <input
                type="number"
                min="1"
                max="180"
                value={timerMinutes}
                onChange={(e) => setTimerMinutes(e.target.value)}
                className="w-24 px-3 py-2 rounded-lg bg-black/30 border border-white/20"
                aria-label={t('timerMinutes')}
              />
              <span className="text-sm text-stone-300">{t('timerMinutes')}</span>
              <button
                type="button"
                onClick={handleStartTimer}
                className="px-3 py-2 rounded-lg bg-amber-500 hover:bg-amber-600 text-white font-semibold"
              >
                {t('startTimer')}
              </button>
              {currentTimer?.status === 'running' && (
                <button
                  type="button"
                  onClick={() => handlePauseTimer(stepIndex)}
                  className="px-3 py-2 rounded-lg border border-white/20 hover:bg-white/10"
                >
                  {t('pauseTimer')}
                </button>
              )}
              {currentTimer?.status === 'paused' && (
                <button
                  type="button"
                  onClick={() => handleResumeTimer(stepIndex)}
                  className="px-3 py-2 rounded-lg border border-white/20 hover:bg-white/10"
                >
                  {t('resumeTimer')}
                </button>
              )}
              {currentTimer && (
                <button
                  type="button"
                  onClick={() => handleCancelTimer(stepIndex)}
                  className="px-3 py-2 rounded-lg border border-white/20 hover:bg-white/10"
                >
                  {t('cancelTimer')}
                </button>
              )}
            </div>
            {currentTimer && (
              <p className="mt-3 text-sm text-stone-200" aria-live="polite">
                {t('currentStepTimer')}: <span className="font-mono">{formatRemaining(currentTimerRemainingSec ?? 0)}</span>
              </p>
            )}
          </div>

          {timersList.length > 0 && (
            <div className="mt-4 rounded-2xl border border-white/10 bg-white/5 p-4">
              <h3 className="font-semibold mb-3">{t('timers')}</h3>
              <ul className="space-y-2">
                {timersList.map((timer) => (
                  <li key={timer.stepKey} className="flex items-center justify-between gap-2 text-sm">
                    <span>
                      {t('step')} {Number(timer.stepKey) + 1}
                    </span>
                    <span className="font-mono">{formatRemaining(timer.remainingSec)}</span>
                    <span className="text-stone-300">
                      {timer.status === 'done'
                        ? t('timerDone')
                        : timer.status === 'running'
                          ? t('timerRunning')
                          : t('timerPaused')}
                    </span>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </section>
      </main>

      <footer className="px-4 sm:px-6 py-4 pb-[calc(1rem+env(safe-area-inset-bottom))] border-t border-white/10 bg-[#111111]">
        <div className="max-w-3xl mx-auto flex items-center justify-between gap-3">
          <button
            type="button"
            onClick={handleBack}
            disabled={stepIndex === 0}
            className="flex-1 sm:flex-none px-4 py-3 rounded-xl border border-white/20 hover:bg-white/10 disabled:opacity-40 disabled:cursor-not-allowed"
          >
            {t('back')}
          </button>
          {stepIndex < steps.length - 1 ? (
            <button
              type="button"
              onClick={handleNext}
              className="flex-1 sm:flex-none px-5 py-3 rounded-xl bg-amber-500 hover:bg-amber-600 text-white font-semibold"
            >
              {t('next')}
            </button>
          ) : (
            <button
              type="button"
              onClick={handleFinishCooking}
              className="flex-1 sm:flex-none px-5 py-3 rounded-xl bg-emerald-600 hover:bg-emerald-700 text-white font-semibold"
            >
              {t('finishCooking')}
            </button>
          )}
        </div>
      </footer>
    </div>
  )
}
