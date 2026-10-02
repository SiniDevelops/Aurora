'use client';
import { useState, useRef, useEffect } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import '@/styles/chat.css';

interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  skill?: string;
}

export default function ChatPage() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [isTyping, setIsTyping] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, isTyping]);

  const handleSend = (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim()) return;

    const newMsg: Message = { id: Date.now().toString(), role: 'user', content: input };
    setMessages(prev => [...prev, newMsg]);
    setInput('');
    setIsTyping(true);

    // Call backend API directly
    fetch('http://localhost:8000/api/chat/message', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message: newMsg.content }),
    })
      .then(res => {
        if (!res.ok) throw new Error(`Server returned ${res.status}`);
        return res.json();
      })
      .then(data => {
        setMessages(prev => [...prev, {
          id: (Date.now() + 1).toString(),
          role: 'assistant',
          content: data.response || 'No response received.',
          skill: data.skill_used || undefined,
        }]);
        setIsTyping(false);
      })
      .catch(err => {
        setMessages(prev => [...prev, {
          id: (Date.now() + 1).toString(),
          role: 'assistant',
          content: `Connection error: ${err.message}. Is the backend running on port 8000?`,
        }]);
        setIsTyping(false);
      });
  };

  return (
    <div className="chat-container">
      <div className="messages-list">
        {messages.map(msg => (
          <div key={msg.id} className={`message-wrapper ${msg.role}`}>
            <div className={`message-bubble message-${msg.role}`}>
              {msg.skill && <span className="skill-badge">{msg.skill}</span>}
              <ReactMarkdown remarkPlugins={[remarkGfm]}>
                {msg.content}
              </ReactMarkdown>
            </div>
          </div>
        ))}
        {isTyping && (
          <div className="message-wrapper assistant">
            <div className="message-bubble message-assistant typing-indicator">
              <span></span><span></span><span></span>
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      <form className="input-bar" onSubmit={handleSend}>
        <input
          type="text"
          className="input-field"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Ask Aurora something..."
        />
        <button type="submit" className="send-button" disabled={!input.trim()}>
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <line x1="22" y1="2" x2="11" y2="13"></line>
            <polygon points="22 2 15 22 11 13 2 9 22 2"></polygon>
          </svg>
        </button>
      </form>
    </div>
  );
}
