"use client";

import { useState, useRef, useEffect, useCallback } from "react";
import { apiFetch } from "@/lib/api-client";
import type { ChatMessage } from "@/lib/types";

const QUICK_PROMPTS = [
  "Tìm SP điện tử Shopee hoa hồng từ 8%",
  "Tạo rule mới cho thời trang TikTok Shop",
  "Tuần này hiệu suất thế nào?",
  "Giờ nào đăng bài hiệu quả nhất?",
  "Chạy ngay pipeline đầu tiên",
  "Gửi báo cáo hôm nay qua Telegram",
];

export default function ChatPage() {
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      role: "assistant",
      content:
        "Xin chào! Tôi là AI Assistant của hệ thống Affiliate Marketing. Tôi có thể giúp bạn:\n\n" +
        "• 🤖 Tạo và quản lý automation rules\n" +
        "• 📝 Tạo content AI theo yêu cầu\n" +
        "• 📅 Lên lịch đăng bài\n" +
        "• 📊 Xem và phân tích hiệu suất\n" +
        "• 📱 Gửi báo cáo qua Telegram\n\n" +
        "Bạn muốn làm gì hôm nay?",
      timestamp: new Date().toISOString(),
    },
  ]);
  const [input, setInput] = useState("");
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const sendMessage = useCallback(async (text: string) => {
    if (!text.trim() || isLoading) return;

    const userMsg: ChatMessage = {
      role: "user",
      content: text.trim(),
      timestamp: new Date().toISOString(),
    };
    setMessages(prev => [...prev, userMsg]);
    setInput("");
    setIsLoading(true);

    try {
      const res = await apiFetch<{ reply: string; session_id: string }>("/chat", {
        method: "POST",
        body: JSON.stringify({ message: text.trim(), session_id: sessionId }),
      });

      setSessionId(res.session_id);
      setMessages(prev => [
        ...prev,
        { role: "assistant", content: res.reply, timestamp: new Date().toISOString() },
      ]);
    } catch (err) {
      setMessages(prev => [
        ...prev,
        {
          role: "assistant",
          content: `❌ Lỗi: ${err instanceof Error ? err.message : "Không thể kết nối"}\n\nKiểm tra ANTHROPIC_API_KEY trong file .env`,
          timestamp: new Date().toISOString(),
        },
      ]);
    } finally {
      setIsLoading(false);
      inputRef.current?.focus();
    }
  }, [isLoading, sessionId]);

  const handleKey = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage(input);
    }
  };

  const clearSession = async () => {
    if (sessionId) {
      await apiFetch(`/chat/${sessionId}`, { method: "DELETE" }).catch(() => {});
    }
    setSessionId(null);
    setMessages([{
      role: "assistant",
      content: "Đã bắt đầu cuộc hội thoại mới. Tôi có thể giúp gì cho bạn?",
      timestamp: new Date().toISOString(),
    }]);
  };

  return (
    <div className="flex flex-col h-[calc(100vh-4rem)]">
      {/* Header */}
      <div className="flex justify-between items-center mb-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">💬 AI Chat Assistant</h1>
          <p className="text-sm text-slate-500 mt-0.5">
            Điều khiển hệ thống bằng ngôn ngữ tự nhiên tiếng Việt
          </p>
        </div>
        <button
          onClick={clearSession}
          className="text-sm px-3 py-1.5 text-slate-500 hover:text-slate-700 hover:bg-slate-100 rounded-lg transition-colors"
        >
          🔄 Cuộc hội thoại mới
        </button>
      </div>

      {/* Quick prompts */}
      <div className="flex gap-2 flex-wrap mb-3">
        {QUICK_PROMPTS.map((p, i) => (
          <button
            key={i}
            onClick={() => sendMessage(p)}
            disabled={isLoading}
            className="text-xs px-3 py-1.5 bg-white border border-slate-200 text-slate-600 rounded-full hover:bg-blue-50 hover:border-blue-300 hover:text-blue-700 transition-colors disabled:opacity-50"
          >
            {p}
          </button>
        ))}
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto bg-white rounded-xl border shadow-sm p-4 space-y-4 mb-4">
        {messages.map((msg, i) => (
          <MessageBubble key={i} message={msg} />
        ))}

        {isLoading && (
          <div className="flex items-start gap-3">
            <div className="w-8 h-8 rounded-full bg-blue-600 flex items-center justify-center text-white text-sm shrink-0">
              AI
            </div>
            <div className="bg-slate-100 rounded-2xl rounded-tl-sm px-4 py-3">
              <div className="flex gap-1">
                {[0, 1, 2].map(i => (
                  <div
                    key={i}
                    className="w-2 h-2 bg-slate-400 rounded-full animate-bounce"
                    style={{ animationDelay: `${i * 0.15}s` }}
                  />
                ))}
              </div>
            </div>
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      {/* Input */}
      <div className="bg-white rounded-xl border shadow-sm p-3 flex gap-3 items-end">
        <textarea
          ref={inputRef}
          value={input}
          onChange={e => setInput(e.target.value)}
          onKeyDown={handleKey}
          rows={1}
          placeholder="Nhập yêu cầu... (Enter để gửi, Shift+Enter xuống dòng)"
          className="flex-1 resize-none text-sm text-slate-800 placeholder-slate-400 focus:outline-none leading-relaxed"
          style={{ maxHeight: "120px" }}
          disabled={isLoading}
        />
        <button
          onClick={() => sendMessage(input)}
          disabled={!input.trim() || isLoading}
          className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors text-sm font-medium shrink-0"
        >
          Gửi →
        </button>
      </div>
    </div>
  );
}

function MessageBubble({ message }: { message: ChatMessage }) {
  const isUser = message.role === "user";

  return (
    <div className={`flex items-start gap-3 ${isUser ? "flex-row-reverse" : ""}`}>
      {/* Avatar */}
      <div className={`w-8 h-8 rounded-full flex items-center justify-center text-white text-sm shrink-0 ${
        isUser ? "bg-slate-600" : "bg-blue-600"
      }`}>
        {isUser ? "Bạn" : "AI"}
      </div>

      {/* Bubble */}
      <div
        className={`max-w-[75%] px-4 py-3 rounded-2xl text-sm leading-relaxed whitespace-pre-wrap ${
          isUser
            ? "bg-blue-600 text-white rounded-tr-sm"
            : "bg-slate-100 text-slate-800 rounded-tl-sm"
        }`}
      >
        {message.content}
      </div>
    </div>
  );
}
