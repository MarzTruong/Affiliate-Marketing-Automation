"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api-client";
import type { AutomationRule, PipelineRun } from "@/lib/types";

interface ReviewItem {
  post_id: string;
  content_id: string;
  content_title: string | null;
  content_body_preview: string;
  content_type: string;
  channel: string;
  scheduled_at: string;
  visual_url: string | null;
  rule_name: string | null;
}

type Tab = "rules" | "review" | "insights";

const PLATFORM_LABELS: Record<string, string> = {
  shopee: "Shopee",
  tiktok_shop: "TikTok Shop",
  shopback: "ShopBack",
  accesstrade: "AccessTrade VN",
};

const CHANNEL_LABELS: Record<string, string> = {
  facebook: "📘 Facebook",
  wordpress: "🌐 WordPress",
  tiktok: "🎵 TikTok",
};

const STATUS_COLORS: Record<string, string> = {
  completed: "bg-green-100 text-green-700",
  running: "bg-blue-100 text-blue-700",
  failed: "bg-red-100 text-red-700",
  partial: "bg-yellow-100 text-yellow-700",
};

export default function AutomationPage() {
  const qc = useQueryClient();
  const [activeTab, setActiveTab] = useState<Tab>("rules");
  const [showForm, setShowForm] = useState(false);
  const [expandedRule, setExpandedRule] = useState<string | null>(null);
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());

  const { data: rules = [], isLoading } = useQuery<AutomationRule[]>({
    queryKey: ["automation-rules"],
    queryFn: () => apiFetch("/automation"),
  });

  const createMutation = useMutation({
    mutationFn: (data: object) =>
      apiFetch("/automation", { method: "POST", body: JSON.stringify(data) }),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["automation-rules"] }); setShowForm(false); },
  });

  const toggleMutation = useMutation({
    mutationFn: (id: string) => apiFetch(`/automation/${id}/toggle`, { method: "PATCH" }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["automation-rules"] }),
  });

  const triggerMutation = useMutation({
    mutationFn: (id: string) => apiFetch(`/automation/${id}/trigger`, { method: "POST" }),
    onSuccess: (_, id) => {
      qc.invalidateQueries({ queryKey: ["automation-rules"] });
      qc.invalidateQueries({ queryKey: ["pipeline-runs", id] });
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => apiFetch(`/automation/${id}`, { method: "DELETE" }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["automation-rules"] }),
  });

  const handleCreate = (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const fd = new FormData(e.currentTarget);
    const channels = (fd.getAll("channels") as string[]).reduce(
      (acc, ch) => ({ ...acc, [ch]: true }), {}
    );
    const content_types = (fd.getAll("content_types") as string[]).reduce(
      (acc, ct) => ({ ...acc, [ct]: true }), {}
    );
    createMutation.mutate({
      name: fd.get("name"),
      platform: fd.get("platform"),
      category: fd.get("category") || null,
      min_commission_pct: fd.get("min_commission") ? Number(fd.get("min_commission")) : null,
      min_price: fd.get("min_price") ? Number(fd.get("min_price")) : null,
      max_price: fd.get("max_price") ? Number(fd.get("max_price")) : null,
      min_rating: fd.get("min_rating") ? Number(fd.get("min_rating")) : null,
      max_products_per_run: Number(fd.get("max_products") || 5),
      publish_channels: Object.keys(channels).length > 0 ? channels : { facebook: true },
      content_types: Object.keys(content_types).length > 0 ? content_types : { social_post: true },
      generate_visual: fd.get("generate_visual") === "on",
    });
  };

  const { data: reviewItems = [] } = useQuery<ReviewItem[]>({
    queryKey: ["review-queue"],
    queryFn: () => apiFetch("/automation/review-queue"),
    refetchInterval: activeTab === "review" ? 30000 : false,
  });

  const approveMutation = useMutation({
    mutationFn: (postId: string) =>
      apiFetch(`/automation/review/${postId}/approve`, { method: "POST" }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["review-queue"] }),
  });

  const rejectMutation = useMutation({
    mutationFn: (postId: string) =>
      apiFetch(`/automation/review/${postId}/reject`, {
        method: "POST",
        body: JSON.stringify({ reason: "Từ chối bởi người dùng" }),
      }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["review-queue"] }),
  });

  const bulkApproveMutation = useMutation({
    mutationFn: (ids: string[]) =>
      apiFetch("/automation/review/bulk-approve", {
        method: "POST",
        body: JSON.stringify({ post_ids: ids }),
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["review-queue"] });
      setSelectedIds(new Set());
    },
  });

  const bulkRejectMutation = useMutation({
    mutationFn: (ids: string[]) =>
      apiFetch("/automation/review/bulk-reject", {
        method: "POST",
        body: JSON.stringify({ post_ids: ids, reason: "Từ chối hàng loạt" }),
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["review-queue"] });
      setSelectedIds(new Set());
    },
  });

  const toggleSelect = (id: string) =>
    setSelectedIds(prev => {
      const next = new Set(prev);
      next.has(id) ? next.delete(id) : next.add(id);
      return next;
    });

  const toggleSelectAll = () =>
    setSelectedIds(prev =>
      prev.size === reviewItems.length
        ? new Set()
        : new Set(reviewItems.map(i => i.post_id))
    );

  const pendingCount = reviewItems.length;

  return (
    <div>
      {/* Header */}
      <div className="flex justify-between items-center mb-5">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">🤖 Tự động hoá</h1>
          <p className="text-sm text-slate-500 mt-1">
            Tự quét SP → tạo content → chờ duyệt → lên lịch đăng. Lịch tự học theo hiệu suất.
          </p>
        </div>
        {activeTab === "rules" && (
          <button
            onClick={() => setShowForm(v => !v)}
            className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors text-sm font-medium"
          >
            {showForm ? "Hủy" : "+ Tạo rule mới"}
          </button>
        )}
      </div>

      {/* Tabs */}
      <div className="flex gap-1 mb-6 bg-slate-100 p-1 rounded-xl w-fit">
        {([
          ["rules", "⚙️ Rules"],
          ["review", `✅ Chờ Duyệt${pendingCount > 0 ? ` (${pendingCount})` : ""}`],
          ["insights", "📊 Thống kê lịch"],
        ] as [Tab, string][]).map(([tab, label]) => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
              activeTab === tab
                ? "bg-white shadow-sm text-slate-900"
                : "text-slate-500 hover:text-slate-700"
            }`}
          >
            {label}
          </button>
        ))}
      </div>

      {/* Create Form */}
      {showForm && (
        <div className="bg-white rounded-xl shadow-sm border p-6 mb-6">
          <h2 className="text-lg font-semibold mb-4">Tạo Automation Rule</h2>
          <form onSubmit={handleCreate} className="space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">Tên rule *</label>
                <input name="name" required className={INPUT_CLS} placeholder="VD: Shopee Điện tử 8%" />
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">Nền tảng *</label>
                <select name="platform" required className={INPUT_CLS}>
                  {Object.entries(PLATFORM_LABELS).map(([v, l]) => (
                    <option key={v} value={v}>{l}</option>
                  ))}
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">Danh mục</label>
                <input name="category" className={INPUT_CLS} placeholder="dien_tu, thoi_trang, gia_dung..." />
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">Hoa hồng tối thiểu (%)</label>
                <input name="min_commission" type="number" step="0.5" min="0" max="100" className={INPUT_CLS} placeholder="8" />
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">Giá tối thiểu (VNĐ)</label>
                <input name="min_price" type="number" className={INPUT_CLS} placeholder="100000" />
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">Giá tối đa (VNĐ)</label>
                <input name="max_price" type="number" className={INPUT_CLS} placeholder="5000000" />
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">Rating tối thiểu</label>
                <input name="min_rating" type="number" step="0.1" min="0" max="5" className={INPUT_CLS} placeholder="4.0" />
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">Số SP tối đa / lần chạy</label>
                <input name="max_products" type="number" min="1" max="20" className={INPUT_CLS} defaultValue="5" />
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              <div>
                <p className="text-sm font-medium text-slate-700 mb-2">Kênh đăng bài</p>
                {Object.entries(CHANNEL_LABELS).map(([v, l]) => (
                  <label key={v} className="flex items-center gap-2 mb-1.5 text-sm cursor-pointer">
                    <input type="checkbox" name="channels" value={v} defaultChecked={v === "facebook"} />
                    {l}
                  </label>
                ))}
              </div>
              <div>
                <p className="text-sm font-medium text-slate-700 mb-2">Loại content</p>
                {[
                  ["social_post", "📱 Bài MXH"],
                  ["product_description", "📦 Mô tả SP"],
                  ["seo_article", "📰 Bài SEO"],
                  ["video_script", "🎬 Kịch bản video"],
                ].map(([v, l]) => (
                  <label key={v} className="flex items-center gap-2 mb-1.5 text-sm cursor-pointer">
                    <input type="checkbox" name="content_types" value={v} defaultChecked={v === "social_post"} />
                    {l}
                  </label>
                ))}
              </div>
              <div>
                <p className="text-sm font-medium text-slate-700 mb-2">Tuỳ chọn</p>
                <label className="flex items-center gap-2 text-sm cursor-pointer">
                  <input type="checkbox" name="generate_visual" defaultChecked />
                  🖼️ Tạo visual tự động
                </label>
                <p className="text-xs text-slate-400 mt-2">
                  Lịch đăng được tự động học theo hiệu suất (12h, 20h, 22h mặc định).
                </p>
              </div>
            </div>

            <div className="flex gap-3">
              <button
                type="submit"
                disabled={createMutation.isPending}
                className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 text-sm font-medium"
              >
                {createMutation.isPending ? "Đang tạo..." : "Tạo rule"}
              </button>
              {createMutation.isError && (
                <p className="text-red-600 text-sm self-center">{String(createMutation.error)}</p>
              )}
            </div>
          </form>
        </div>
      )}

      {/* Tab: Rules */}
      {activeTab === "rules" && (
        <>
          {isLoading ? (
            <div className="space-y-3">
              {[1, 2].map(i => <div key={i} className="h-24 bg-slate-200 rounded-xl animate-pulse" />)}
            </div>
          ) : rules.length === 0 ? (
            <div className="bg-white rounded-xl shadow-sm border p-12 text-center">
              <p className="text-4xl mb-3">🤖</p>
              <p className="text-slate-600 font-medium mb-1">Chưa có rule nào</p>
              <p className="text-sm text-slate-400">Tạo rule đầu tiên để hệ thống tự động chạy!</p>
            </div>
          ) : (
            <div className="space-y-3">
              {rules.map(rule => (
                <RuleCard
                  key={rule.id}
                  rule={rule}
                  isExpanded={expandedRule === rule.id}
                  onToggleExpand={() => setExpandedRule(expandedRule === rule.id ? null : rule.id)}
                  onToggleActive={() => toggleMutation.mutate(rule.id)}
                  onTrigger={() => triggerMutation.mutate(rule.id)}
                  onDelete={() => deleteMutation.mutate(rule.id)}
                  isTriggering={triggerMutation.isPending && triggerMutation.variables === rule.id}
                />
              ))}
            </div>
          )}
        </>
      )}

      {/* Tab: Review Queue */}
      {activeTab === "review" && (
        <div>
          {reviewItems.length === 0 ? (
            <div className="bg-white rounded-xl shadow-sm border p-12 text-center">
              <p className="text-4xl mb-3">✅</p>
              <p className="text-slate-600 font-medium mb-1">Không có bài nào chờ duyệt</p>
              <p className="text-sm text-slate-400">
                Sau khi pipeline chạy, content sẽ xuất hiện ở đây để bạn xem trước và duyệt.
              </p>
            </div>
          ) : (
            <div className="space-y-4">
              {/* Toolbar */}
              <div className="flex items-center justify-between">
                <label className="flex items-center gap-2 text-sm text-slate-600 cursor-pointer select-none">
                  <input
                    type="checkbox"
                    checked={selectedIds.size === reviewItems.length && reviewItems.length > 0}
                    onChange={toggleSelectAll}
                    className="w-4 h-4 rounded accent-blue-600"
                  />
                  {selectedIds.size === 0
                    ? `${pendingCount} bài chờ duyệt`
                    : `Đã chọn ${selectedIds.size} / ${pendingCount} bài`}
                </label>

                {selectedIds.size > 0 && (
                  <div className="flex items-center gap-2">
                    <button
                      onClick={() => bulkApproveMutation.mutate([...selectedIds])}
                      disabled={bulkApproveMutation.isPending}
                      className="px-4 py-1.5 bg-green-600 text-white text-sm font-medium rounded-lg hover:bg-green-700 disabled:opacity-50 transition-colors"
                    >
                      {bulkApproveMutation.isPending ? "Đang duyệt..." : `✅ Duyệt tất cả (${selectedIds.size})`}
                    </button>
                    <button
                      onClick={() => bulkRejectMutation.mutate([...selectedIds])}
                      disabled={bulkRejectMutation.isPending}
                      className="px-4 py-1.5 bg-red-50 text-red-600 text-sm font-medium rounded-lg hover:bg-red-100 disabled:opacity-50 transition-colors border border-red-200"
                    >
                      {bulkRejectMutation.isPending ? "Đang từ chối..." : `✕ Từ chối tất cả (${selectedIds.size})`}
                    </button>
                  </div>
                )}
              </div>

              {/* Items */}
              {reviewItems.map(item => {
                const isSelected = selectedIds.has(item.post_id);
                return (
                  <div
                    key={item.post_id}
                    className={`bg-white rounded-xl shadow-sm border overflow-hidden transition-colors ${
                      isSelected ? "border-blue-400 ring-1 ring-blue-300" : ""
                    }`}
                  >
                    <div className="p-5">
                      <div className="flex items-start gap-3">
                        <input
                          type="checkbox"
                          checked={isSelected}
                          onChange={() => toggleSelect(item.post_id)}
                          className="w-4 h-4 mt-1 rounded accent-blue-600 shrink-0 cursor-pointer"
                        />
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-2 mb-2 flex-wrap">
                            {item.rule_name && (
                              <span className="text-xs px-2 py-0.5 bg-purple-50 text-purple-700 rounded-full">
                                🤖 {item.rule_name}
                              </span>
                            )}
                            <span className="text-xs px-2 py-0.5 bg-blue-50 text-blue-700 rounded-full">
                              {CHANNEL_LABELS[item.channel] ?? item.channel}
                            </span>
                            <span className="text-xs px-2 py-0.5 bg-slate-100 text-slate-600 rounded-full">
                              {item.content_type}
                            </span>
                            <span className="text-xs text-slate-400">
                              📅 {new Date(item.scheduled_at).toLocaleString("vi-VN")}
                            </span>
                          </div>
                          {item.content_title && (
                            <h3 className="font-semibold text-slate-900 mb-2">{item.content_title}</h3>
                          )}
                          <p className="text-sm text-slate-600 leading-relaxed bg-slate-50 rounded-lg p-3 border">
                            {item.content_body_preview}
                          </p>
                        </div>
                        {item.visual_url && (
                          <img
                            src={item.visual_url}
                            alt="visual"
                            className="w-24 h-24 rounded-lg object-cover shrink-0 border"
                          />
                        )}
                      </div>
                    </div>
                    <div className="border-t bg-slate-50 px-5 py-3 flex items-center gap-3">
                      <button
                        onClick={() => approveMutation.mutate(item.post_id)}
                        disabled={approveMutation.isPending}
                        className="px-4 py-1.5 bg-green-600 text-white text-sm font-medium rounded-lg hover:bg-green-700 disabled:opacity-50 transition-colors"
                      >
                        ✅ Duyệt
                      </button>
                      <button
                        onClick={() => rejectMutation.mutate(item.post_id)}
                        disabled={rejectMutation.isPending}
                        className="px-4 py-1.5 bg-red-50 text-red-600 text-sm font-medium rounded-lg hover:bg-red-100 disabled:opacity-50 transition-colors border border-red-200"
                      >
                        ✕ Từ chối
                      </button>
                      <a href="/content" className="px-4 py-1.5 text-slate-500 text-sm hover:text-slate-700 transition-colors">
                        Xem toàn bộ →
                      </a>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      )}

      {/* Tab: Insights */}
      {activeTab === "insights" && <ScheduleInsights />}
    </div>
  );
}

function RuleCard({
  rule, isExpanded, onToggleExpand, onToggleActive, onTrigger, onDelete, isTriggering,
}: {
  rule: AutomationRule;
  isExpanded: boolean;
  onToggleExpand: () => void;
  onToggleActive: () => void;
  onTrigger: () => void;
  onDelete: () => void;
  isTriggering: boolean;
}) {
  const { data: runs } = useQuery<PipelineRun[]>({
    queryKey: ["pipeline-runs", rule.id],
    queryFn: () => apiFetch(`/automation/${rule.id}/runs?limit=5`),
    enabled: isExpanded,
  });

  const channels = Object.keys(rule.publish_channels || {}).filter(k => rule.publish_channels?.[k]);
  const contentTypes = Object.keys(rule.content_types || {}).filter(k => rule.content_types?.[k]);

  return (
    <div className="bg-white rounded-xl shadow-sm border overflow-hidden">
      <div className="p-5 flex items-center gap-4">
        {/* Toggle switch */}
        <button
          onClick={onToggleActive}
          className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors shrink-0 ${
            rule.is_active ? "bg-blue-600" : "bg-slate-300"
          }`}
        >
          <span className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
            rule.is_active ? "translate-x-6" : "translate-x-1"
          }`} />
        </button>

        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <h3 className="font-semibold text-slate-900">{rule.name}</h3>
            <span className="text-xs px-2 py-0.5 bg-slate-100 text-slate-600 rounded-full">
              {PLATFORM_LABELS[rule.platform] ?? rule.platform}
            </span>
          </div>
          <div className="flex gap-3 mt-1 text-xs text-slate-500 flex-wrap">
            {rule.category && <span>📁 {rule.category}</span>}
            {rule.min_commission_pct && <span>💰 Hoa hồng ≥{rule.min_commission_pct}%</span>}
            {rule.min_price && <span>💵 Từ {Number(rule.min_price).toLocaleString("vi-VN")}₫</span>}
            {rule.max_price && <span>đến {Number(rule.max_price).toLocaleString("vi-VN")}₫</span>}
            <span>🕐 {rule.cron_expression}</span>
          </div>
          <div className="flex gap-2 mt-1.5 flex-wrap">
            {channels.map(ch => (
              <span key={ch} className="text-xs px-2 py-0.5 bg-blue-50 text-blue-700 rounded">{CHANNEL_LABELS[ch] ?? ch}</span>
            ))}
            {contentTypes.map(ct => (
              <span key={ct} className="text-xs px-2 py-0.5 bg-purple-50 text-purple-700 rounded">{ct}</span>
            ))}
            {rule.generate_visual && <span className="text-xs px-2 py-0.5 bg-green-50 text-green-700 rounded">🖼️ Visual</span>}
          </div>
        </div>

        <div className="flex items-center gap-2 shrink-0">
          <button
            onClick={onTrigger}
            disabled={isTriggering}
            className="px-3 py-1.5 text-xs font-medium bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:opacity-50 transition-colors"
          >
            {isTriggering ? "Đang chạy..." : "▶ Chạy ngay"}
          </button>
          <button onClick={onToggleExpand} className="p-1.5 text-slate-400 hover:text-slate-600 rounded">
            {isExpanded ? "▲" : "▼"}
          </button>
          <button onClick={onDelete} className="p-1.5 text-slate-300 hover:text-red-500 rounded">✕</button>
        </div>
      </div>

      {isExpanded && (
        <div className="border-t bg-slate-50 p-4">
          <h4 className="text-sm font-semibold text-slate-700 mb-3">Lịch sử chạy gần đây</h4>
          {!runs || runs.length === 0 ? (
            <p className="text-sm text-slate-400">Chưa có lần chạy nào.</p>
          ) : (
            <div className="space-y-2">
              {runs.map(run => (
                <div key={run.id} className="bg-white border rounded-lg px-4 py-3 flex items-center justify-between">
                  <div className="text-sm">
                    <span className={`px-2 py-0.5 rounded text-xs font-medium mr-2 ${STATUS_COLORS[run.status] ?? "bg-slate-100 text-slate-600"}`}>
                      {run.status}
                    </span>
                    <span className="text-slate-600">
                      {run.products_filtered} SP → {run.content_created} bài → {run.posts_scheduled} lịch
                    </span>
                  </div>
                  <span className="text-xs text-slate-400">
                    {new Date(run.started_at).toLocaleString("vi-VN")}
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function ScheduleInsights() {
  const { data } = useQuery({
    queryKey: ["schedule-insights"],
    queryFn: () => apiFetch("/automation/schedule-insights"),
  });

  if (!data || (data as { message?: string }).message) {
    return (
      <div className="mt-6 bg-white rounded-xl shadow-sm border p-6">
        <h2 className="text-lg font-semibold mb-2">📊 Adaptive Scheduler</h2>
        <p className="text-sm text-slate-400">
          {(data as { message?: string })?.message ?? "Chưa có dữ liệu. Cần ít nhất 7 ngày đăng bài để hệ thống học lịch tốt nhất."}
        </p>
      </div>
    );
  }

  const insights = data as {
    top_slots: Array<{ channel: string; hour: string; day: string; avg_clicks: number; score: number }>;
    total_data_points: number;
  };

  return (
    <div className="mt-6 bg-white rounded-xl shadow-sm border p-6">
      <div className="flex justify-between items-center mb-4">
        <h2 className="text-lg font-semibold">📊 Adaptive Scheduler — Giờ đăng hiệu quả nhất</h2>
        <span className="text-xs text-slate-400">{insights.total_data_points} data points</span>
      </div>
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-3">
        {insights.top_slots.slice(0, 5).map((slot, i) => (
          <div key={i} className="border rounded-lg p-3 text-center">
            <div className="text-lg font-bold text-blue-600">{slot.hour}</div>
            <div className="text-xs text-slate-500">{slot.day}</div>
            <div className="text-xs text-slate-400 mt-1">{slot.channel}</div>
            <div className="text-xs font-medium text-green-600 mt-1">
              ↑ {slot.avg_clicks.toFixed(1)} clicks
            </div>
          </div>
        ))}
      </div>
      <p className="text-xs text-slate-400 mt-3">
        Lịch đăng tự cập nhật hàng tuần dựa trên dữ liệu thực tế.
      </p>
    </div>
  );
}

const INPUT_CLS = "w-full px-3 py-2 border rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:outline-none";
