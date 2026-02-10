import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { ArrowLeft, Check, Volume2, ChevronDown } from 'lucide-react'
import Logo from '../components/Logo'

function Preferences() {
  const navigate = useNavigate()
  const [selectedTopics, setSelectedTopics] = useState([])
  const [selectedSources, setSelectedSources] = useState([])
  const [selectedVoice, setSelectedVoice] = useState('en-US-Chirp3-HD-Aoede')
  const [isSaving, setIsSaving] = useState(false)
  const [showMobilePreview, setShowMobilePreview] = useState(false)
  const [toast, setToast] = useState(null)

  // Topics with article counts and trending status
  const topicsData = [
    { id: 'Politics', name: 'Politics', count: 24, trending: true },
    { id: 'Technology', name: 'Technology', count: 18, trending: false },
    { id: 'Health', name: 'Health', count: 12, trending: false },
    { id: 'Business', name: 'Business', count: 15, trending: false },
    { id: 'Sports', name: 'Sports', count: 8, trending: false },
    { id: 'Entertainment', name: 'Entertainment', count: 6, trending: false },
    { id: 'Campus Life', name: 'Campus Life', count: 22, trending: true },
    { id: 'Research', name: 'Research', count: 28, trending: true }
  ]

  // Sources with metadata
  const sourcesData = [
    {
      id: 'Harvard Crimson',
      name: 'Harvard Crimson',
      description: 'Student-run newspaper covering campus news',
      url: 'thecrimson.harvard.edu',
      count: 18,
      icon: '📰'
    },
    {
      id: 'Harvard Gazette',
      name: 'Harvard Gazette',
      description: 'Official news from Harvard University',
      url: 'news.harvard.edu',
      count: 24,
      icon: '📜'
    },
    {
      id: 'Harvard Medical School',
      name: 'Harvard Medical School',
      description: 'Medical research and health news',
      url: 'hms.harvard.edu',
      count: 12,
      icon: '🏥'
    },
    {
      id: 'Harvard SEAS',
      name: 'Harvard SEAS',
      description: 'Engineering and applied sciences',
      url: 'seas.harvard.edu',
      count: 15,
      icon: '⚙️'
    },
    {
      id: 'Harvard Law School',
      name: 'Harvard Law School',
      description: 'Legal news and analysis',
      url: 'hls.harvard.edu',
      count: 10,
      icon: '⚖️'
    },
    {
      id: 'Harvard Business School',
      name: 'Harvard Business School',
      description: 'Business insights and research',
      url: 'hbs.edu',
      count: 14,
      icon: '💼'
    },
    {
      id: 'Harvard Magazine',
      name: 'Harvard Magazine',
      description: 'In-depth stories from the Harvard community',
      url: 'harvardmagazine.com',
      count: 8,
      icon: '📖'
    },
    {
      id: 'Harvard Kennedy School',
      name: 'Harvard Kennedy School',
      description: 'Public policy and governance',
      url: 'hks.harvard.edu',
      count: 11,
      icon: '🏛️'
    }
  ]

  // Voice options
  const voicesData = [
    {
      id: 'en-US-Chirp3-HD-Aoede',
      name: 'Aoede',
      gender: 'Female',
      style: 'Natural & Warm',
      description: 'A friendly, conversational voice perfect for daily news',
      icon: '👩'
    },
    {
      id: 'en-US-Chirp3-HD-Alnilam',
      name: 'Alnilam',
      gender: 'Male',
      style: 'Professional & Clear',
      description: 'A confident, authoritative voice for serious topics',
      icon: '👨'
    }
  ]

  // Sample headlines for preview
  const sampleHeadlines = {
    'Politics': [
      'Harvard Study Reveals New Insights on Voter Behavior',
      'Political Science Department Hosts International Summit'
    ],
    'Technology': [
      'SEAS Researchers Develop Revolutionary AI Algorithm',
      'Harvard-MIT Partnership Advances Quantum Computing'
    ],
    'Health': [
      'HMS Study Links Sleep Patterns to Mental Health',
      'New COVID-19 Research Published by Harvard Scientists'
    ],
    'Business': [
      'HBS Case Study Examines Tech Industry Disruption',
      'Alumni-Founded Startup Reaches Unicorn Status'
    ],
    'Sports': [
      'Harvard Crew Team Claims Victory at National Championship',
      'Athletic Department Unveils New Training Facility'
    ],
    'Entertainment': [
      'Harvard Art Museums Debut Major New Exhibition',
      'Student Film Wins Sundance Documentary Prize'
    ],
    'Campus Life': [
      'New Residential Hall Opens in Harvard Yard',
      'Student Organizations Plan Record Number of Events'
    ],
    'Research': [
      'Harvard Scientists Make Breakthrough in Cancer Treatment',
      'Climate Research Team Publishes Landmark Study'
    ]
  }

  // API helper functions
  const getApiUrl = () => {
    const isProduction = window.location.hostname.includes('newsjuiceapp.com')
    return isProduction ? '' : 'http://localhost:8080'
  }

  const getAuthHeaders = () => {
    const token = localStorage.getItem('auth_token')
    return {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json'
    }
  }

  // Load existing preferences on mount
  useEffect(() => {
    loadPreferences()
  }, [])

  // Show toast notifications
  useEffect(() => {
    if (toast) {
      const timer = setTimeout(() => setToast(null), 3000)
      return () => clearTimeout(timer)
    }
  }, [toast])

  const loadPreferences = async () => {
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

      // Parse preferences (they're stored as JSON strings)
      if (data.preferences) {
        const prefs = data.preferences
        if (prefs.topics) {
          const topics = typeof prefs.topics === 'string'
            ? JSON.parse(prefs.topics)
            : prefs.topics
          setSelectedTopics(topics)
        }
        if (prefs.sources) {
          const sources = typeof prefs.sources === 'string'
            ? JSON.parse(prefs.sources)
            : prefs.sources
          setSelectedSources(sources)
        }
        if (prefs.voice_preference) {
          setSelectedVoice(prefs.voice_preference)
        }
      }
    } catch (error) {
      console.error('[preferences] Error loading:', error)
    }
  }

  // Toggle topic selection
  const toggleTopic = (topic) => {
    setSelectedTopics(prev =>
      prev.includes(topic)
        ? prev.filter(t => t !== topic)
        : [...prev, topic]
    )
  }

  // Toggle source selection
  const toggleSource = (source) => {
    setSelectedSources(prev =>
      prev.includes(source)
        ? prev.filter(s => s !== source)
        : [...prev, source]
    )
  }

  // Apply preset
  const applyPreset = (preset) => {
    switch(preset) {
      case 'recommended':
        setSelectedTopics(['Politics', 'Technology', 'Campus Life', 'Research'])
        setSelectedSources(['Harvard Crimson', 'Harvard Gazette', 'Harvard SEAS', 'Harvard Business School'])
        setToast('✨ Applied recommended preset')
        break
      case 'all':
        setSelectedTopics(topicsData.map(t => t.id))
        setSelectedSources(sourcesData.map(s => s.id))
        setToast('📚 Selected all topics and sources')
        break
      case 'minimal':
        setSelectedTopics(['Campus Life', 'Politics'])
        setSelectedSources(['Harvard Crimson', 'Harvard Gazette'])
        setToast('⚡ Applied minimal brief preset')
        break
      case 'student':
        setSelectedTopics(['Campus Life', 'Sports', 'Entertainment'])
        setSelectedSources(['Harvard Crimson', 'Harvard Magazine'])
        setToast('🎓 Applied student focus preset')
        break
      default:
        break
    }
  }

  // Calculate preview stats
  const calculatePreviewStats = () => {
    let totalArticles = 0
    let headlines = []

    selectedTopics.forEach(topicId => {
      const topic = topicsData.find(t => t.id === topicId)
      if (topic) {
        totalArticles += Math.floor(topic.count * (selectedSources.length / sourcesData.length))
        if (sampleHeadlines[topicId]) {
          headlines = headlines.concat(sampleHeadlines[topicId].slice(0, 2))
        }
      }
    })

    headlines = headlines.slice(0, 6)
    const listenTime = Math.ceil((totalArticles * 1.5) / 3)

    return { totalArticles, listenTime, headlines }
  }

  const { totalArticles, listenTime, headlines } = calculatePreviewStats()

  // Calculate progress
  const calculateProgress = () => {
    let completed = 0
    if (selectedTopics.length > 0) completed++
    if (selectedSources.length > 0) completed++
    if (selectedVoice) completed++
    return { completed, total: 3, percentage: (completed / 3) * 100 }
  }

  const progress = calculateProgress()

  // Play voice sample
  const playVoiceSample = (voiceId) => {
    const voice = voicesData.find(v => v.id === voiceId)
    setToast(`🔊 Playing ${voice.name} voice sample...`)
  }

  // Save preferences to backend
  const savePreferences = async () => {
    if (selectedTopics.length === 0 || selectedSources.length === 0) {
      setToast('⚠️ Please select at least one topic and one source')
      return
    }

    setIsSaving(true)

    const payload = {
      topics: selectedTopics,
      sources: selectedSources,
      voice_preference: selectedVoice
    }

    try {
      console.log('[preferences] Saving payload:', JSON.stringify(payload, null, 2))
      console.log('[preferences] API URL:', getApiUrl())
      console.log('[preferences] Auth token exists:', !!localStorage.getItem('auth_token'))

      const response = await fetch(`${getApiUrl()}/api/user/preferences`, {
        method: 'POST',
        headers: getAuthHeaders(),
        body: JSON.stringify(payload)
      })

      if (!response.ok) {
        const errorText = await response.text()
        console.error('[preferences] Server response:', errorText)
        throw new Error(`Failed to save preferences: ${response.status}`)
      }

      const result = await response.json()
      console.log('[preferences] Saved successfully:', result)
      setToast('✅ Preferences saved successfully!')

      // Navigate back to podcast page after short delay
      setTimeout(() => navigate('/podcast'), 1500)
    } catch (error) {
      console.error('[preferences] Error saving:', error)
      setToast('❌ Failed to save preferences. Please try again.')
    } finally {
      setIsSaving(false)
    }
  }

  // Reset preferences
  const resetPreferences = () => {
    setSelectedTopics([])
    setSelectedSources([])
    setSelectedVoice('en-US-Chirp3-HD-Aoede')
    setToast('🔄 Preferences reset')
  }

  return (
    <div className="min-h-screen bg-primary-darker text-white">
      {/* Toast Notification */}
      {toast && (
        <div className="fixed bottom-6 right-6 z-50 bg-gray-800 text-white px-6 py-3 rounded-full shadow-lg border border-gray-700 animate-slide-up">
          {toast}
        </div>
      )}

      {/* Header */}
      <div className="sticky top-0 z-40 bg-primary-darker/80 backdrop-blur-lg border-b border-gray-800">
        <div className="max-w-7xl mx-auto px-6 py-4 flex items-center justify-between">
          <button
            onClick={() => navigate('/podcast')}
            className="p-2 hover:bg-gray-800 rounded-full transition-colors"
          >
            <ArrowLeft size={24} />
          </button>
          <Logo />
          <div className="w-10"></div>
        </div>
      </div>

      {/* Main Content */}
      <div className="max-w-7xl mx-auto px-6 py-8">
        <div className="lg:flex lg:gap-8">

          {/* Left Column: Preferences */}
          <div className="flex-1 space-y-10">

            {/* Progress Indicator */}
            <div className="bg-blue-900/20 border border-blue-800/50 rounded-2xl p-6">
              <div className="flex items-center justify-between mb-2">
                <span className="font-semibold">Setup Progress</span>
                <span className="text-sm text-gray-400">{progress.completed}/{progress.total} Complete</span>
              </div>
              <div className="w-full bg-gray-800 rounded-full h-2 mb-3">
                <div className="bg-gradient-to-r from-primary-pink to-pink-500 h-2 rounded-full transition-all duration-500" style={{ width: `${progress.percentage}%` }}></div>
              </div>
              <div className="flex items-center gap-4 text-sm flex-wrap">
                <span className={selectedTopics.length > 0 ? 'text-green-400' : 'text-gray-500'}>
                  {selectedTopics.length > 0 ? '✓' : '⏳'} Select topics
                </span>
                <span className={selectedSources.length > 0 ? 'text-green-400' : 'text-gray-500'}>
                  {selectedSources.length > 0 ? '✓' : '⏳'} Choose sources
                </span>
                <span className={selectedVoice ? 'text-green-400' : 'text-gray-500'}>
                  {selectedVoice ? '✓' : '⏳'} Pick voice
                </span>
              </div>
            </div>

            {/* Quick Presets */}
            <section>
              <h2 className="text-2xl font-bold mb-4">Quick Setup</h2>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                <button
                  onClick={() => applyPreset('recommended')}
                  className="px-4 py-3 bg-gray-800/50 hover:bg-gray-700/50 border border-gray-700 rounded-2xl text-sm font-medium transition-all hover:border-primary-pink/50"
                >
                  ✨ Recommended
                </button>
                <button
                  onClick={() => applyPreset('all')}
                  className="px-4 py-3 bg-gray-800/50 hover:bg-gray-700/50 border border-gray-700 rounded-2xl text-sm font-medium transition-all hover:border-primary-pink/50"
                >
                  📚 Select All
                </button>
                <button
                  onClick={() => applyPreset('minimal')}
                  className="px-4 py-3 bg-gray-800/50 hover:bg-gray-700/50 border border-gray-700 rounded-2xl text-sm font-medium transition-all hover:border-primary-pink/50"
                >
                  ⚡ Minimal Brief
                </button>
                <button
                  onClick={() => applyPreset('student')}
                  className="px-4 py-3 bg-gray-800/50 hover:bg-gray-700/50 border border-gray-700 rounded-2xl text-sm font-medium transition-all hover:border-primary-pink/50"
                >
                  🎓 Student Focus
                </button>
              </div>
            </section>

            {/* Topics Section */}
            <section>
              <h2 className="text-2xl font-bold mb-2">Topics</h2>
              <p className="text-gray-400 mb-6">
                Select the topics you'd like to see in your daily briefing
              </p>

              <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                {topicsData.map((topic) => (
                  <button
                    key={topic.id}
                    onClick={() => toggleTopic(topic.id)}
                    className={`relative px-6 py-4 rounded-2xl font-medium transition-all ${
                      selectedTopics.includes(topic.id)
                        ? 'bg-gradient-to-br from-primary-pink to-pink-600 text-white shadow-lg shadow-primary-pink/30 border border-primary-pink'
                        : 'bg-gray-800/50 text-gray-300 hover:bg-gray-700/50 border border-gray-700'
                    }`}
                  >
                    <div className="flex items-center justify-between mb-1">
                      <span>{topic.name}</span>
                      {selectedTopics.includes(topic.id) && (
                        <Check size={16} />
                      )}
                    </div>
                    <div className="flex items-center gap-2">
                      <span className="text-xs text-gray-400">{topic.count} articles</span>
                      {topic.trending && (
                        <span className="text-xs bg-primary-pink/20 text-primary-pink px-2 py-0.5 rounded-full">Trending</span>
                      )}
                    </div>
                  </button>
                ))}
              </div>

              <p className="text-sm text-gray-500 mt-4">
                Selected: <span className="font-semibold text-white">{selectedTopics.length}</span> topics
              </p>
              {selectedTopics.length === 0 && (
                <p className="text-sm text-yellow-400 mt-2">💡 Tip: Select 3-5 topics for a well-rounded brief</p>
              )}
            </section>

            {/* Sources Section */}
            <section>
              <h2 className="text-2xl font-bold mb-2">News Sources</h2>
              <p className="text-gray-400 mb-6">
                Choose which Harvard news sources to include
              </p>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                {sourcesData.map((source) => (
                  <button
                    key={source.id}
                    onClick={() => toggleSource(source.id)}
                    className={`relative px-6 py-4 rounded-2xl font-medium text-left transition-all ${
                      selectedSources.includes(source.id)
                        ? 'bg-gradient-to-br from-primary-pink to-pink-600 text-white shadow-lg shadow-primary-pink/30 border border-primary-pink'
                        : 'bg-gray-800/50 text-gray-300 hover:bg-gray-700/50 border border-gray-700'
                    }`}
                  >
                    <div className="flex items-start justify-between mb-2">
                      <div className="flex items-center gap-3">
                        <span className="text-2xl">{source.icon}</span>
                        <div>
                          <p className="font-semibold">{source.name}</p>
                          <p className="text-xs opacity-70">{source.url}</p>
                        </div>
                      </div>
                      {selectedSources.includes(source.id) && (
                        <Check size={18} className="flex-shrink-0" />
                      )}
                    </div>
                    <p className="text-xs opacity-90">{source.description}</p>
                    <p className="text-xs text-primary-pink mt-2">{source.count} articles today</p>
                  </button>
                ))}
              </div>

              <p className="text-sm text-gray-500 mt-4">
                Selected: <span className="font-semibold text-white">{selectedSources.length}</span> sources
              </p>
              {selectedSources.length > 0 && selectedSources.length <= 2 && (
                <p className="text-sm text-yellow-400 mt-2">💡 Tip: Most users select 4-6 sources for better coverage</p>
              )}
            </section>

            {/* Voice Selection */}
            <section>
              <h2 className="text-2xl font-bold mb-2">Voice Preference</h2>
              <p className="text-gray-400 mb-6">
                Choose the voice for your podcast narration
              </p>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4 max-w-2xl">
                {voicesData.map((voice) => (
                  <button
                    key={voice.id}
                    onClick={() => setSelectedVoice(voice.id)}
                    className={`relative px-6 py-6 rounded-2xl text-left transition-all border-2 ${
                      selectedVoice === voice.id
                        ? 'bg-gradient-to-br from-primary-pink to-pink-600 text-white border-primary-pink shadow-lg shadow-primary-pink/30'
                        : 'bg-gray-800/50 text-gray-300 hover:bg-gray-700/50 border-gray-700'
                    }`}
                  >
                    <div className="flex items-center gap-3 mb-3">
                      <div className="w-12 h-12 rounded-full bg-gray-700/50 flex items-center justify-center text-2xl">
                        {voice.icon}
                      </div>
                      <div>
                        <p className="font-semibold text-lg">{voice.name}</p>
                        <p className="text-xs opacity-70">{voice.gender} • {voice.style}</p>
                      </div>
                    </div>
                    <p className="text-sm opacity-90 mb-3">{voice.description}</p>
                    <button
                      onClick={(e) => {
                        e.stopPropagation()
                        playVoiceSample(voice.id)
                      }}
                      className="w-full px-4 py-2 bg-gray-900/50 hover:bg-gray-900 rounded-lg text-sm font-medium transition-colors flex items-center justify-center gap-2"
                    >
                      <Volume2 size={16} />
                      Preview Voice
                    </button>
                  </button>
                ))}
              </div>

              <p className="text-sm text-gray-500 mt-4">
                This voice will be used for all podcast narrations, including daily briefs and Q&A responses.
              </p>
            </section>

            {/* Action Buttons */}
            <div className="flex gap-4 pt-6">
              <button
                onClick={savePreferences}
                disabled={isSaving || selectedTopics.length === 0 || selectedSources.length === 0}
                className="flex-1 py-4 bg-gradient-to-r from-primary-pink to-pink-500 rounded-full text-white font-semibold hover:shadow-lg hover:shadow-primary-pink/50 transition-all disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:shadow-none"
              >
                {isSaving ? 'Saving...' : 'Save Preferences'}
              </button>
              <button
                onClick={resetPreferences}
                className="px-8 py-4 bg-transparent border border-gray-600 rounded-full text-gray-300 hover:border-gray-500 transition-colors"
              >
                Cancel
              </button>
            </div>

            {/* Info Box */}
            <div className="bg-blue-900/20 border border-blue-800/50 rounded-2xl p-6">
              <h3 className="font-semibold mb-2 flex items-center gap-2">
                <span>💡</span>
                How it works
              </h3>
              <p className="text-sm text-gray-300">
                Your daily briefing will be personalized based on these preferences.
                You'll receive news from your selected sources that match your chosen topics.
                You can update your preferences anytime.
              </p>
            </div>

          </div>

          {/* Right Column: Preview Panel (Desktop) */}
          <div className="hidden lg:block lg:w-80 xl:w-96">
            <div className="sticky top-24">
              <div className="bg-gradient-to-br from-gray-800/30 to-gray-900/30 rounded-2xl p-6 border border-gray-700">
                <h3 className="text-xl font-bold mb-4 flex items-center gap-2">
                  <span>👀</span>
                  Your Brief Preview
                </h3>

                <div className="mb-6 p-4 bg-primary-dark/50 rounded-xl">
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-sm text-gray-400">Articles</span>
                    <span className="text-2xl font-bold text-primary-pink">{totalArticles}</span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-sm text-gray-400">Listen Time</span>
                    <span className="text-lg font-semibold">{totalArticles > 0 ? `~${listenTime} min` : '~0 min'}</span>
                  </div>
                </div>

                <div className="space-y-3">
                  {headlines.length > 0 ? (
                    <>
                      <div className="text-xs text-gray-400 mb-2">Sample headlines:</div>
                      {headlines.map((headline, idx) => (
                        <div key={idx} className="text-sm p-3 bg-primary-dark/50 rounded-lg border border-gray-700/50">
                          {headline}
                        </div>
                      ))}
                    </>
                  ) : (
                    <p className="text-sm text-gray-500 text-center py-8">
                      Select topics and sources to see sample headlines
                    </p>
                  )}
                </div>
              </div>
            </div>
          </div>

        </div>

        {/* Mobile Preview (Bottom Sheet) */}
        <div className="lg:hidden mt-10">
          <button
            onClick={() => setShowMobilePreview(!showMobilePreview)}
            className="w-full px-6 py-4 bg-gradient-to-br from-gray-800/30 to-gray-900/30 rounded-2xl border border-gray-700 font-semibold flex items-center justify-between"
          >
            <span>👀 Preview Your Brief</span>
            <ChevronDown size={20} className={`transition-transform ${showMobilePreview ? 'rotate-180' : ''}`} />
          </button>
          {showMobilePreview && (
            <div className="mt-4 bg-gradient-to-br from-gray-800/30 to-gray-900/30 rounded-2xl p-6 border border-gray-700">
              <div className="mb-6 p-4 bg-primary-dark/50 rounded-xl">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-sm text-gray-400">Articles</span>
                  <span className="text-2xl font-bold text-primary-pink">{totalArticles}</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-sm text-gray-400">Listen Time</span>
                  <span className="text-lg font-semibold">{totalArticles > 0 ? `~${listenTime} min` : '~0 min'}</span>
                </div>
              </div>
              <div className="space-y-3">
                {headlines.length > 0 ? (
                  <>
                    <div className="text-xs text-gray-400 mb-2">Sample headlines:</div>
                    {headlines.map((headline, idx) => (
                      <div key={idx} className="text-sm p-3 bg-primary-dark/50 rounded-lg border border-gray-700/50">
                        {headline}
                      </div>
                    ))}
                  </>
                ) : (
                  <p className="text-sm text-gray-500 text-center py-8">
                    Select topics and sources to see sample headlines
                  </p>
                )}
              </div>
            </div>
          )}
        </div>

      </div>
    </div>
  )
}

export default Preferences
