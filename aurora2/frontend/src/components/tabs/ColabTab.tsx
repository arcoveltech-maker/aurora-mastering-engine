import { useState, useRef, useEffect, useCallback } from 'react';
import { Send, Scissors, Tag, Loader2 } from 'lucide-react';
import { api } from '@/utils/api';
import { useAuth } from '@/contexts/AuthContext';
import { useSessionStore } from '@/stores/sessionStore';
import { useToast } from '@/contexts/ToastContext';

interface Message {
  role: 'user' | 'assistant';
  content: string;
}

interface StemJob {
  jobId: string;
  status: 'pending' | 'complete' | 'error';
  numStems: number;
}

export function ColabTab() {
  const [messages, setMessages] = useState<Message[]>([
    {
      role: 'assistant',
      content: "Hi! I'm Aurora AI. I can help you with stem separation (12-stem Demucs), metadata editing, and mastering adjustments. What would you like to do?",
    },
  ]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [stemJobs, setStemJobs] = useState<StemJob[]>([]);
  const [metadataTags, setMetadataTags] = useState<Record<string, string>>({
    title: '', artist: '', album: '', year: '', genre: '',
  });
  const [activePanel, setActivePanel] = useState<'chat' | 'stems' | 'metadata'>('chat');
  const scrollRef = useRef<HTMLDivElement>(null);

  const { sessionToken } = useAuth();
  const { sessionId, sourceFileKey } = useSessionStore();
  const { addToast } = useToast();

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: 'smooth' });
  }, [messages]);

  const sendMessage = useCallback(async () => {
    const text = input.trim();
    if (!text || isLoading) return;
    setInput('');

    const userMsg: Message = { role: 'user', content: text };
    setMessages((prev) => [...prev, userMsg]);
    setIsLoading(true);

    try {
      const res = await api.colab.chat(
        sessionToken ?? '',
        sessionId ?? '',
        [...messages, userMsg],
      );

      setMessages((prev) => [...prev, { role: 'assistant', content: res.reply }]);

      // Execute any actions returned by AI
      if (res.actions) {
        for (const action of res.actions) {
          if (action.type === 'stem_separate' && sourceFileKey) {
            const numStems = (action.params['num_stems'] as number) ?? 12;
            handleStemSeparate(numStems as 12 | 6 | 4 | 2);
          }
        }
      }
    } catch {
      setMessages((prev) => [...prev, {
        role: 'assistant',
        content: 'Sorry, I encountered an error. Please try again.',
      }]);
    } finally {
      setIsLoading(false);
    }
  }, [input, isLoading, messages, sessionToken, sessionId, sourceFileKey]);

  const handleStemSeparate = useCallback(async (numStems: 12 | 6 | 4 | 2) => {
    if (!sourceFileKey || !sessionToken) {
      addToast({ type: 'warning', message: 'Upload a track first' });
      return;
    }
    try {
      const { job_id } = await api.colab.separateStems(sessionToken, sourceFileKey, numStems);
      setStemJobs((prev) => [...prev, { jobId: job_id, status: 'pending', numStems }]);
      addToast({ type: 'info', message: `${numStems}-stem separation started` });
    } catch {
      addToast({ type: 'error', message: 'Stem separation failed' });
    }
  }, [sourceFileKey, sessionToken, addToast]);

  const handleWriteMetadata = useCallback(async () => {
    if (!sourceFileKey || !sessionToken) {
      addToast({ type: 'warning', message: 'Upload a track first' });
      return;
    }
    const nonEmpty = Object.fromEntries(
      Object.entries(metadataTags).filter(([, v]) => v.trim())
    );
    try {
      await api.colab.writeMetadata(sessionToken, sourceFileKey, nonEmpty);
      addToast({ type: 'success', message: 'Metadata written to file' });
    } catch {
      addToast({ type: 'error', message: 'Failed to write metadata' });
    }
  }, [sourceFileKey, sessionToken, metadataTags, addToast]);

  return (
    <div className="flex flex-col h-full">
      {/* Panel tabs */}
      <div className="flex border-b border-slate-800">
        {(['chat', 'stems', 'metadata'] as const).map((p) => (
          <button
            key={p}
            onClick={() => setActivePanel(p)}
            className={`px-4 py-2 text-xs font-medium capitalize transition-colors ${
              activePanel === p
                ? 'text-aurora-accent border-b-2 border-aurora-accent'
                : 'text-white/40 hover:text-white/70'
            }`}
          >
            {p === 'stems' ? '12-Stem Separation' : p === 'metadata' ? 'Metadata' : 'AI Chat'}
          </button>
        ))}
      </div>

      {/* Chat panel */}
      {activePanel === 'chat' && (
        <div className="flex flex-col flex-1 min-h-0">
          <div ref={scrollRef} className="flex-1 overflow-y-auto p-3 flex flex-col gap-2">
            {messages.map((msg, i) => (
              <div
                key={i}
                className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
              >
                <div className={`max-w-[80%] rounded-lg px-3 py-2 text-sm ${
                  msg.role === 'user'
                    ? 'bg-aurora-accent text-white'
                    : 'bg-slate-800 text-white/80'
                }`}>
                  {msg.content}
                </div>
              </div>
            ))}
            {isLoading && (
              <div className="flex justify-start">
                <div className="bg-slate-800 rounded-lg px-3 py-2">
                  <Loader2 className="w-4 h-4 text-aurora-accent animate-spin" />
                </div>
              </div>
            )}
          </div>
          <div className="p-3 border-t border-slate-800 flex gap-2">
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && !e.shiftKey && sendMessage()}
              placeholder="Ask Aurora AI anything..."
              className="flex-1 bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-sm text-white placeholder-white/30 focus:outline-none focus:border-aurora-accent"
            />
            <button
              onClick={sendMessage}
              disabled={isLoading || !input.trim()}
              className="p-2 bg-aurora-accent rounded-lg disabled:opacity-40 hover:bg-blue-400 transition-colors"
            >
              <Send className="w-4 h-4 text-white" />
            </button>
          </div>
        </div>
      )}

      {/* Stem separation panel */}
      {activePanel === 'stems' && (
        <div className="flex flex-col gap-4 p-4">
          <p className="text-sm text-white/50">
            Separate your track into individual stems using Demucs deep learning model.
          </p>
          <div className="grid grid-cols-2 gap-2">
            {([12, 6, 4, 2] as const).map((n) => (
              <button
                key={n}
                onClick={() => handleStemSeparate(n)}
                className="flex items-center gap-2 p-3 bg-slate-900 border border-slate-700 rounded-lg hover:border-aurora-accent/50 transition-colors text-sm text-white/70 hover:text-white"
              >
                <Scissors className="w-4 h-4 text-aurora-accent" />
                {n}-stem split
              </button>
            ))}
          </div>
          {stemJobs.length > 0 && (
            <div className="flex flex-col gap-2">
              <span className="text-xs text-white/40 uppercase tracking-wider">Jobs</span>
              {stemJobs.map((j) => (
                <div key={j.jobId} className="flex items-center justify-between p-2 bg-slate-900 rounded-lg text-sm">
                  <span className="text-white/70">{j.numStems}-stem</span>
                  <span className={`text-xs px-2 py-0.5 rounded ${
                    j.status === 'complete' ? 'bg-green-900 text-green-400' :
                    j.status === 'error' ? 'bg-red-900 text-red-400' :
                    'bg-slate-800 text-white/40'
                  }`}>{j.status}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Metadata panel */}
      {activePanel === 'metadata' && (
        <div className="flex flex-col gap-3 p-4">
          <p className="text-sm text-white/50">Write ID3/metadata tags to your audio file.</p>
          <div className="grid grid-cols-2 gap-2">
            {Object.keys(metadataTags).map((key) => (
              <div key={key} className="flex flex-col gap-1">
                <label className="text-xs text-white/40 capitalize">{key}</label>
                <input
                  type="text"
                  value={metadataTags[key]}
                  onChange={(e) => setMetadataTags((prev) => ({ ...prev, [key]: e.target.value }))}
                  className="bg-slate-900 border border-slate-700 rounded px-2 py-1.5 text-sm text-white focus:outline-none focus:border-aurora-accent"
                />
              </div>
            ))}
          </div>
          <button
            onClick={handleWriteMetadata}
            className="flex items-center justify-center gap-2 py-2 bg-aurora-accent rounded-lg text-sm text-white hover:bg-blue-400 transition-colors mt-2"
          >
            <Tag className="w-4 h-4" />
            Write Metadata to File
          </button>
        </div>
      )}
    </div>
  );
}
