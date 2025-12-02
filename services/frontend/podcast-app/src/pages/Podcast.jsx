import { useState, useRef, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { ArrowLeft, Menu, Phone, PhoneOff, Mic, MicOff, Settings as SettingsIcon, Info, Sparkles, Sliders, Clock, Play, Pause } from 'lucide-react'
import { motion, AnimatePresence } from 'framer-motion'
import AnimatedOrb from '../components/AnimatedOrb'
import OrbSelector, { OrbStyle1, OrbStyle2, OrbStyle3, OrbStyle4, OrbStyle5, OrbStyle6, OrbStyle7, OrbStyle8, OrbStyle9, OrbStyle10 } from '../components/OrbSelector'

function Podcast() {
  const navigate = useNavigate()

  // ========== DAILY BRIEF STATE ==========
  const [dailyBrief, setDailyBrief] = useState(null)
  const [isGeneratingBrief, setIsGeneratingBrief] = useState(false)
  const [briefAudioPlaying, setBriefAudioPlaying] = useState(false)
  const [briefAudioProgress, setBriefAudioProgress] = useState(0)
  const [briefAudioDuration, setBriefAudioDuration] = useState(0)
  const [userTopics, setUserTopics] = useState([])
  const [userSources, setUserSources] = useState([])
  const briefAudioRef = useRef(null)

  // ========== Q&A STATE (EXISTING) ==========
  const [isRecording, setIsRecording] = useState(false)
  const [isPlaying, setIsPlaying] = useState(false)
  const [statusMessage, setStatusMessage] = useState("Go ahead, I'm listening")
  const [menuOpen, setMenuOpen] = useState(false)
  const [showOrbSelector, setShowOrbSelector] = useState(false)
  const [selectedOrb, setSelectedOrb] = useState(1)

  // WebSocket and audio refs (EXISTING)
  const wsRef = useRef(null)
  const audioContextRef = useRef(null)
  const mediaStreamRef = useRef(null)
  const processorRef = useRef(null)
  const audioBufferRef = useRef([])
  const audioPlayerRef = useRef(null)
  const isStreamingAudioRef = useRef(false)
  const isRecordingRef = useRef(false)
  const currentAudioUrlRef = useRef(null)
  const preventAutoPlayRef = useRef(false)

  // ========== API HELPER ==========
  const getApiUrl = () => {
    const isProduction = window.location.hostname.includes('newsjuiceapp.com')
    return isProduction
      ? 'https://chatter-919568151211.us-central1.run.app'
      : 'http://localhost:8080'
  }

  const getAuthHeaders = () => {
    const token = localStorage.getItem('auth_token')
    return {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json'
    }
  }

  // ========== DAILY BRIEF FUNCTIONS ==========

  // Load user preferences (topics and sources)
  const loadUserPreferences = async () => {
    try {
      const response = await fetch(`${getApiUrl()}/api/user/preferences`, {
        headers: getAuthHeaders()
      })

      if (!response.ok) {
        console.error('[preferences] Failed to load:', response.status)
        return
      }

      const data = await response.json()
      console.log('[preferences] Loaded:', data)

      // Parse JSON arrays from preference_value strings
      const topics = data.topics ? JSON.parse(data.topics) : []
      const sources = data.sources ? JSON.parse(data.sources) : []

      setUserTopics(topics)
      setUserSources(sources)
    } catch (error) {
      console.error('[preferences] Error loading:', error)
    }
  }

  // Check if daily brief was generated today
  const checkDailyBriefStatus = async () => {
    try {
      const response = await fetch(`${getApiUrl()}/api/daily-brief/status`, {
        headers: getAuthHeaders()
      })

      if (!response.ok) {
        console.error('[daily-brief] Status check failed:', response.status)
        return false
      }

      const data = await response.json()
      return data.generated_today
    } catch (error) {
      console.error('[daily-brief] Error checking status:', error)
      return false
    }
  }

  // Load latest daily brief from history
  const loadLatestDailyBrief = async () => {
    try {
      const response = await fetch(`${getApiUrl()}/api/daily-brief/latest`, {
        headers: getAuthHeaders()
      })

      if (!response.ok) {
        console.error('[daily-brief] Failed to load latest:', response.status)
        return null
      }

      const data = await response.json()
      console.log('[daily-brief] Loaded latest:', data)
      return data
    } catch (error) {
      console.error('[daily-brief] Error loading latest:', error)
      return null
    }
  }

  // Generate new daily brief
  const generateDailyBrief = async () => {
    setIsGeneratingBrief(true)

    try {
      console.log('[daily-brief] Generating...')

      const response = await fetch(`${getApiUrl()}/api/daily-brief`, {
        method: 'POST',
        headers: getAuthHeaders()
      })

      if (!response.ok) {
        console.error('[daily-brief] Generation failed:', response.status)
        setIsGeneratingBrief(false)
        return
      }

      const data = await response.json()
      console.log('[daily-brief] Generated:', data)

      setDailyBrief(data)
      setIsGeneratingBrief(false)
    } catch (error) {
      console.error('[daily-brief] Error generating:', error)
      setIsGeneratingBrief(false)
    }
  }

  // Check and auto-generate daily brief if needed
  const checkAndGenerateDailyBrief = async () => {
    console.log('[daily-brief] Checking if generation needed...')

    const generatedToday = await checkDailyBriefStatus()

    if (generatedToday) {
      console.log('[daily-brief] Already generated today, loading latest...')
      const latest = await loadLatestDailyBrief()
      if (latest) {
        setDailyBrief(latest)
      }
    } else {
      console.log('[daily-brief] Not generated today, auto-generating...')
      await generateDailyBrief()
    }
  }

  // Play daily brief audio
  const playDailyBrief = () => {
    if (!dailyBrief || !dailyBrief.audio_url) {
      console.warn('[daily-brief] No audio URL available')
      return
    }

    if (!briefAudioRef.current) {
      briefAudioRef.current = new Audio(dailyBrief.audio_url)

      // Update progress
      briefAudioRef.current.ontimeupdate = () => {
        setBriefAudioProgress(briefAudioRef.current.currentTime)
        setBriefAudioDuration(briefAudioRef.current.duration)
      }

      // Reset on end
      briefAudioRef.current.onended = () => {
        setBriefAudioPlaying(false)
        setBriefAudioProgress(0)
      }
    }

    if (briefAudioPlaying) {
      briefAudioRef.current.pause()
      setBriefAudioPlaying(false)
    } else {
      briefAudioRef.current.play()
      setBriefAudioPlaying(true)
    }
  }

  // Format date for display
  const formatDate = (timestamp) => {
    if (!timestamp) return ''

    const date = new Date(timestamp)
    const options = { weekday: 'long', month: 'long', day: 'numeric', year: 'numeric' }
    return date.toLocaleDateString('en-US', options)
  }

  // Format time for audio player (MM:SS)
  const formatTime = (seconds) => {
    if (isNaN(seconds)) return '0:00'
    const mins = Math.floor(seconds / 60)
    const secs = Math.floor(seconds % 60)
    return `${mins}:${secs.toString().padStart(2, '0')}`
  }

  // ========== Q&A FUNCTIONS (EXISTING) ==========

  // WebSocket URL
  const getWebSocketUrl = () => {
    const isProduction = window.location.hostname.includes('newsjuiceapp.com')
    const protocol = isProduction ? 'wss' : 'ws'
    const host = isProduction
      ? 'chatter-919568151211.us-central1.run.app'
      : 'localhost:8080'
    const token = localStorage.getItem('auth_token')
    return `${protocol}://${host}/ws/chat${token ? `?token=${token}` : ''}`
  }

  // Connect WebSocket
  const connectWebSocket = () => {
    return new Promise((resolve, reject) => {
      const ws = new WebSocket(getWebSocketUrl())

      ws.onopen = () => {
        console.log("[ws] Connected")
        wsRef.current = ws
        resolve()
      }

      ws.onerror = (error) => {
        console.error("[ws] Error:", error)
        reject(error)
      }

      ws.onclose = () => {
        console.log("[ws] Disconnected")
        wsRef.current = null
      }

      ws.onmessage = async (event) => {
        if (event.data instanceof Blob) {
          handleAudioChunk(event.data)
        } else {
          try {
            const data = JSON.parse(event.data)
            handleStatusMessage(data)
          } catch (e) {
            console.error("[ws] Failed to parse message:", e)
          }
        }
      }
    })
  }

  // Handle status messages from backend
  const handleStatusMessage = (data) => {
    const status = data.status

    switch(status) {
      case "chunk_received":
        break
      case "transcribing":
        setStatusMessage("🎤 Transcribing your voice...")
        break
      case "transcribed":
        setStatusMessage(`✅ Transcribed: "${data.text}"`)
        break
      case "retrieving":
        setStatusMessage("🔍 Finding relevant news articles...")
        break
      case "generating":
        setStatusMessage("✨ Generating podcast response...")
        break
      case "podcast_generated":
        setStatusMessage("📝 Podcast text ready!")
        break
      case "converting_to_audio":
        setStatusMessage("🔊 Converting to audio...")
        break
      case "streaming_audio":
        setStatusMessage("📡 Receiving audio stream...")
        audioBufferRef.current = []
        isStreamingAudioRef.current = false
        break
      case "complete":
        setStatusMessage("✅ Complete! Playing podcast...")
        finalizeAudio()
        break
      case "error":
        setStatusMessage(`❌ Error: ${data.error}`)
        setIsRecording(false)
        break
      default:
        console.log("[ws] Status:", data)
    }
  }

  // Handle audio chunks from backend
  const handleAudioChunk = (chunk) => {
    if (!isStreamingAudioRef.current) {
      console.log("[audio] Starting to accumulate audio chunks")
      isStreamingAudioRef.current = true
    }

    audioBufferRef.current.push(chunk)
    console.log(`[audio] Accumulated ${audioBufferRef.current.length} chunks (${chunk.size} bytes)`)
  }

  // Finalize and play audio
  const finalizeAudio = () => {
    if (isRecordingRef.current || preventAutoPlayRef.current) {
      console.log("[audio] Skipping audio playback - recording in progress or auto-play prevented")
      audioBufferRef.current = []
      isStreamingAudioRef.current = false
      return
    }

    if (audioBufferRef.current.length === 0) {
      console.warn("[audio] No audio chunks to finalize")
      return
    }

    console.log(`[audio] Finalizing audio: ${audioBufferRef.current.length} chunks`)

    if (currentAudioUrlRef.current) {
      console.log("[audio] Revoking previous audio URL")
      URL.revokeObjectURL(currentAudioUrlRef.current)
      currentAudioUrlRef.current = null
    }

    const mimeTypes = ['audio/wav', 'audio/wave', 'audio/x-wav']

    for (const mimeType of mimeTypes) {
      try {
        const audioBlob = new Blob(audioBufferRef.current, { type: mimeType })
        const audioUrl = URL.createObjectURL(audioBlob)

        currentAudioUrlRef.current = audioUrl

        if (!audioPlayerRef.current) {
          audioPlayerRef.current = new Audio()
        }

        audioPlayerRef.current.src = audioUrl
        audioPlayerRef.current.oncanplay = () => {
          if (isRecordingRef.current || preventAutoPlayRef.current) {
            console.log("[audio] oncanplay - Skipping playback, recording active")
            return
          }
          console.log("[audio] Audio can play, attempting autoplay")
          setIsPlaying(true)
          audioPlayerRef.current.play().catch((err) => {
            console.warn("[audio] Autoplay blocked:", err)
          })
        }

        audioPlayerRef.current.onended = () => {
          setIsPlaying(false)
          setStatusMessage("Go ahead, I'm listening")
        }

        audioPlayerRef.current.onerror = (e) => {
          console.error(`[audio] Error playing audio with ${mimeType}:`, e)
        }

        break
      } catch (e) {
        console.warn(`[audio] Failed to create blob with ${mimeType}:`, e)
      }
    }

    audioBufferRef.current = []
    isStreamingAudioRef.current = false
  }

  // Start recording
  const startRecording = async () => {
    if (isRecording || isRecordingRef.current) {
      console.log("[recording] Already recording, ignoring start request")
      return
    }

    try {
      preventAutoPlayRef.current = true
      console.log("[recording] preventAutoPlay flag set to TRUE")

      if (isPlaying) {
        stopPlayback()
      }

      if (wsRef.current && wsRef.current.readyState !== WebSocket.OPEN) {
        console.log("[recording] WebSocket not open, closing and reconnecting...")
        wsRef.current.close()
        wsRef.current = null
      }

      if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) {
        setStatusMessage("Connecting...")
        await connectWebSocket()
      }

      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true,
          sampleRate: { ideal: 44100 },
          channelCount: { ideal: 1 }
        }
      })

      mediaStreamRef.current = stream

      const AudioContext = window.AudioContext || window.webkitAudioContext
      const audioContext = new AudioContext()
      audioContextRef.current = audioContext

      const source = audioContext.createMediaStreamSource(stream)

      const bufferSize = 4096
      const processor = audioContext.createScriptProcessor(bufferSize, 1, 1)

      processor.onaudioprocess = (e) => {
        if (!isRecordingRef.current || !wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) {
          return
        }

        const inputData = e.inputBuffer.getChannelData(0)
        const pcmData = new Int16Array(inputData.length)

        for (let i = 0; i < inputData.length; i++) {
          const sample = Math.max(-1, Math.min(1, inputData[i]))
          pcmData[i] = sample < 0 ? sample * 0x8000 : sample * 0x7FFF
        }

        try {
          wsRef.current.send(pcmData.buffer)
          console.log(`[recording] Sent audio chunk: ${pcmData.buffer.byteLength} bytes`)
        } catch (error) {
          console.error("[recording] Error sending audio chunk:", error)
        }
      }

      processorRef.current = processor
      source.connect(processor)
      processor.connect(audioContext.destination)

      isRecordingRef.current = true
      setIsRecording(true)
      setStatusMessage("Listening...")
      console.log("[recording] Started recording, audio processor active")
    } catch (error) {
      console.error('Error starting recording:', error)
      setStatusMessage("Error: " + error.message)
    }
  }

  // Stop recording
  const stopRecording = () => {
    console.log("[recording] Stopping recording...")

    isRecordingRef.current = false

    setTimeout(() => {
      preventAutoPlayRef.current = false
      console.log("[recording] preventAutoPlay flag reset to FALSE - next podcast can auto-play")
    }, 500)

    setTimeout(() => {
      if (processorRef.current) {
        processorRef.current.disconnect()
        processorRef.current = null
      }

      if (mediaStreamRef.current) {
        mediaStreamRef.current.getTracks().forEach(track => track.stop())
        mediaStreamRef.current = null
      }

      if (audioContextRef.current) {
        audioContextRef.current.close()
        audioContextRef.current = null
      }

      setIsRecording(false)

      if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
        console.log("[recording] Sending complete signal to backend")
        wsRef.current.send(JSON.stringify({ type: "complete" }))
        setStatusMessage("Processing...")
      } else {
        console.warn("[recording] WebSocket not ready (state:", wsRef.current?.readyState, "), cannot send complete signal")

        if (!wsRef.current || wsRef.current.readyState === WebSocket.CLOSED) {
          setStatusMessage("Go ahead, I'm listening")
        } else if (wsRef.current.readyState === WebSocket.CONNECTING) {
          setStatusMessage("Connecting...")
          const originalWs = wsRef.current

          originalWs.addEventListener('open', () => {
            if (wsRef.current === originalWs && originalWs.readyState === WebSocket.OPEN) {
              console.log("[recording] WebSocket opened after delay, sending complete signal")
              originalWs.send(JSON.stringify({ type: "complete" }))
              setStatusMessage("Processing...")
            }
          }, { once: true })
        }
      }
    }, 200)
  }

  // Stop playback
  const stopPlayback = () => {
    console.log("[playback] Stopping playback and cleaning up")

    if (audioPlayerRef.current) {
      audioPlayerRef.current.pause()
      audioPlayerRef.current.currentTime = 0
      audioPlayerRef.current.src = ''

      audioPlayerRef.current.onended = null
      audioPlayerRef.current.onerror = null
    }

    if (currentAudioUrlRef.current) {
      URL.revokeObjectURL(currentAudioUrlRef.current)
      currentAudioUrlRef.current = null
    }

    setIsPlaying(false)
    setStatusMessage("Go ahead, I'm listening")
  }

  // Handle call button
  const handleCallButton = () => {
    if (isRecording) {
      stopRecording()
    } else if (isPlaying) {
      stopPlayback()
      startRecording()
    } else {
      startRecording()
    }
  }

  // ========== LIFECYCLE ==========

  // Load preferences and daily brief on mount
  useEffect(() => {
    loadUserPreferences()
    checkAndGenerateDailyBrief()
  }, [])

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (wsRef.current) {
        wsRef.current.close()
      }
      if (processorRef.current) {
        processorRef.current.disconnect()
      }
      if (mediaStreamRef.current) {
        mediaStreamRef.current.getTracks().forEach(track => track.stop())
      }
      if (audioContextRef.current) {
        audioContextRef.current.close()
      }
      if (audioPlayerRef.current) {
        audioPlayerRef.current.pause()
      }
      if (briefAudioRef.current) {
        briefAudioRef.current.pause()
      }
    }
  }, [])

  // ========== UI HELPERS ==========

  const handleOrbSelection = (orbId) => {
    if (orbId !== null) {
      setSelectedOrb(orbId)
    }
    setShowOrbSelector(false)
  }

  const getOrbComponent = () => {
    const orbMap = {
      1: OrbStyle1, 2: OrbStyle2, 3: OrbStyle3, 4: OrbStyle4, 5: OrbStyle5,
      6: OrbStyle6, 7: OrbStyle7, 8: OrbStyle8, 9: OrbStyle9, 10: OrbStyle10,
    }
    return orbMap[selectedOrb] || OrbStyle1
  }

  const SelectedOrbComponent = getOrbComponent()

  // ========== RENDER ==========

  return (
    <div className="min-h-screen bg-primary-darker text-white relative overflow-hidden">
      {/* Background gradient */}
      <div className="absolute inset-0 bg-gradient-to-b from-primary-purple/20 via-primary-darker to-primary-darker"></div>

      {/* Header */}
      <div className="relative z-10 px-6 py-4 flex items-center justify-between">
        <button
          onClick={() => navigate('/login')}
          className="p-2 hover:bg-gray-800 rounded-full transition-colors"
        >
          <ArrowLeft size={24} />
        </button>
        <h1 className="text-lg font-semibold">AI Daily News Briefing</h1>
        <div className="flex items-center gap-2">
          <button
            onClick={() => navigate('/preferences')}
            className="p-2 hover:bg-gray-800 rounded-full transition-colors"
            title="Preferences"
          >
            <Sliders size={24} />
          </button>
          <button
            onClick={() => setMenuOpen(!menuOpen)}
            className="p-2 hover:bg-gray-800 rounded-full transition-colors"
          >
            <Menu size={24} />
          </button>
        </div>
      </div>

      {/* Hamburger Menu */}
      <AnimatePresence>
        {menuOpen && (
          <motion.div
            initial={{ x: '100%' }}
            animate={{ x: 0 }}
            exit={{ x: '100%' }}
            transition={{ type: 'tween', duration: 0.3 }}
            className="fixed top-0 right-0 h-full w-64 bg-primary-dark border-l border-gray-800 z-50 shadow-2xl"
          >
            <div className="p-6 space-y-6">
              <div className="flex justify-between items-center mb-8">
                <h2 className="text-xl font-bold">Menu</h2>
                <button
                  onClick={() => setMenuOpen(false)}
                  className="p-2 hover:bg-gray-800 rounded-full transition-colors"
                >
                  ✕
                </button>
              </div>
              <button
                onClick={() => {
                  navigate('/settings')
                  setMenuOpen(false)
                }}
                className="w-full flex items-center gap-3 p-3 hover:bg-gray-800 rounded-lg transition-colors"
              >
                <SettingsIcon size={20} />
                <span>Settings</span>
              </button>
              <button
                onClick={() => {
                  navigate('/about')
                  setMenuOpen(false)
                }}
                className="w-full flex items-center gap-3 p-3 hover:bg-gray-800 rounded-lg transition-colors"
              >
                <Info size={20} />
                <span>About Us</span>
              </button>
              <button
                onClick={() => {
                  localStorage.removeItem('auth_token')
                  localStorage.removeItem('user_id')
                  navigate('/login')
                  setMenuOpen(false)
                }}
                className="w-full flex items-center gap-3 p-3 hover:bg-red-900/30 text-red-400 rounded-lg transition-colors"
              >
                <ArrowLeft size={20} />
                <span>Logout</span>
              </button>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Main Content Container */}
      <div className="relative z-10 max-w-6xl mx-auto px-6 py-6 space-y-12">

        {/* ========== SECTION 1: DAILY BRIEFING (PRIMARY, TOP) ========== */}
        <section>
          <div className="bg-gradient-to-br from-red-900/30 to-red-800/20 rounded-3xl p-8 border border-red-800/50 shadow-2xl">
            {/* Date and Title */}
            <div className="mb-6">
              <div className="flex items-center gap-2 text-gray-300 mb-2">
                <Clock size={18} />
                <span className="text-sm">{formatDate(dailyBrief?.created_at || new Date().toISOString())}</span>
              </div>
              <h2 className="text-3xl font-bold">Daily News Briefing</h2>
            </div>

            {/* Topics */}
            {userTopics.length > 0 && (
              <div className="mb-6">
                <p className="text-sm text-gray-400 mb-3">Today's coverage:</p>
                <div className="flex flex-wrap gap-2">
                  {userTopics.map((topic, index) => (
                    <span
                      key={index}
                      className="px-4 py-2 bg-red-900/40 border border-red-700/50 rounded-full text-sm"
                    >
                      {topic}
                    </span>
                  ))}
                </div>
              </div>
            )}

            {/* Sources */}
            {userSources.length > 0 && (
              <div className="mb-6">
                <p className="text-sm text-gray-400 mb-3">Sources for today's briefing:</p>
                <div className="space-y-2">
                  {userSources.map((source, index) => (
                    <div
                      key={index}
                      className="flex items-center gap-3 px-4 py-2 bg-gray-800/30 rounded-lg border border-gray-700"
                    >
                      <span className="text-2xl">📰</span>
                      <div>
                        <p className="font-medium text-sm">{source}</p>
                        <p className="text-xs text-gray-500">
                          {source.toLowerCase().replace(/\s+/g, '')}.harvard.edu
                        </p>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Generate or Play */}
            {isGeneratingBrief ? (
              <div className="text-center py-8">
                <div className="inline-block animate-spin rounded-full h-12 w-12 border-4 border-gray-600 border-t-primary-pink mb-4"></div>
                <p className="text-gray-400">Generating your personalized briefing...</p>
              </div>
            ) : dailyBrief ? (
              <div className="space-y-4">
                {/* Play Button and Progress */}
                <div className="flex items-center gap-4">
                  <button
                    onClick={playDailyBrief}
                    className="w-16 h-16 bg-gradient-to-br from-primary-pink to-pink-600 rounded-full flex items-center justify-center shadow-lg hover:shadow-primary-pink/50 transition-all"
                  >
                    {briefAudioPlaying ? <Pause size={28} /> : <Play size={28} className="ml-1" />}
                  </button>
                  <div className="flex-1">
                    <div className="h-2 bg-gray-700 rounded-full overflow-hidden mb-2">
                      <div
                        className="h-full bg-gradient-to-r from-primary-pink to-pink-500 transition-all"
                        style={{ width: `${briefAudioDuration > 0 ? (briefAudioProgress / briefAudioDuration) * 100 : 0}%` }}
                      ></div>
                    </div>
                    <div className="flex justify-between text-xs text-gray-400">
                      <span>{formatTime(briefAudioProgress)}</span>
                      <span>{formatTime(briefAudioDuration)}</span>
                    </div>
                  </div>
                </div>

                <p className="text-center text-sm text-gray-400">
                  {briefAudioPlaying ? "Playing your briefing..." : "Click to play briefing"}
                </p>
              </div>
            ) : (
              <div className="text-center py-8">
                <p className="text-gray-400 mb-4">No daily brief available yet.</p>
                <button
                  onClick={generateDailyBrief}
                  className="px-8 py-3 bg-gradient-to-r from-primary-pink to-pink-500 rounded-full font-semibold hover:shadow-lg hover:shadow-primary-pink/50 transition-all"
                >
                  Generate Daily Brief
                </button>
              </div>
            )}

            {/* Preferences Prompt */}
            {userTopics.length === 0 && userSources.length === 0 && (
              <div className="mt-6 p-4 bg-yellow-900/20 border border-yellow-700/50 rounded-lg text-center">
                <p className="text-sm text-yellow-300 mb-2">
                  No preferences set yet! Configure your topics and sources to get personalized briefings.
                </p>
                <button
                  onClick={() => navigate('/preferences')}
                  className="text-sm text-primary-pink hover:underline"
                >
                  Set Preferences →
                </button>
              </div>
            )}
          </div>
        </section>

        {/* ========== DIVIDER ========== */}
        <div className="border-t border-gray-800"></div>

        {/* ========== SECTION 2: INTERACTIVE Q&A (SECONDARY, BELOW) ========== */}
        <section>
          <div className="text-center mb-8">
            <h2 className="text-2xl font-bold mb-2">Ask About Today's News</h2>
            <p className="text-gray-400">Click the microphone and speak your question</p>
          </div>

          {/* Two Column Layout: Orb on right, controls on left */}
          <div className="flex flex-col lg:flex-row lg:gap-12 items-center">

            {/* Left: Controls and Status */}
            <div className="w-full lg:w-1/2 flex flex-col items-center lg:items-start space-y-6">
              {/* Status Message */}
              <motion.div
                key={statusMessage}
                initial={{ opacity: 0, y: -10 }}
                animate={{ opacity: 1, y: 0 }}
                className="w-full px-6 py-3 bg-gray-800/50 rounded-full border border-gray-700 backdrop-blur-sm text-center"
              >
                <p className="text-sm text-gray-300">{statusMessage}</p>
              </motion.div>

              {/* Call Buttons */}
              <div className="flex items-center gap-6">
                <motion.button
                  whileTap={{ scale: 0.95 }}
                  className="w-16 h-16 bg-gray-800/50 hover:bg-red-900/50 rounded-full flex items-center justify-center border border-gray-700 hover:border-red-500 transition-all"
                >
                  <PhoneOff size={24} className="text-red-400" />
                </motion.button>

                <motion.button
                  onClick={handleCallButton}
                  whileTap={{ scale: 0.95 }}
                  className={`w-24 h-24 rounded-full flex items-center justify-center transition-all shadow-lg ${
                    isRecording
                      ? 'bg-red-600 shadow-red-500/50'
                      : 'bg-gradient-to-br from-primary-pink to-pink-600 shadow-primary-pink/50'
                  }`}
                >
                  {isRecording ? <Mic size={32} className="animate-pulse" /> : <Phone size={32} />}
                </motion.button>

                <motion.button
                  whileTap={{ scale: 0.95 }}
                  className="w-16 h-16 bg-gray-800/50 hover:bg-gray-700/50 rounded-full flex items-center justify-center border border-gray-700 transition-all"
                >
                  <MicOff size={24} className="text-gray-400" />
                </motion.button>
              </div>

              {/* Instructions */}
              <div className="text-center lg:text-left text-gray-500 text-sm">
                <p>Click the call button to start recording, click again to send</p>
              </div>
            </div>

            {/* Right: Animated Orb */}
            <div className="w-full lg:w-1/2 flex flex-col items-center mt-8 lg:mt-0">
              <div className="relative">
                <SelectedOrbComponent isPlaying={isPlaying} size="large" />
                <button
                  onClick={() => setShowOrbSelector(true)}
                  className="absolute -bottom-4 left-1/2 -translate-x-1/2 px-4 py-2 bg-gray-800/80 hover:bg-gray-700/80 rounded-full text-xs flex items-center gap-2 border border-gray-600 transition-all"
                >
                  <Sparkles size={14} />
                  <span>Change Style</span>
                </button>
              </div>
            </div>
          </div>
        </section>
      </div>

      {/* Orb Selector Modal */}
      {showOrbSelector && (
        <OrbSelector
          onSelect={handleOrbSelection}
          currentSelection={selectedOrb}
        />
      )}
    </div>
  )
}

export default Podcast
