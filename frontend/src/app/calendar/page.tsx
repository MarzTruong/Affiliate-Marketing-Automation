"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api-client";
import type { WeekCalendar, CalendarDay } from "@/lib/types";

const CHANNEL_STYLES: Record<string, string> = {
  facebook: "bg-blue-100 text-blue-800 border-blue-200",
  wordpress: "bg-orange-100 text-orange-800 border-orange-200",
  tiktok: "bg-slate-900 text-white border-slate-700",
  telegram: "bg-cyan-100 text-cyan-800 border-cyan-200",
};

const CHANNEL_ICONS: Record<string, string> = {
  facebook: "📘",
  wordpress: "🌐",
  tiktok: "🎵",
  telegram: "✈️",
};

const STATUS_ICONS: Record<string, string> = {
  scheduled: "🕐",
  published: "✅",
  failed: "❌",
  cancelled: "⭕",
};

const DAY_NAMES = ["Thứ 2", "Thứ 3", "Thứ 4", "Thứ 5", "Thứ 6", "Thứ 7", "CN"];

export default function CalendarPage() {
  const [weekOffset, setWeekOffset] = useState(0);

  const { data: calendar, isLoading } = useQuery<WeekCalendar>({
    queryKey: ["calendar-week", weekOffset],
    queryFn: () => apiFetch(`/calendar/week?week_offset=${weekOffset}`),
  });

  const totalPosts = calendar
    ? Object.values(calendar.days).reduce((s, posts) => s + posts.length, 0)
    : 0;

  const publishedCount = calendar
    ? Object.values(calendar.days)
        .flat()
        .filter(p => p.status === "published").length
    : 0;

  return (
    <div>
      {/* Header */}
      <div className="flex justify-between items-center mb-6">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">📅 Lịch đăng bài</h1>
          <p className="text-sm text-slate-500 mt-1">
            {calendar ? `${formatDate(calendar.week_start)} – ${formatDate(calendar.week_end)}` : ""}
            {totalPosts > 0 && ` • ${publishedCount}/${totalPosts} đã đăng`}
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => setWeekOffset(v => v - 1)}
            className="p-2 text-slate-600 hover:bg-slate-100 rounded-lg transition-colors"
          >
            ←
          </button>
          <button
            onClick={() => setWeekOffset(0)}
            className={`px-3 py-1.5 text-sm rounded-lg transition-colors ${
              weekOffset === 0 ? "bg-blue-600 text-white" : "bg-slate-100 text-slate-600 hover:bg-slate-200"
            }`}
          >
            Tuần này
          </button>
          <button
            onClick={() => setWeekOffset(v => v + 1)}
            className="p-2 text-slate-600 hover:bg-slate-100 rounded-lg transition-colors"
          >
            →
          </button>
        </div>
      </div>

      {/* Legend */}
      <div className="flex gap-3 mb-4 flex-wrap">
        {Object.entries(CHANNEL_ICONS).map(([ch, icon]) => (
          <span key={ch} className={`text-xs px-2.5 py-1 rounded-full border ${CHANNEL_STYLES[ch]}`}>
            {icon} {ch}
          </span>
        ))}
        <span className="text-xs px-2.5 py-1 rounded-full text-slate-500 bg-slate-100">
          🕐 lên lịch &nbsp;✅ đã đăng &nbsp;❌ thất bại
        </span>
      </div>

      {/* Calendar Grid */}
      {isLoading ? (
        <div className="grid grid-cols-7 gap-2">
          {Array.from({ length: 7 }).map((_, i) => (
            <div key={i} className="h-64 bg-slate-200 rounded-xl animate-pulse" />
          ))}
        </div>
      ) : calendar ? (
        <div className="grid grid-cols-7 gap-2">
          {Object.entries(calendar.days).map(([date, posts], idx) => {
            const isToday = date === new Date().toISOString().slice(0, 10);
            return (
              <div
                key={date}
                className={`rounded-xl border min-h-[240px] p-2 ${
                  isToday ? "border-blue-400 bg-blue-50" : "border-slate-200 bg-white"
                }`}
              >
                {/* Day header */}
                <div className="mb-2 text-center">
                  <div className="text-xs text-slate-500">{DAY_NAMES[idx]}</div>
                  <div className={`text-sm font-bold ${isToday ? "text-blue-600" : "text-slate-800"}`}>
                    {date.slice(8)}
                  </div>
                  {posts.length > 0 && (
                    <div className="text-xs text-slate-400">{posts.length} bài</div>
                  )}
                </div>

                {/* Posts */}
                <div className="space-y-1.5">
                  {posts.length === 0 ? (
                    <div className="text-center text-slate-300 text-xs py-6">
                      —
                    </div>
                  ) : (
                    posts.map(post => <PostCard key={post.id} post={post} />)
                  )}
                </div>
              </div>
            );
          })}
        </div>
      ) : null}

      {/* Stats */}
      {calendar && totalPosts > 0 && (
        <div className="mt-6 bg-white rounded-xl shadow-sm border p-4">
          <h2 className="text-sm font-semibold text-slate-700 mb-3">Thống kê tuần</h2>
          <ChannelBreakdown calendar={calendar} />
        </div>
      )}
    </div>
  );
}

function PostCard({ post }: { post: CalendarDay }) {
  return (
    <div
      className={`rounded-lg border px-2 py-1.5 text-xs ${CHANNEL_STYLES[post.channel] ?? "bg-slate-100 border-slate-200 text-slate-700"}`}
      title={post.title}
    >
      <div className="flex items-center justify-between gap-1">
        <span>{CHANNEL_ICONS[post.channel] ?? "📄"}</span>
        <span className="font-medium truncate flex-1">{post.hour}</span>
        <span>{STATUS_ICONS[post.status] ?? "?"}</span>
      </div>
      <div className="truncate mt-0.5 opacity-80">{post.title}</div>
    </div>
  );
}

function ChannelBreakdown({ calendar }: { calendar: WeekCalendar }) {
  const counts: Record<string, number> = {};
  Object.values(calendar.days)
    .flat()
    .forEach(p => { counts[p.channel] = (counts[p.channel] ?? 0) + 1; });

  return (
    <div className="flex gap-4 flex-wrap">
      {Object.entries(counts).map(([ch, cnt]) => (
        <div key={ch} className="text-sm">
          <span>{CHANNEL_ICONS[ch] ?? "📄"}</span>{" "}
          <span className="capitalize text-slate-600">{ch}</span>{" "}
          <span className="font-semibold text-slate-900">{cnt}</span>
        </div>
      ))}
    </div>
  );
}

function formatDate(dateStr: string) {
  return new Date(dateStr).toLocaleDateString("vi-VN", { day: "2-digit", month: "2-digit" });
}
