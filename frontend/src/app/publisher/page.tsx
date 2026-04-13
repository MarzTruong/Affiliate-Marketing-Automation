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

const VARIANT_PLATFORMS = ["tiktok", "facebook"] as const;
type VariantPlatform = (typeof VARIANT_PLATFORMS)[number];

const VARIANT_LABELS: Record<VariantPlatform, string> = {
  tiktok: "🎵 TikTok",
  facebook: "📘 Facebook",
};

interface ContentWithVariants extends ContentPiece {
  platform_variants?: Record<VariantPlatform, string> | null;
}

interface ManualLog {
  id: string;
  content_id: string;
  platform: string;
  published_at: string;
  note: string | null;
}

function CopyButton({ text, label }: { text: string; label: string }) {
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    if (!text) return;
    await navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <button
      onClick={handleCopy}
      disabled={!text}
      className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm font-medium transition-colors ${
        copied
          ? "bg-green-100 text-green-700 border border-green-300"
          : "bg-white text-gray-700 border border-gray-300 hover:border-blue-400 hover:text-blue-600"
      } disabled:opacity-40 disabled:cursor-not-allowed`}
    >
      {copied ? "✓ Đã copy!" : `📋 Copy ${label}`}
    </button>
  );
}

function VariantPanel({ content }: { content: ContentWithVariants | null }) {
  const [activeVariant, setActiveVariant] = useState<VariantPlatform>("tiktok");
  const [markedPlatforms, setMarkedPlatforms] = useState<Set<VariantPlatform>>(new Set());
  const queryClient = useQueryClient();

  const markMutation = useMutation({
    mutationFn: (platform: VariantPlatform) =>
      apiFetch("/publisher/mark-published", {
        method: "POST",
        body: JSON.stringify({ content_id: content?.id, platform }),
      }),
    onSuccess: (_data, platform) => {
      setMarkedPlatforms((prev) => new Set([...prev, platform]));
      queryClient.invalidateQueries({ queryKey: ["manual-logs"] });
    },
  });

  if (!content) {
    return (
      <div className="bg-gray-50 rounded-xl border border-dashed border-gray-300 p-8 text-center text-gray-400 text-sm">
        Chọn nội dung để xem bản copy cho từng kênh
      </div>
    );
  }

  const variants = content.platform_variants;
  const activeText = variants?.[activeVariant] || content.body;

  return (
    <div className="bg-white rounded-xl shadow-sm border p-5">
      <div className="flex items-center justify-between mb-3">
        <h3 className="font-semibold text-gray-800 text-sm truncate max-w-xs">
          {content.title || `[${content.content_type}]`}
        </h3>
        {!variants && (
          <span className="text-xs text-amber-600 bg-amber-50 px-2 py-0.5 rounded-full border border-amber-200">
            Chưa có variants — hiển thị body gốc
          </span>
        )}
      </div>

      {/* Tabs */}
      <div className="flex gap-1 mb-3 bg-gray-100 rounded-lg p-1 w-fit">
        {VARIANT_PLATFORMS.map((p) => (
          <button
            key={p}
            onClick={() => setActiveVariant(p)}
            className={`px-3 py-1.5 rounded-md text-xs font-medium transition-colors ${
              activeVariant === p
                ? "bg-white text-gray-900 shadow-sm"
                : "text-gray-500 hover:text-gray-700"
            }`}
          >
            {VARIANT_LABELS[p]}
          </button>
        ))}
      </div>

      {/* Content preview */}
      <div className="bg-gray-50 rounded-lg p-3 mb-3 min-h-[100px] max-h-[200px] overflow-y-auto">
        <p className="text-sm text-gray-700 whitespace-pre-wrap leading-relaxed">
          {activeText || (
            <span className="text-gray-400 italic">Chưa có nội dung cho kênh này</span>
          )}
        </p>
      </div>

      {/* Copy buttons */}
      <div className="flex flex-wrap gap-2 mb-4">
        {VARIANT_PLATFORMS.map((p) => (
          <CopyButton
            key={p}
            text={variants?.[p] || content.body}
            label={p === "tiktok" ? "TikTok" : p === "facebook" ? "Facebook" : "Telegram"}
          />
        ))}
      </div>

      {/* Mark published */}
      <div className="border-t pt-3">
        <p className="text-xs text-gray-500 mb-2 font-medium">Đánh dấu đã đăng thủ công:</p>
        <div className="flex flex-wrap gap-2">
          {VARIANT_PLATFORMS.map((p) => {
            const isDone = markedPlatforms.has(p);
            const isLoading = markMutation.isPending && markMutation.variables === p;
            return (
              <button
                key={p}
                onClick={() => !isDone && markMutation.mutate(p)}
                disabled={isDone || isLoading}
                className={`px-3 py-1.5 rounded-lg text-xs font-medium border transition-colors ${
                  isDone
                    ? "bg-green-50 text-green-700 border-green-300 cursor-default"
                    : "bg-white text-gray-600 border-gray-300 hover:border-green-400 hover:text-green-600"
                } disabled:opacity-60`}
              >
                {isDone ? `✓ ${VARIANT_LABELS[p]} đã đăng` : `Đánh dấu ${VARIANT_LABELS[p]}`}
              </button>
            );
          })}
        </div>
        {markMutation.isError && (
          <p className="text-red-500 text-xs mt-1">
            Lỗi: {(markMutation.error as Error)?.message}
          </p>
        )}
      </div>
    </div>
  );
}

export default function PublisherPage() {
  const queryClient = useQueryClient();
  const [selectedContent, setSelectedContent] = useState("");
  const [selectedChannels, setSelectedChannels] = useState<string[]>([]);
  const [publishMode, setPublishMode] = useState<"immediate" | "scheduled">("immediate");
  const [scheduledAt, setScheduledAt] = useState("");
  const [activeTab, setActiveTab] = useState<"manual" | "auto" | "history">("manual");

  const { data: publications, isLoading } = useQuery<Publication[]>({
    queryKey: ["publications"],
    queryFn: () => apiFetch("/publisher/publications"),
  });

  const { data: channels } = useQuery<{ channels: string[] }>({
    queryKey: ["publisher-channels"],
    queryFn: () => apiFetch("/publisher/channels"),
  });

  const { data: contentList } = useQuery<ContentWithVariants[]>({
    queryKey: ["content-list"],
    queryFn: () => apiFetch("/content"),
  });

  const { data: manualLogs } = useQuery<ManualLog[]>({
    queryKey: ["manual-logs"],
    queryFn: () => apiFetch("/publisher/manual-logs"),
  });

  const selectedContentObj = contentList?.find((c) => c.id === selectedContent) ?? null;

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
      <h1 className="text-2xl font-bold text-gray-900 mb-2">Đăng bài</h1>
      <p className="text-sm text-gray-500 mb-6">
        Copy nội dung tối ưu theo từng kênh hoặc đăng tự động (Telegram).
      </p>

      {/* Tabs */}
      <div className="flex gap-1 mb-6 bg-gray-100 rounded-lg p-1 w-fit">
        <button
          onClick={() => setActiveTab("manual")}
          className={`px-4 py-2 rounded-md text-sm font-medium transition-colors ${
            activeTab === "manual" ? "bg-white text-gray-900 shadow-sm" : "text-gray-500"
          }`}
        >
          📋 Copy & Đăng thủ công
        </button>
        <button
          onClick={() => setActiveTab("auto")}
          className={`px-4 py-2 rounded-md text-sm font-medium transition-colors ${
            activeTab === "auto" ? "bg-white text-gray-900 shadow-sm" : "text-gray-500"
          }`}
        >
          ✈️ Đăng tự động (Telegram)
        </button>
        <button
          onClick={() => setActiveTab("history")}
          className={`px-4 py-2 rounded-md text-sm font-medium transition-colors ${
            activeTab === "history" ? "bg-white text-gray-900 shadow-sm" : "text-gray-500"
          }`}
        >
          📊 Lịch sử ({(manualLogs?.length ?? 0) + historyPubs.length})
        </button>
      </div>

      {/* Tab: Manual copy */}
      {activeTab === "manual" && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Left: content selector */}
          <div className="bg-white rounded-xl shadow-sm border p-5">
            <h2 className="text-base font-semibold mb-4 text-gray-800">Chọn nội dung</h2>
            <select
              value={selectedContent}
              onChange={(e) => setSelectedContent(e.target.value)}
              className="w-full border rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500 focus:outline-none mb-3"
            >
              <option value="">-- Chọn nội dung --</option>
              {contentList?.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.title || `[${c.content_type}] ${c.id.slice(0, 8)}`}
                </option>
              ))}
            </select>
            <p className="text-xs text-gray-400">
              Chọn bài → copy nội dung đã tối ưu theo từng kênh → dán vào app TikTok / Facebook.
            </p>
          </div>

          {/* Right: variant panel */}
          <VariantPanel content={selectedContentObj} />
        </div>
      )}

      {/* Tab: Auto publish */}
      {activeTab === "auto" && (
        <div className="bg-white rounded-xl shadow-sm border p-6">
          <h2 className="text-lg font-semibold mb-4">Đăng tự động</h2>
          <div className="inline-flex items-center gap-2 bg-blue-50 text-blue-700 text-sm px-3 py-1.5 rounded-full mb-4">
            ✈️ Telegram đang hoạt động
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
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

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Kênh đăng bài</label>
              <div className="flex flex-wrap gap-2">
                {channels?.channels.filter((ch) => ch !== "telegram").map((ch) => (
                  <button
                    key={ch}
                    onClick={() => toggleChannel(ch)}
                    className={`px-3 py-1.5 rounded-lg text-sm border transition-colors ${
                      selectedChannels.includes(ch)
                        ? "bg-blue-600 text-white border-blue-600"
                        : "bg-white text-gray-700 border-gray-300 hover:border-blue-400"
                    }`}
                  >
                    {CH_LABELS[ch] ?? ch}
                  </button>
                ))}
              </div>
            </div>
          </div>

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

          {isError && <p className="text-red-600 text-sm mt-2">Lỗi: {errorMsg}</p>}
          {(publishMutation.isSuccess || scheduleMutation.isSuccess) && (
            <p className="text-green-600 text-sm mt-2">
              {publishMode === "immediate" ? "Đã đăng thành công!" : "Đã lên lịch thành công!"}
            </p>
          )}

          {/* Scheduled queue */}
          {scheduledPubs.length > 0 && (
            <div className="mt-6 border-t pt-4">
              <h3 className="text-sm font-semibold mb-3 text-gray-700">
                Đã lên lịch ({scheduledPubs.length})
              </h3>
              <div className="space-y-2">
                {scheduledPubs.map((pub) => {
                  const chName = pub.channel || pub.platform;
                  return (
                    <div
                      key={pub.id}
                      className="flex items-center justify-between p-3 bg-blue-50 rounded-lg border border-blue-100 text-sm"
                    >
                      <span className="font-medium">{CH_LABELS[chName] ?? chName}</span>
                      {pub.scheduled_at && (
                        <span className="text-gray-600 text-xs">
                          ⏰ {new Date(pub.scheduled_at).toLocaleString("vi-VN")}
                        </span>
                      )}
                    </div>
                  );
                })}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Tab: History */}
      {activeTab === "history" && (
        <div className="space-y-6">
          {/* Manual logs */}
          {(manualLogs?.length ?? 0) > 0 && (
            <div className="bg-white rounded-xl shadow-sm border p-6">
              <h2 className="text-base font-semibold mb-4 text-gray-800">
                Đăng thủ công ({manualLogs!.length})
              </h2>
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b text-left text-gray-500">
                      <th className="pb-3 pr-4">Kênh</th>
                      <th className="pb-3 pr-4">Content ID</th>
                      <th className="pb-3 pr-4">Thời gian</th>
                      <th className="pb-3">Ghi chú</th>
                    </tr>
                  </thead>
                  <tbody>
                    {manualLogs!.map((log) => (
                      <tr key={log.id} className="border-b last:border-0">
                        <td className="py-3 pr-4 font-medium">
                          {CH_LABELS[log.platform] ?? log.platform}
                        </td>
                        <td className="py-3 pr-4 font-mono text-xs text-gray-500">
                          {log.content_id.slice(0, 8)}...
                        </td>
                        <td className="py-3 pr-4 text-gray-500 text-xs">
                          {new Date(log.published_at).toLocaleString("vi-VN")}
                        </td>
                        <td className="py-3 text-gray-500 text-xs">{log.note || "—"}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* Auto publish history */}
          <div className="bg-white rounded-xl shadow-sm border p-6">
            <h2 className="text-base font-semibold mb-4 text-gray-800">
              Đăng tự động ({historyPubs.length})
            </h2>
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
                    {historyPubs.map((pub) => {
                      const chName = pub.channel || pub.platform;
                      return (
                        <tr key={pub.id} className="border-b last:border-0">
                          <td className="py-3 pr-4 font-medium">
                            {CH_LABELS[chName] ?? chName}
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
                          <td className="py-3 text-gray-500 text-xs">
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
      )}
    </div>
  );
}
