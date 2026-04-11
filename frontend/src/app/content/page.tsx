"use client";

import { useState, useCallback } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api-client";
import type { Campaign, ContentPiece, Product } from "@/lib/types";

const TYPE_OPTIONS = [
  { value: "product_description", label: "Mô tả sản phẩm" },
  { value: "seo_article", label: "Bài viết SEO" },
  { value: "social_post", label: "Bài đăng MXH" },
  { value: "video_script", label: "Kịch bản video" },
];

const STATUS_COLORS: Record<string, string> = {
  draft: "bg-gray-100 text-gray-700",
  published: "bg-green-100 text-green-700",
  archived: "bg-yellow-100 text-yellow-700",
};

const STATUS_LABELS: Record<string, string> = {
  draft: "Nháp",
  published: "Đã đăng",
  archived: "Lưu trữ",
};

const CH_LABELS: Record<string, string> = {
  facebook: "📘 Facebook",
  wordpress: "🌐 WordPress",
  telegram: "✈️ Telegram",
  tiktok: "🎵 TikTok",
};

// ── Preview & Publish Modal ──────────────────────────────────────────
function PreviewModal({
  piece,
  channels,
  onClose,
}: {
  piece: ContentPiece;
  channels: string[];
  onClose: () => void;
}) {
  const [selectedChannels, setSelectedChannels] = useState<string[]>([]);
  const [publishMode, setPublishMode] = useState<"immediate" | "scheduled">("immediate");
  const [scheduledAt, setScheduledAt] = useState("");
  const [publishing, setPublishing] = useState(false);
  const [done, setDone] = useState(false);
  const [error, setError] = useState("");

  const toggleChannel = (ch: string) =>
    setSelectedChannels((prev) =>
      prev.includes(ch) ? prev.filter((c) => c !== ch) : [...prev, ch]
    );

  const handlePublish = async () => {
    if (selectedChannels.length === 0) return;
    setPublishing(true);
    setError("");
    try {
      if (publishMode === "immediate") {
        await apiFetch("/publisher/publish", {
          method: "POST",
          body: JSON.stringify({ content_id: piece.id, channels: selectedChannels }),
        });
      } else {
        if (!scheduledAt) { setError("Chọn thời gian lên lịch"); setPublishing(false); return; }
        await apiFetch("/publisher/schedule", {
          method: "POST",
          body: JSON.stringify({
            content_id: piece.id,
            channels: selectedChannels,
            scheduled_at: new Date(scheduledAt).toISOString(),
          }),
        });
      }
      setDone(true);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setPublishing(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4" onClick={onClose}>
      <div
        className="bg-white rounded-2xl shadow-2xl w-full max-w-3xl max-h-[90vh] flex flex-col"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Modal header */}
        <div className="flex items-start justify-between p-5 border-b shrink-0">
          <div>
            <h2 className="text-lg font-bold text-gray-900">{piece.title || "Xem trước nội dung"}</h2>
            <div className="flex flex-wrap gap-2 mt-1">
              <span className="px-2 py-0.5 bg-blue-50 text-blue-700 rounded text-xs">
                {TYPE_OPTIONS.find((t) => t.value === piece.content_type)?.label || piece.content_type}
              </span>
              {piece.claude_model && (
                <span className="px-2 py-0.5 bg-purple-50 text-purple-700 rounded text-xs">
                  {piece.claude_model}
                </span>
              )}
              {piece.estimated_cost_usd != null && (
                <span className="px-2 py-0.5 bg-green-50 text-green-700 rounded text-xs">
                  ${Number(piece.estimated_cost_usd).toFixed(4)}
                </span>
              )}
            </div>
          </div>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600 text-xl p-1">✕</button>
        </div>

        {/* Content preview */}
        <div className="flex-1 overflow-y-auto p-5">
          <pre className="text-sm text-gray-700 whitespace-pre-wrap font-sans leading-relaxed bg-gray-50 rounded-xl p-4 border">
            {piece.body}
          </pre>
          {piece.seo_keywords && piece.seo_keywords.length > 0 && (
            <div className="flex gap-2 mt-4 flex-wrap items-center">
              <span className="text-xs font-medium text-gray-500">Từ khóa SEO:</span>
              {piece.seo_keywords.map((kw) => (
                <span key={kw} className="px-2 py-0.5 bg-white border text-gray-600 rounded text-xs">
                  {kw}
                </span>
              ))}
            </div>
          )}
        </div>

        {/* Publish controls */}
        {!done ? (
          <div className="border-t p-5 shrink-0 space-y-3">
            {/* Channels */}
            <div>
              <p className="text-sm font-medium text-gray-700 mb-2">Chọn kênh đăng bài</p>
              <div className="flex flex-wrap gap-2">
                {channels.map((ch) => (
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

            {/* Mode toggle */}
            <div className="flex gap-4">
              <label className="flex items-center gap-2 text-sm cursor-pointer">
                <input type="radio" name="mode" checked={publishMode === "immediate"}
                  onChange={() => setPublishMode("immediate")} className="accent-blue-600" />
                Đăng ngay
              </label>
              <label className="flex items-center gap-2 text-sm cursor-pointer">
                <input type="radio" name="mode" checked={publishMode === "scheduled"}
                  onChange={() => setPublishMode("scheduled")} className="accent-blue-600" />
                Lên lịch
              </label>
            </div>

            {publishMode === "scheduled" && (
              <input
                type="datetime-local"
                value={scheduledAt}
                onChange={(e) => setScheduledAt(e.target.value)}
                min={new Date().toISOString().slice(0, 16)}
                className="border rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500 focus:outline-none"
              />
            )}

            <div className="flex items-center gap-3">
              <button
                onClick={handlePublish}
                disabled={selectedChannels.length === 0 || publishing}
                className="bg-blue-600 text-white px-6 py-2 rounded-lg text-sm font-medium hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {publishing
                  ? "Đang xử lý..."
                  : publishMode === "immediate"
                  ? "Đăng ngay"
                  : "Lên lịch đăng"}
              </button>
              {error && <p className="text-red-600 text-sm">{error}</p>}
            </div>
          </div>
        ) : (
          <div className="border-t p-5 shrink-0 text-center">
            <p className="text-green-600 font-medium">
              {publishMode === "immediate" ? "Đã đăng thành công!" : "Đã lên lịch thành công!"}
            </p>
            <button onClick={onClose} className="mt-2 text-sm text-gray-500 hover:text-gray-700 underline">
              Đóng
            </button>
          </div>
        )}
      </div>
    </div>
  );
}

// ── Main page ────────────────────────────────────────────────────────
export default function ContentPage() {
  const queryClient = useQueryClient();
  const [showForm, setShowForm] = useState(false);
  const [selectedCampaign, setSelectedCampaign] = useState("");
  const [selectedProducts, setSelectedProducts] = useState<string[]>([]);
  const [contentType, setContentType] = useState("product_description");
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [previewPiece, setPreviewPiece] = useState<ContentPiece | null>(null);

  // Bulk generation progress
  const [progress, setProgress] = useState<{ current: number; total: number } | null>(null);
  const [genError, setGenError] = useState("");
  const [regeneratingId, setRegeneratingId] = useState<string | null>(null);

  const { data: campaigns } = useQuery<Campaign[]>({
    queryKey: ["campaigns"],
    queryFn: () => apiFetch("/campaigns"),
  });

  const { data: products } = useQuery<Product[]>({
    queryKey: ["products", selectedCampaign],
    queryFn: () => apiFetch(`/campaigns/${selectedCampaign}/products`),
    enabled: !!selectedCampaign,
  });

  const { data: content, isLoading } = useQuery<ContentPiece[]>({
    queryKey: ["content"],
    queryFn: () => apiFetch("/content?limit=50"),
  });

  const { data: channelsData } = useQuery<{ channels: string[] }>({
    queryKey: ["publisher-channels"],
    queryFn: () => apiFetch("/publisher/channels"),
  });

  const toggleProduct = (id: string) =>
    setSelectedProducts((prev) =>
      prev.includes(id) ? prev.filter((p) => p !== id) : [...prev, id]
    );

  const selectAll = () => setSelectedProducts(products?.map((p) => p.id) ?? []);
  const clearAll = () => setSelectedProducts([]);

  const handleGenerate = useCallback(async () => {
    if (!selectedCampaign || selectedProducts.length === 0) return;
    setGenError("");
    setProgress({ current: 0, total: selectedProducts.length });

    try {
      for (let i = 0; i < selectedProducts.length; i++) {
        setProgress({ current: i + 1, total: selectedProducts.length });
        await apiFetch("/content/generate", {
          method: "POST",
          body: JSON.stringify({
            product_ids: [selectedProducts[i]],
            campaign_id: selectedCampaign,
            content_type: contentType,
          }),
        });
        // Refresh list after each item so user sees results appearing
        queryClient.invalidateQueries({ queryKey: ["content"] });
      }
    } catch (e) {
      setGenError((e as Error).message);
    } finally {
      setProgress(null);
      setShowForm(false);
      setSelectedCampaign("");
      setSelectedProducts([]);
      setContentType("product_description");
    }
  }, [selectedCampaign, selectedProducts, contentType, queryClient]);

  const handleRegenerate = async (contentId: string) => {
    setRegeneratingId(contentId);
    try {
      await apiFetch(`/content/${contentId}/regenerate`, { method: "POST" });
      queryClient.invalidateQueries({ queryKey: ["content"] });
    } finally {
      setRegeneratingId(null);
    }
  };

  const channels = channelsData?.channels ?? [];
  const isGenerating = progress !== null;

  return (
    <div>
      {/* Preview modal */}
      {previewPiece && (
        <PreviewModal
          piece={previewPiece}
          channels={channels}
          onClose={() => setPreviewPiece(null)}
        />
      )}

      {/* Header */}
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Nội dung AI</h1>
        <button
          onClick={() => setShowForm((v) => !v)}
          className="bg-blue-600 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-blue-700 transition-colors"
        >
          {showForm ? "✕ Đóng" : "+ Tạo nội dung mới"}
        </button>
      </div>

      {/* Create Form */}
      {showForm && (
        <div className="bg-white rounded-xl shadow-sm border p-6 mb-6">
          <h2 className="text-lg font-semibold mb-4">Tạo nội dung bằng AI</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
            {/* Campaign selector */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Chiến dịch</label>
              <select
                value={selectedCampaign}
                onChange={(e) => {
                  setSelectedCampaign(e.target.value);
                  setSelectedProducts([]);
                }}
                className="w-full border rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500 focus:outline-none"
              >
                <option value="">-- Chọn chiến dịch --</option>
                {campaigns?.map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.name} ({c.platform})
                  </option>
                ))}
              </select>
            </div>

            {/* Content type */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Loại nội dung</label>
              <select
                value={contentType}
                onChange={(e) => setContentType(e.target.value)}
                className="w-full border rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500 focus:outline-none"
              >
                {TYPE_OPTIONS.map((t) => (
                  <option key={t.value} value={t.value}>{t.label}</option>
                ))}
              </select>
            </div>
          </div>

          {/* Product selector */}
          {selectedCampaign && (
            <div className="mb-4">
              <div className="flex items-center justify-between mb-2">
                <label className="block text-sm font-medium text-gray-700">
                  Sản phẩm{" "}
                  <span className="text-gray-400 font-normal">
                    ({selectedProducts.length}/{products?.length ?? 0} đã chọn)
                  </span>
                </label>
                {products && products.length > 0 && (
                  <div className="flex gap-2">
                    <button
                      onClick={selectAll}
                      className="text-xs text-blue-600 hover:text-blue-800 underline"
                    >
                      Chọn tất cả
                    </button>
                    {selectedProducts.length > 0 && (
                      <button
                        onClick={clearAll}
                        className="text-xs text-gray-500 hover:text-gray-700 underline"
                      >
                        Bỏ chọn
                      </button>
                    )}
                  </div>
                )}
              </div>
              {!products || products.length === 0 ? (
                <p className="text-sm text-gray-400 bg-gray-50 rounded-lg p-3">
                  Chiến dịch này chưa có sản phẩm. Thêm sản phẩm từ trang Chiến dịch.
                </p>
              ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-2 max-h-48 overflow-y-auto">
                  {products.map((p) => (
                    <label
                      key={p.id}
                      className={`flex items-center gap-3 p-3 rounded-lg border cursor-pointer transition-colors ${
                        selectedProducts.includes(p.id)
                          ? "border-blue-500 bg-blue-50"
                          : "border-gray-200 hover:border-gray-300"
                      }`}
                    >
                      <input
                        type="checkbox"
                        checked={selectedProducts.includes(p.id)}
                        onChange={() => toggleProduct(p.id)}
                        className="accent-blue-600"
                      />
                      <div className="min-w-0">
                        <p className="text-sm font-medium text-gray-800 truncate">{p.name}</p>
                        {p.price != null && (
                          <p className="text-xs text-gray-500">
                            {p.price.toLocaleString("vi-VN")} ₫
                          </p>
                        )}
                      </div>
                    </label>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* Progress bar */}
          {isGenerating && progress && (
            <div className="mb-4">
              <div className="flex justify-between text-xs text-gray-600 mb-1">
                <span>Đang tạo nội dung...</span>
                <span>{progress.current} / {progress.total}</span>
              </div>
              <div className="w-full bg-gray-200 rounded-full h-2">
                <div
                  className="bg-blue-600 h-2 rounded-full transition-all duration-300"
                  style={{ width: `${(progress.current / progress.total) * 100}%` }}
                />
              </div>
            </div>
          )}

          {/* Actions */}
          <div className="flex items-center gap-3">
            <button
              onClick={handleGenerate}
              disabled={!selectedCampaign || selectedProducts.length === 0 || isGenerating}
              className="bg-blue-600 text-white px-6 py-2 rounded-lg text-sm font-medium hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              {isGenerating
                ? `Đang tạo ${progress?.current}/${progress?.total}...`
                : `Tạo ${selectedProducts.length > 0 ? `${selectedProducts.length} ` : ""}nội dung`}
            </button>
            {genError && <p className="text-red-600 text-sm">Lỗi: {genError}</p>}
          </div>
        </div>
      )}

      {/* Content list */}
      {isLoading ? (
        <div className="space-y-4">
          {[1, 2, 3].map((i) => (
            <div key={i} className="h-32 bg-gray-200 rounded-xl animate-pulse" />
          ))}
        </div>
      ) : content && content.length > 0 ? (
        <div className="space-y-4">
          {content.map((piece) => (
            <div key={piece.id} className="bg-white rounded-xl shadow-sm border overflow-hidden">
              <div className="p-5">
                <div className="flex justify-between items-start">
                  <div className="flex-1 min-w-0 mr-4">
                    <h3 className="font-semibold text-gray-900 truncate">
                      {piece.title || "Chưa có tiêu đề"}
                    </h3>
                    <div className="flex flex-wrap gap-2 mt-1.5">
                      <span className="px-2 py-0.5 bg-blue-50 text-blue-700 rounded text-xs">
                        {TYPE_OPTIONS.find((t) => t.value === piece.content_type)?.label || piece.content_type}
                      </span>
                      {piece.claude_model && (
                        <span className="px-2 py-0.5 bg-purple-50 text-purple-700 rounded text-xs">
                          {piece.claude_model}
                        </span>
                      )}
                      {piece.estimated_cost_usd != null && (
                        <span className="px-2 py-0.5 bg-green-50 text-green-700 rounded text-xs">
                          ${Number(piece.estimated_cost_usd).toFixed(4)}
                        </span>
                      )}
                      {piece.token_cost_input != null && (
                        <span className="px-2 py-0.5 bg-gray-50 text-gray-500 rounded text-xs">
                          {piece.token_cost_input + (piece.token_cost_output ?? 0)} tokens
                        </span>
                      )}
                    </div>
                  </div>
                  <div className="flex items-center gap-1.5 shrink-0">
                    <span
                      className={`px-2.5 py-1 rounded-full text-xs font-medium ${
                        STATUS_COLORS[piece.status] ?? "bg-gray-100 text-gray-700"
                      }`}
                    >
                      {STATUS_LABELS[piece.status] ?? piece.status}
                    </span>
                    {/* Preview & publish */}
                    <button
                      onClick={() => setPreviewPiece(piece)}
                      title="Xem trước & Đăng bài"
                      className="px-2.5 py-1 text-xs text-blue-600 bg-blue-50 hover:bg-blue-100 rounded transition-colors font-medium"
                    >
                      Đăng
                    </button>
                    <button
                      onClick={() => handleRegenerate(piece.id)}
                      disabled={regeneratingId === piece.id}
                      title="Tạo lại"
                      className="p-1.5 text-gray-400 hover:text-blue-600 hover:bg-blue-50 rounded transition-colors disabled:opacity-40"
                    >
                      {regeneratingId === piece.id ? "..." : "↺"}
                    </button>
                    <button
                      onClick={() => setExpandedId(expandedId === piece.id ? null : piece.id)}
                      className="p-1.5 text-gray-400 hover:text-gray-600 hover:bg-gray-100 rounded transition-colors"
                      title={expandedId === piece.id ? "Thu gọn" : "Xem nội dung"}
                    >
                      {expandedId === piece.id ? "▲" : "▼"}
                    </button>
                  </div>
                </div>

                {/* Collapsed preview */}
                {expandedId !== piece.id && (
                  <p className="text-sm text-gray-600 mt-2 line-clamp-2 whitespace-pre-wrap">
                    {piece.body}
                  </p>
                )}
              </div>

              {/* Expanded full content */}
              {expandedId === piece.id && (
                <div className="border-t bg-gray-50 p-5">
                  <pre className="text-sm text-gray-700 whitespace-pre-wrap font-sans leading-relaxed">
                    {piece.body}
                  </pre>
                  {piece.seo_keywords && piece.seo_keywords.length > 0 && (
                    <div className="flex gap-2 mt-4 flex-wrap">
                      <span className="text-xs font-medium text-gray-500">Từ khóa SEO:</span>
                      {piece.seo_keywords.map((kw) => (
                        <span key={kw} className="px-2 py-0.5 bg-white border text-gray-600 rounded text-xs">
                          {kw}
                        </span>
                      ))}
                    </div>
                  )}
                </div>
              )}
            </div>
          ))}
        </div>
      ) : (
        <div className="bg-white rounded-xl shadow-sm border p-16 text-center">
          <p className="text-gray-400 mb-4">Chưa có nội dung nào.</p>
          <button
            onClick={() => setShowForm(true)}
            className="bg-blue-600 text-white px-5 py-2 rounded-lg text-sm font-medium hover:bg-blue-700"
          >
            + Tạo nội dung đầu tiên
          </button>
        </div>
      )}
    </div>
  );
}
