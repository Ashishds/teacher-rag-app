import { useState, useRef, useEffect } from 'react'
import ReactMarkdown from 'react-markdown'

function App() {
  const [question, setQuestion] = useState('')
  const [messages, setMessages] = useState([
    {
      role: 'assistant',
      content: "Hello! I'm your AI Tutor 🎓\n\nAsk me anything about GenAI, and I'll explain it just like Sudhanshu Sir would!",
      sources: []
    }
  ])
  const [loading, setLoading] = useState(false)
  const messagesEndRef = useRef(null)

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  const handleSend = async (e) => {
    e.preventDefault()
    if (!question.trim()) return

    const userQuestion = question
    setQuestion('')
    setMessages(prev => [...prev, { role: 'user', content: userQuestion, sources: [] }])
    setLoading(true)

    let messageIndex = -1
    let started = false
    let charQueue = []
    let currentText = ''

    // Animate characters with delay
    const animateNext = () => {
      if (charQueue.length > 0) {
        const nextChars = charQueue.splice(0, 3) // Process 3 chars at a time
        currentText += nextChars.join('')

        setMessages(prev => {
          const newMsgs = [...prev]
          if (newMsgs[messageIndex]) {
            newMsgs[messageIndex].content = currentText
          }
          return newMsgs
        })

        setTimeout(animateNext, 30) // 30ms delay for visible streaming
      }
    }

    try {
      const response = await fetch('/api/query', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question: userQuestion })
      })

      if (!response.ok) throw new Error('Failed to fetch')

      const reader = response.body.getReader()
      const decoder = new TextDecoder()
      let buffer = ''

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split('\n\n')
        buffer = lines.pop() || ''

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            const data = JSON.parse(line.slice(6))

            if (data.type === 'content') {
              if (!started) {
                started = true
                setLoading(false)
                messageIndex = messages.length + 1
                setMessages(prev => [...prev, { role: 'assistant', content: '', sources: [] }])
              }

              // Add to queue for animation
              charQueue.push(...data.data.split(''))
              if (charQueue.length === data.data.length) {
                animateNext()
              }

            } else if (data.type === 'sources') {
              // Wait for character animation to finish before showing sources
              const waitForAnimation = () => {
                if (charQueue.length === 0) {
                  setMessages(prev => {
                    const newMsgs = [...prev]
                    if (newMsgs[messageIndex]) {
                      newMsgs[messageIndex].sources = data.data
                    }
                    return newMsgs
                  })
                } else {
                  setTimeout(waitForAnimation, 100)
                }
              }
              waitForAnimation()
            } else if (data.type === 'done') {
              setLoading(false)
            }
          }
        }
      }

    } catch (error) {
      console.error('Error:', error)
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: "I'm sorry, I'm having trouble right now. Please try again.",
        sources: []
      }])
      setLoading(false)
    }
  }

  return (
    <div className="flex flex-col h-screen bg-gradient-to-br from-slate-950 via-gray-900 to-slate-950">
      {/* Header */}
      <header className="bg-gradient-to-r from-slate-900/95 via-gray-900/95 to-slate-900/95 backdrop-blur-xl border-b border-teal-500/10 shadow-2xl sticky top-0 z-50">
        <div className="max-w-6xl mx-auto px-4 sm:px-8 py-4 sm:py-5">
          <div className="flex items-center justify-center gap-4 mb-2">
            <div className="relative group">
              <div className="absolute inset-0 bg-gradient-to-r from-teal-400 to-cyan-400 rounded-full blur-xl opacity-40 group-hover:opacity-60 transition-opacity"></div>
              <img
                src="/tutor.jpg"
                alt="Shudhansu Sir"
                className="relative w-14 h-14 sm:w-16 sm:h-16 rounded-full border-3 border-teal-400/60 shadow-2xl object-cover ring-4 ring-teal-500/20 group-hover:scale-105 transition-transform"
              />
            </div>
            <h1 className="text-2xl sm:text-4xl font-bold bg-gradient-to-r from-teal-300 via-cyan-300 to-teal-300 bg-clip-text text-transparent drop-shadow-lg">
              Learn GenAI With Sudhanshu Sir
            </h1>
          </div>
          <div className="flex justify-center">
            <span className="inline-flex items-center gap-2.5 text-xs sm:text-sm font-semibold text-teal-200/90 px-4 py-1.5 rounded-full bg-gradient-to-r from-teal-500/20 to-cyan-500/20 border border-teal-400/30 backdrop-blur-sm shadow-lg">
              <svg className="w-3.5 h-3.5 text-teal-300" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm1-12a1 1 0 10-2 0v4a1 1 0 00.293.707l2.828 2.829a1 1 0 101.415-1.415L11 9.586V6z" clipRule="evenodd" />
              </svg>
              ANYTIME • ANYWHERE
            </span>
          </div>
        </div>
      </header>

      {/* Chat Area */}
      <main className="flex-1 overflow-y-auto">
        <div className="max-w-4xl mx-auto px-4 sm:px-8 py-6 sm:py-8 space-y-6">
          {messages.map((msg, index) => (
            <div
              key={index}
              className={`flex gap-3 sm:gap-4 ${msg.role === 'user' ? 'justify-end' : 'justify-start'} opacity-0 animate-[fadeInUp_0.6s_ease-out_forwards]`}
              style={{ animationDelay: `${index * 0.1}s` }}
            >

              {/* Assistant Avatar */}
              {msg.role === 'assistant' && (
                <div className="flex-shrink-0 mt-1">
                  <div className="relative">
                    <div className="absolute inset-0 bg-teal-400/20 rounded-full blur-md"></div>
                    <img
                      src="/tutor.jpg"
                      alt="AI Tutor"
                      className="relative w-9 h-9 sm:w-10 sm:h-10 rounded-full border-2 border-teal-400/40 shadow-xl object-cover ring-2 ring-teal-500/20"
                    />
                  </div>
                </div>
              )}

              {/* Message Bubble */}
              <div className={`group max-w-[90%] sm:max-w-[80%] md:max-w-2xl ${msg.role === 'user'
                ? 'bg-gradient-to-br from-teal-600 to-cyan-700 rounded-3xl rounded-br-lg shadow-xl border border-teal-400/30'
                : 'bg-gradient-to-br from-slate-800/90 to-gray-800/90 backdrop-blur-md rounded-3xl rounded-bl-lg border border-teal-500/10 shadow-xl'
                } hover:shadow-2xl transition-all duration-300`}>
                <div className="p-4 sm:p-5">
                  <div className={`prose prose-lg max-w-none leading-relaxed ${msg.role === 'user'
                    ? 'prose-invert [&>p]:text-white [&>p]:text-[0.95rem] sm:[&>p]:text-base [&>*]:text-white [&_strong]:text-teal-100 [&_strong]:font-bold'
                    : 'prose-invert [&>p]:text-gray-100 [&>p]:text-[0.95rem] sm:[&>p]:text-base [&_strong]:text-teal-300 [&_strong]:font-bold [&_code]:text-cyan-300 [&_code]:bg-teal-900/40 [&_code]:px-2 [&_code]:py-1 [&_code]:rounded-md [&_code]:text-sm [&_ol]:text-gray-200 [&_ul]:text-gray-200 [&_li]:text-[0.95rem] sm:[&_li]:text-base'
                    }`}>
                    <ReactMarkdown>{msg.content}</ReactMarkdown>
                  </div>

                  {/* Sources */}
                  {msg.sources && msg.sources.length > 0 && (
                    <div className="mt-4 pt-3 border-t border-teal-500/20">
                      <div className="flex items-center gap-2 mb-2">
                        <svg className="w-4 h-4 text-teal-300" fill="currentColor" viewBox="0 0 20 20">
                          <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clipRule="evenodd" />
                        </svg>
                        <span className="text-xs font-bold text-teal-200 uppercase tracking-wide">
                          Referenced Sources
                        </span>
                      </div>
                      <div className="space-y-2">
                        {msg.sources.map((source, idx) => (
                          <div
                            key={idx}
                            className="flex items-center gap-2 text-[0.7rem] sm:text-xs bg-gradient-to-r from-slate-700/30 to-gray-700/30 px-2.5 py-1.5 rounded-lg border border-teal-500/10 hover:border-teal-400/20 transition-all"
                          >
                            <svg className="w-3 h-3 text-teal-400 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
                              <path d="M9 4.804A7.968 7.968 0 005.5 4c-1.255 0-2.443.29-3.5.804v10A7.969 7.969 0 015.5 14c1.669 0 3.218.51 4.5 1.385A7.962 7.962 0 0114.5 14c1.255 0 2.443.29 3.5.804v-10A7.968 7.968 0 0014.5 4c-1.255 0-2.443.29-3.5.804V12a1 1 0 11-2 0V4.804z" />
                            </svg>
                            <span className="font-semibold text-teal-200 truncate" title={source.course}>{source.course}</span>
                            <span className="text-gray-500">•</span>
                            <span className="text-gray-300 truncate flex-1" title={source.lecture}>{source.lecture}</span>
                            <span className="text-gray-500">•</span>
                            <span className="text-gray-400 font-mono whitespace-nowrap">
                              {source.timestamp_start.split('.')[0].substring(0, 8)}
                            </span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              </div>
            </div>
          ))}

          {loading && (
            <div className="flex justify-start gap-3 opacity-0 animate-[fadeInUp_0.4s_ease-out_forwards]">
              <div className="flex-shrink-0 mt-1">
                <div className="relative">
                  <div className="absolute inset-0 bg-teal-400/20 rounded-full blur-md"></div>
                  <img
                    src="/tutor.jpg"
                    alt="AI Tutor"
                    className="relative w-9 h-9 sm:w-10 sm:h-10 rounded-full border-2 border-teal-400/40 shadow-xl object-cover ring-2 ring-teal-500/20"
                  />
                </div>
              </div>
              <div className="bg-gradient-to-br from-slate-800/90 to-gray-800/90 backdrop-blur-md rounded-3xl rounded-bl-lg border border-teal-500/10 shadow-xl p-4">
                <div className="flex items-center gap-4">
                  <div className="flex gap-2">
                    <div className="w-2 h-2 bg-teal-400 rounded-full animate-bounce" style={{ animationDelay: '0ms' }}></div>
                    <div className="w-2 h-2 bg-teal-400 rounded-full animate-bounce" style={{ animationDelay: '150ms' }}></div>
                    <div className="w-2 h-2 bg-teal-400 rounded-full animate-bounce" style={{ animationDelay: '300ms' }}></div>
                  </div>
                  <span className="text-sm text-teal-200 font-medium">Thinking...</span>
                </div>
              </div>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>
      </main>

      {/* Input Area */}
      <div className="border-t border-teal-500/10 bg-gradient-to-r from-slate-900/95 via-gray-900/95 to-slate-900/95 backdrop-blur-xl shadow-2xl">
        <div className="max-w-4xl mx-auto px-4 sm:px-8 py-5 sm:py-6">
          <form onSubmit={handleSend} className="relative">
            <div className="relative group">
              <input
                type="text"
                value={question}
                onChange={(e) => setQuestion(e.target.value)}
                placeholder="Ask a question about the lecture..."
                className="w-full pl-6 pr-32 py-4 text-base bg-slate-800/90 text-white rounded-2xl border-2 border-teal-500/20 focus:outline-none focus:ring-2 focus:ring-teal-400/50 focus:border-teal-400/50 placeholder-gray-500 transition-all shadow-xl hover:shadow-2xl hover:border-teal-400/30 font-medium"
                disabled={loading}
              />
              <button
                type="submit"
                disabled={loading || !question.trim()}
                className="absolute right-2 top-1/2 -translate-y-1/2 bg-gradient-to-r from-teal-500 to-cyan-600 hover:from-teal-600 hover:to-cyan-700 text-white px-6 py-2.5 rounded-xl font-bold disabled:opacity-40 disabled:cursor-not-allowed transition-all shadow-lg hover:shadow-teal-500/30 active:scale-95 text-base flex items-center gap-2"
              >
                <span>Send</span>
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" />
                </svg>
              </button>
            </div>
          </form>
          <p className="text-center text-sm text-gray-500 mt-4 flex items-center justify-center gap-2 font-medium">
            <svg className="w-4 h-4 text-teal-400" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clipRule="evenodd" />
            </svg>
            AI responses generated from lecture transcripts
          </p>
        </div>
      </div>
    </div>
  )
}

export default App
