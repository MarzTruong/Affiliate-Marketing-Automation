"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useMutation } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api-client";
import type { TikTokAngle, TikTokProject } from "@/lib/types";

// ── Types ─────────────────────────────────────────────────────────────────────

type Step = 1 | 2 | 3;
type Mode = "manual" | "from-url";

interface FormData {
  product_name: string;
  product_ref_url: string;
  notes: string;
  angle: TikTokAngle | "";
}

interface QuickForm {
  url: string;
  angle: TikTokAngle | "";
  channel_type: "kenh1_faceless" | "kenh2_real_review";
  notes: string;
}

// ── Angle options ─────────────────────────────────────────────────────────────

const ANGLE_OPTIONS: {
  value: TikTokAngle;
  label: string;
  icon: string;
  desc: string;
}[] = [
  {
    value: "pain_point",
    label: "Vấn đề & Giải pháp",
    icon: "😤",
    desc: "Chỉ ra vấn đề mà sản phẩm giải quyết.",
  },
  {
    value: "feature",
    label: "Tính năng nổi bật",
    icon: "⭐",
    desc: "Showcase tính năng độc đáo của sản phẩm.",
  },
  {
    value: "social_proof",
    label: "Bằng chứng xã hội",
    icon: "👥",
    desc: "Dùng review, số liệu để thuyết phục.",
  },
];

// ── Main component ────────────────────────────────────────────────────────────

export default function NewTikTokProjectPage() {
  const router = useRouter();
  const [mode, setMode] = useState<Mode>("from-url");

  // Manual wizard state
  const [step, setStep] = useState<Step>(1);
  const [form, setForm] = useState<FormData>({
    product_name: "",
    product_ref_url: "",
    notes: "",
    angle: "",
  });

  // Quick from-url state
  const [quick, setQuick] = useState<QuickForm>({ url: "", angle: "", channel_type: "kenh1_faceless", notes: "" });
  const [urlPreview, setUrlPreview] = useState<{ product_name: string; price_text: string; success: boolean } | null>(null);
  const [isPreviewing, setIsPreviewing] = useState(false);

  // ── Mutations ──────────────────────────────────────────────────────────────

  const createMutation = useMutation({
    mutationFn: (data: {
      product_name: string;
      angle: TikTokAngle;
      product_ref_url?: string;
      notes?: string;
    }) => apiFetch<TikTokProject>("/tiktok-studio", { method: "POST", body: JSON.stringify(data) }),
    onSuccess: (project) => router.push(`/tiktok-studio/${project.id}`),
  });

  const fromUrlMutation = useMutation({
    mutationFn: (data: { url: string; angle: TikTokAngle; channel_type: string; notes?: string }) =>
      apiFetch<TikTokProject>("/tiktok-studio/from-url", { method: "POST", body: JSON.stringify(data) }),
    onSuccess: (project) => router.push(`/tiktok-studio/${project.id}`),
  });

  // ── Handlers ───────────────────────────────────────────────────────────────

  const handleManualSubmit = () => {
    if (!form.angle) return;
    createMutation.mutate({
      product_name: form.product_name,
      angle: form.angle,
      product_ref_url: form.product_ref_url || undefined,
      notes: form.notes || undefined,
    });
  };

  const handlePreviewUrl = async () => {
    if (!quick.url || !quick.angle) return;
    setIsPreviewing(true);
    try {
      const res = await apiFetch<{ product_name: string; price_text: string; success: boolean }>(
        "/tiktok-studio/preview-url",
        { method: "POST", body: JSON.stringify({ url: quick.url, angle: quick.angle }) }
      );
      setUrlPreview(res);
    } catch {
      setUrlPreview({ product_name: "", price_text: "", success: false });
    } finally {
      setIsPreviewing(false);
    }
  };

  const handleQuickSubmit = () => {
    if (!quick.url || !quick.angle) return;
    fromUrlMutation.mutate({
      url: quick.url,
      angle: quick.angle as TikTokAngle,
      channel_type: quick.channel_type,
      notes: quick.notes || undefined,
    });
  };

  const canProceedStep1 = form.product_name.trim().length >= 3;
  const canProceedStep2 = form.angle !== "";
  const canQuickSubmit = quick.url.trim().startsWith("http") && quick.angle !== "";

  return (
    <div className="max-w-2xl mx-auto">
      {/* Header */}
      <div className="mb-6">
        <button
          onClick={() => router.push("/tiktok-studio")}
          className="text-sm text-slate-400 hover:text-slate-600 mb-3 flex items-center gap-1"
        >
          ← Quay lại TikTok Studio
        </button>
        <h1 className="text-2xl font-bold text-slate-900">🎬 Tạo dự án mới</h1>
        <p className="text-sm text-slate-500 mt-1">
          Chọn sản phẩm muốn review để AI tạo kịch bản tự động.
        </p>
      </div>

      {/* Mode toggle */}
      <div className="flex gap-2 mb-6 bg-slate-100 p-1 rounded-xl">
        <button
          onClick={() => setMode("from-url")}
          className={`flex-1 py-2 rounded-lg text-sm font-medium transition-colors ${
            mode === "from-url"
              ? "bg-white text-slate-900 shadow-sm"
              : "text-slate-500 hover:text-slate-700"
          }`}
        >
          🔗 Nhập từ link TikTok Shop
        </button>
        <button
          onClick={() => setMode("manual")}
          className={`flex-1 py-2 rounded-lg text-sm font-medium transition-colors ${
            mode === "manual"
              ? "bg-white text-slate-900 shadow-sm"
              : "text-slate-500 hover:text-slate-700"
          }`}
        >
          ✏️ Nhập tay
        </button>
      </div>

      {/* ── FROM-URL MODE ── */}
      {mode === "from-url" && (
        <div className="space-y-4">
          <div className="bg-white rounded-xl border p-6 space-y-5">
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1.5">
                Link sản phẩm TikTok Shop <span className="text-red-500">*</span>
              </label>
              <input
                type="url"
                value={quick.url}
                onChange={(e) => {
                  setQuick((q) => ({ ...q, url: e.target.value }));
                  setUrlPreview(null);
                }}
                placeholder="https://vt.tiktok.com/... hoặc link sản phẩm TikTok Shop"
                className="w-full px-3 py-2.5 border rounded-lg text-sm focus:ring-2 focus:ring-pink-400 focus:outline-none"
                autoFocus
              />
              <p className="text-xs text-slate-400 mt-1">
                Mở TikTok Shop → chọn SP → Share → Copy link
              </p>
            </div>

            <div>
              <label className="block text-sm font-medium text-slate-700 mb-2">Kênh đăng</label>
              <div className="flex gap-2">
                {(["kenh1_faceless", "kenh2_real_review"] as const).map((ch) => (
                  <button
                    key={ch}
                    onClick={() => setQuick((q) => ({ ...q, channel_type: ch }))}
                    className={`flex-1 py-2 px-3 rounded-lg border-2 text-sm font-medium transition-all ${
                      quick.channel_type === ch
                        ? "border-pink-500 bg-pink-50 text-pink-700"
                        : "border-slate-200 text-slate-600 hover:border-slate-300"
                    }`}
                  >
                    {ch === "kenh1_faceless" ? "🤖 Kênh 1 — Faceless AI" : "🎥 Kênh 2 — Real Review"}
                  </button>
                ))}
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium text-slate-700 mb-2">
                Góc tiếp cận <span className="text-red-500">*</span>
              </label>
              <div className="grid grid-cols-3 gap-2">
                {ANGLE_OPTIONS.map((opt) => (
                  <button
                    key={opt.value}
                    onClick={() => {
                      setQuick((q) => ({ ...q, angle: opt.value }));
                      setUrlPreview(null);
                    }}
                    className={`p-3 rounded-xl border-2 text-left transition-all ${
                      quick.angle === opt.value
                        ? "border-pink-500 bg-pink-50"
                        : "border-slate-200 hover:border-slate-300"
                    }`}
                  >
                    <div className="text-xl mb-1">{opt.icon}</div>
                    <div className="text-xs font-semibold text-slate-700">{opt.label}</div>
                    <div className="text-xs text-slate-400 mt-0.5 hidden sm:block">{opt.desc}</div>
                  </button>
                ))}
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1.5">
                Ghi chú cho AI (tuỳ chọn)
              </label>
              <input
                type="text"
                value={quick.notes}
                onChange={(e) => setQuick((q) => ({ ...q, notes: e.target.value }))}
                placeholder="VD: Target mẹ bầu, nhấn mạnh an toàn cho bé..."
                className="w-full px-3 py-2.5 border rounded-lg text-sm focus:ring-2 focus:ring-pink-400 focus:outline-none"
              />
            </div>

            {/* Preview result */}
            {urlPreview && (
              <div
                className={`rounded-xl p-4 text-sm border ${
                  urlPreview.success
                    ? "bg-green-50 border-green-200 text-green-800"
                    : "bg-amber-50 border-amber-200 text-amber-800"
                }`}
              >
                {urlPreview.success ? (
                  <>
                    <p className="font-semibold mb-1">✅ Đã nhận diện sản phẩm:</p>
                    <p>
                      <strong>{urlPreview.product_name}</strong>
                      {urlPreview.price_text && (
                        <span className="ml-2 text-green-600">{urlPreview.price_text}</span>
                      )}
                    </p>
                  </>
                ) : (
                  <p>
                    ⚠️ Không tự lấy được tên SP từ link này — hệ thống sẽ dùng tên mặc định và AI
                    sẽ đọc URL để hiểu sản phẩm. Bạn có thể thêm ghi chú để AI hiểu rõ hơn.
                  </p>
                )}
              </div>
            )}

            {fromUrlMutation.isError && (
              <p className="text-sm text-red-600 bg-red-50 border border-red-200 rounded-lg px-4 py-2">
                {String(fromUrlMutation.error)}
              </p>
            )}

            <div className="flex gap-3">
              {!urlPreview && (
                <button
                  onClick={handlePreviewUrl}
                  disabled={!canQuickSubmit || isPreviewing}
                  className="flex-1 py-2.5 border border-slate-300 text-slate-700 rounded-lg font-medium text-sm hover:bg-slate-50 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
                >
                  {isPreviewing ? "Đang đọc link..." : "🔍 Xem trước thông tin"}
                </button>
              )}
              <button
                onClick={handleQuickSubmit}
                disabled={!canQuickSubmit || fromUrlMutation.isPending}
                className="flex-1 py-2.5 bg-pink-600 text-white rounded-lg font-medium text-sm hover:bg-pink-700 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
              >
                {fromUrlMutation.isPending ? "Đang tạo..." : "⚡ Tạo & chạy AI ngay"}
              </button>
            </div>
          </div>

          <div className="bg-blue-50 border border-blue-200 rounded-xl p-4 text-xs text-blue-700 space-y-1">
            <p className="font-semibold">⚡ Sau khi bấm "Tạo & chạy AI ngay":</p>
            <ul className="list-disc list-inside space-y-0.5">
              <li>AI tự động viết kịch bản faceless 45–60 giây</li>
              <li>ElevenLabs tạo audio giọng nói</li>
              <li>HeyGen tạo clips hook + CTA</li>
              <li>Nhận thông báo Telegram khi assets sẵn sàng</li>
            </ul>
          </div>
        </div>
      )}

      {/* ── MANUAL MODE ── */}
      {mode === "manual" && (
        <>
          {/* Stepper */}
          <div className="flex items-center gap-2 mb-6">
            {([1, 2, 3] as Step[]).map((s) => (
              <div key={s} className="flex items-center gap-2">
                <div
                  className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-bold transition-colors ${
                    step === s
                      ? "bg-pink-600 text-white"
                      : step > s
                      ? "bg-green-500 text-white"
                      : "bg-slate-200 text-slate-500"
                  }`}
                >
                  {step > s ? "✓" : s}
                </div>
                <span className={`text-sm font-medium ${step === s ? "text-slate-900" : "text-slate-400"}`}>
                  {s === 1 ? "Thông tin SP" : s === 2 ? "Góc tiếp cận" : "Xác nhận"}
                </span>
                {s < 3 && <span className="text-slate-300 ml-1">→</span>}
              </div>
            ))}
          </div>

          {/* Step 1 */}
          {step === 1 && (
            <div className="bg-white rounded-xl border p-6 space-y-5">
              <h2 className="text-lg font-semibold text-slate-800">Thông tin sản phẩm</h2>
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1.5">
                  Tên sản phẩm <span className="text-red-500">*</span>
                </label>
                <input
                  type="text"
                  value={form.product_name}
                  onChange={(e) => setForm((f) => ({ ...f, product_name: e.target.value }))}
                  placeholder="VD: Son dưỡng môi Laneige Lip Sleeping Mask"
                  className="w-full px-3 py-2.5 border rounded-lg text-sm focus:ring-2 focus:ring-pink-400 focus:outline-none"
                  autoFocus
                />
                <p className="text-xs text-slate-400 mt-1">Tối thiểu 3 ký tự.</p>
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1.5">
                  Link sản phẩm (tuỳ chọn)
                </label>
                <input
                  type="url"
                  value={form.product_ref_url}
                  onChange={(e) => setForm((f) => ({ ...f, product_ref_url: e.target.value }))}
                  placeholder="https://..."
                  className="w-full px-3 py-2.5 border rounded-lg text-sm focus:ring-2 focus:ring-pink-400 focus:outline-none"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1.5">
                  Ghi chú cho AI (tuỳ chọn)
                </label>
                <textarea
                  value={form.notes}
                  onChange={(e) => setForm((f) => ({ ...f, notes: e.target.value }))}
                  placeholder="VD: Target nữ 20-30 tuổi, nhấn mạnh giá sale 50%..."
                  rows={3}
                  className="w-full px-3 py-2.5 border rounded-lg text-sm focus:ring-2 focus:ring-pink-400 focus:outline-none resize-none"
                />
              </div>
              <button
                disabled={!canProceedStep1}
                onClick={() => setStep(2)}
                className="w-full py-2.5 bg-pink-600 text-white rounded-lg font-medium text-sm hover:bg-pink-700 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
              >
                Tiếp theo →
              </button>
            </div>
          )}

          {/* Step 2 */}
          {step === 2 && (
            <div className="bg-white rounded-xl border p-6 space-y-4">
              <h2 className="text-lg font-semibold text-slate-800">Chọn góc tiếp cận</h2>
              {ANGLE_OPTIONS.map((opt) => (
                <button
                  key={opt.value}
                  onClick={() => setForm((f) => ({ ...f, angle: opt.value }))}
                  className={`w-full text-left p-4 rounded-xl border-2 transition-all ${
                    form.angle === opt.value
                      ? "border-pink-500 bg-pink-50"
                      : "border-slate-200 hover:border-slate-300 hover:bg-slate-50"
                  }`}
                >
                  <div className="flex items-start gap-3">
                    <span className="text-2xl">{opt.icon}</span>
                    <div className="flex-1">
                      <p className="font-semibold text-slate-800 text-sm">{opt.label}</p>
                      <p className="text-xs text-slate-500 mt-0.5">{opt.desc}</p>
                    </div>
                    {form.angle === opt.value && (
                      <span className="text-pink-500 font-bold text-lg">✓</span>
                    )}
                  </div>
                </button>
              ))}
              <div className="flex gap-3 pt-2">
                <button
                  onClick={() => setStep(1)}
                  className="flex-1 py-2.5 border border-slate-300 text-slate-600 rounded-lg font-medium text-sm hover:bg-slate-50 transition-colors"
                >
                  ← Quay lại
                </button>
                <button
                  disabled={!canProceedStep2}
                  onClick={() => setStep(3)}
                  className="flex-1 py-2.5 bg-pink-600 text-white rounded-lg font-medium text-sm hover:bg-pink-700 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
                >
                  Tiếp theo →
                </button>
              </div>
            </div>
          )}

          {/* Step 3 */}
          {step === 3 && (
            <div className="bg-white rounded-xl border p-6 space-y-5">
              <h2 className="text-lg font-semibold text-slate-800">Xác nhận & Tạo dự án</h2>
              <div className="bg-slate-50 rounded-xl p-4 space-y-3 border">
                <Row label="Sản phẩm" value={form.product_name} />
                {form.product_ref_url && <Row label="Link SP" value={form.product_ref_url} link />}
                <Row
                  label="Góc tiếp cận"
                  value={
                    ANGLE_OPTIONS.find((o) => o.value === form.angle)?.icon +
                    " " +
                    ANGLE_OPTIONS.find((o) => o.value === form.angle)?.label
                  }
                />
                {form.notes && <Row label="Ghi chú" value={form.notes} />}
              </div>
              {createMutation.isError && (
                <p className="text-sm text-red-600 bg-red-50 border border-red-200 rounded-lg px-4 py-2">
                  {String(createMutation.error)}
                </p>
              )}
              <div className="flex gap-3">
                <button
                  onClick={() => setStep(2)}
                  className="flex-1 py-2.5 border border-slate-300 text-slate-600 rounded-lg font-medium text-sm hover:bg-slate-50 transition-colors"
                >
                  ← Quay lại
                </button>
                <button
                  onClick={handleManualSubmit}
                  disabled={createMutation.isPending}
                  className="flex-1 py-2.5 bg-pink-600 text-white rounded-lg font-medium text-sm hover:bg-pink-700 disabled:opacity-50 transition-colors"
                >
                  {createMutation.isPending ? "Đang tạo..." : "🎬 Tạo dự án"}
                </button>
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}

function Row({
  label,
  value,
  link = false,
}: {
  label: string;
  value: string | undefined;
  link?: boolean;
}) {
  if (!value) return null;
  return (
    <div className="flex items-start gap-3">
      <span className="text-xs text-slate-500 w-28 shrink-0 pt-0.5">{label}</span>
      {link ? (
        <a
          href={value}
          target="_blank"
          rel="noopener noreferrer"
          className="text-sm text-blue-600 hover:underline break-all"
        >
          {value}
        </a>
      ) : (
        <span className="text-sm text-slate-800 break-words">{value}</span>
      )}
    </div>
  );
}
