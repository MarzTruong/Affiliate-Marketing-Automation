"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api-client";
import type { Publication, ContentPiece } from "@/lib/types";

const statusLabels: Record<string, string> = {
  pending: "Chờ xử lý",
  scheduled: "Đã lên lịch",
  publishing: "Đang đăng",
  published: "Đã đăng",
  failed: "Thất bại",
};

const statusColors: Record<string, string> = {
  pending: "bg-gray-100 text-gray-700",
  scheduled: "bg-blue-100 text-blue-700",
  publishing: "bg-yellow-100 text-yellow-700",
  published: "bg-green-100 text-green-700",
  failed: "bg-red-100 text-red-700",
};

const CH_LABELS: Record<string, string> = {
  facebook: "📘 Facebook",
  wordpress: "🌐 WordPress",
  telegram: "✈️ Telegram",
  tiktok: "🎵 TikTok",
};

export default function PublisherPage() {
  const queryClient = useQueryClient();
  const [selectedContent, setSelectedContent] = useState("");
  const [selectedChannels, setSelectedChannels] = useState<string[]>([]);
  const [publishMode, setPublishMode] = useState<"immediate" | "scheduled">("immediate");
  const [scheduledAt, setScheduledAt] = useState("");
  const [activeTab, setActiveTab] = useState<"publish" | "history">("publish");

  const { data: publications, isLoading } = useQuery<Publication[]>({
    queryKey: ["publications"],
    queryFn: () => apiFetch("/publisher/publications"),
  });

  const { data: channels } = useQuery<{ channels: string[] }>({
    queryKey: ["publisher-channels"],
    queryFn: () => apiFetch("/publisher/channels"),
  });

  const { data: contentList } = useQuery<ContentPiece[]>({
    queryKey: ["content-list"],
    queryFn: () => apiFetch("/content"),
  });

  const publishMutation = useMutation({
    mutationFn: (data: { content_id: string; channels: string[] }) =>
      apiFetch("/publisher/publish", {
        method: "POST",
        body: JSON.stringify(data),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["publications"] });
      resetForm();
    },
  });

  const scheduleMutation = useMutation({
    mutationFn: (data: { content_id: string; channels: string[]; scheduled_at: string }) =>
      apiFetch("/publisher/schedule", {
        method: "POST",
        body: JSON.stringify(data),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["publications"] });
      resetForm();
    },
  });

  const resetForm = () => {
    setSelectedContent("");
    setSelectedChannels([]);
    setScheduledAt("");
  };

  const toggleChannel = (ch: string) =>
    setSelectedChannels((prev) =>
      prev.includes(ch) ? prev.filter((c) => c !== ch) : [...prev, ch]
    );

  const handleSubmit = () => {
    if (!selectedContent || selectedChannels.length === 0) return;
    if (publishMode === "immediate") {
      publishMutation.mutate({ content_id: selectedContent, channels: selectedChannels });
    } else {
      if (!scheduledAt) return;
      scheduleMutation.mutate({
        content_id: selectedContent,
        channels: selectedChannels,
        scheduled_at: new Date(scheduledAt).toISOString(),
      });
    }
  };

  const isPending = publishMutation.isPending || scheduleMutation.isPending;
  const isError = publishMutation.isError || scheduleMutation.isError;
  const errorMsg = ((publishMutation.error || scheduleMutation.error) as Error)?.message;

  const scheduledPubs = publications?.filter((p) => p.status === "scheduled") ?? [];
  const historyPubs = publications?.filter((p) => p.status !== "scheduled") ?? [];

  return (
    <div>
      <h1 className="text-2xl font-bold text-gray-900 mb-6">Đăng bài</h1>

      {/* Publish Form */}
      <div className="bg-white rounded-xl shadow-sm border p-6 mb-6">
        <h2 className="text-lg font-semibold mb-4">Đăng nội dung mới</h2>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
          {/* Content select */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Chọn nội dung</label>
            <select
              value={selectedContent}
              onChange={(e) => setSelectedContent(e.target.value)}
              className="w-full border rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500 focus:outline-none"
            >
              <option value="">-- Chọn nội dung --</option>
              {contentList?.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.title || `[${c.content_type}] ${c.id.slice(0, 8)}`}
                </option>
              ))}
            </select>
          </div>

          {/* Channels */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Kênh đăng bài</label>
            <div className="flex flex-wrap gap-2">
              {channels?.channels.map((ch) => (
                <button
                  key={ch}
                  onClick={() => toggleChannel(ch)}
                  className={`px-3 py-1.5 rounded-lg text-sm border transition-colors ${
                    selectedChannels.includes(ch)
                      ? "bg-blue-600 text-white border-blue-600"
                      : "bg-white text-gray-700 border-gray-300 hover:border-blue-400"
                  }`}
                >
                  {CH_LABELS[ch] ?? ch.charAt(0).toUpperCase() + ch.slice(1)}
                </button>
              ))}
            </div>
          </div>
        </div>

        {/* Publish mode */}
        <div className="flex gap-6 mb-4">
          <label className="flex items-center gap-2 text-sm cursor-pointer">
            <input
              type="radio"
              name="publishMode"
              checked={publishMode === "immediate"}
              onChange={() => setPublishMode("immediate")}
              className="accent-blue-600"
            />
            <span className="font-medium">Đăng ngay</span>
          </label>
          <label className="flex items-center gap-2 text-sm cursor-pointer">
            <input
              type="radio"
              name="publishMode"
              checked={publishMode === "scheduled"}
              onChange={() => setPublishMode("scheduled")}
              className="accent-blue-600"
            />
            <span className="font-medium">Lên lịch đăng</span>
          </label>
        </div>

        {/* Schedule datetime */}
        {publishMode === "scheduled" && (
          <div className="mb-4">
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Thời gian đăng bài
            </label>
            <input
              type="datetime-local"
              value={scheduledAt}
              onChange={(e) => setScheduledAt(e.target.value)}
              min={new Date().toISOString().slice(0, 16)}
              className="border rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500 focus:outline-none"
            />
          </div>
        )}

        <button
          onClick={handleSubmit}
          disabled={
            !selectedContent ||
            selectedChannels.length === 0 ||
            (publishMode === "scheduled" && !scheduledAt) ||
            isPending
          }
          className="bg-blue-600 text-white px-6 py-2 rounded-lg text-sm font-medium hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {isPending
            ? "Đang xử lý..."
            : publishMode === "immediate"
            ? "Đăng ngay"
            : "Lên lịch"}
        </button>

        {isError && (
          <p className="text-red-600 text-sm mt-2">Lỗi: {errorMsg}</p>
        )}
        {(publishMutation.isSuccess || scheduleMutation.isSuccess) && (
          <p className="text-green-600 text-sm mt-2">
            {publishMode === "immediate" ? "Đã đăng thành công!" : "Đã lên lịch thành công!"}
          </p>
        )}
      </div>

      {/* Scheduled publications */}
      {scheduledPubs.length > 0 && (
        <div className="bg-white rounded-xl shadow-sm border p-6 mb-6">
          <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
            Đã lên lịch
            <span className="px-2 py-0.5 bg-blue-100 text-blue-700 rounded-full text-xs font-medium">
              {scheduledPubs.length}
            </span>
          </h2>
          <div className="space-y-3">
            {scheduledPubs.map((pub) => {
              const chName = pub.channel || pub.platform;
              return (
                <div key={pub.id} className="flex items-center justify-between p-3 bg-blue-50 rounded-lg border border-blue-100">
                  <div className="flex items-center gap-3">
                    <span className="font-medium text-sm">
                      {CH_LABELS[chName] ?? chName}
                    </span>
                    {pub.scheduled_at && (
                      <span className="text-sm text-gray-600">
                        ⏰ {new Date(pub.scheduled_at).toLocaleString("vi-VN")}
                      </span>
                    )}
                  </div>
                  <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${statusColors.scheduled}`}>
                    Đã lên lịch
                  </span>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* History */}
      <div className="bg-white rounded-xl shadow-sm border p-6">
        {/* Tabs */}
        <div className="flex gap-1 mb-4 bg-gray-100 rounded-lg p-1 w-fit">
          <button
            onClick={() => setActiveTab("publish")}
            className={`px-3 py-1.5 rounded-md text-sm font-medium transition-colors ${
              activeTab === "publish" ? "bg-white text-gray-900 shadow-sm" : "text-gray-500"
            }`}
          >
            Đã đăng ({historyPubs.filter((p) => p.status === "published").length})
          </button>
          <button
            onClick={() => setActiveTab("history")}
            className={`px-3 py-1.5 rounded-md text-sm font-medium transition-colors ${
              activeTab === "history" ? "bg-white text-gray-900 shadow-sm" : "text-gray-500"
            }`}
          >
            Tất cả ({historyPubs.length})
          </button>
        </div>

        {isLoading ? (
          <div className="text-center py-8 text-gray-400">Đang tải...</div>
        ) : historyPubs.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b text-left text-gray-500">
                  <th className="pb-3 pr-4">Kênh</th>
                  <th className="pb-3 pr-4">Trạng thái</th>
                  <th className="pb-3 pr-4">Mã bài đăng</th>
                  <th className="pb-3">Thời gian</th>
                </tr>
              </thead>
              <tbody>
                {(activeTab === "publish"
                  ? historyPubs.filter((p) => p.status === "published")
                  : historyPubs
                ).map((pub) => {
                  const chName = pub.channel || pub.platform;
                  return (
                    <tr key={pub.id} className="border-b last:border-0">
                      <td className="py-3 pr-4 font-medium">
                        {CH_LABELS[chName] ?? chName.charAt(0).toUpperCase() + chName.slice(1)}
                      </td>
                      <td className="py-3 pr-4">
                        <span
                          className={`px-2 py-0.5 rounded-full text-xs font-medium ${
                            statusColors[pub.status] || "bg-gray-100 text-gray-700"
                          }`}
                        >
                          {statusLabels[pub.status] || pub.status}
                        </span>
                      </td>
                      <td className="py-3 pr-4 text-gray-500 font-mono text-xs">
                        {pub.external_post_id || "—"}
                      </td>
                      <td className="py-3 text-gray-500">
                        {pub.published_at
                          ? new Date(pub.published_at).toLocaleString("vi-VN")
                          : pub.scheduled_at
                          ? `⏰ ${new Date(pub.scheduled_at).toLocaleString("vi-VN")}`
                          : "—"}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        ) : (
          <p className="text-gray-400 text-center py-8">Chưa có bài đăng nào.</p>
        )}
      </div>
    </div>
  );
}
