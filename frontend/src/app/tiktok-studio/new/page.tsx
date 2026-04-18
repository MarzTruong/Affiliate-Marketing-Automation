"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useMutation } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api-client";
import type { TikTokAngle, TikTokProject } from "@/lib/types";

// ── Types ─────────────────────────────────────────────────────────────────────

type Step = 1 | 2 | 3;

interface FormData {
  product_name: string;
  product_ref_url: string;
  notes: string;
  angle: TikTokAngle | "";
}

// ── Angle options ─────────────────────────────────────────────────────────────

const ANGLE_OPTIONS: {
  value: TikTokAngle;
  label: string;
  icon: string;
  desc: string;
  example: string;
}[] = [
  {
    value: "pain_point",
    label: "Vấn đề & Giải pháp",
    icon: "😤",
    desc: "Chỉ ra vấn đề mà sản phẩm giải quyết. Mạnh nhất khi target audience đang gặp đúng vấn đề đó.",
    example: "\"Bạn có bao giờ bị...? Mình đã tìm ra cách giải quyết...\"",
  },
  {
    value: "feature",
    label: "Tính năng nổi bật",
    icon: "⭐",
    desc: "Showcase tính năng độc đáo của sản phẩm. Hiệu quả với sản phẩm có điểm khác biệt rõ ràng.",
    example: "\"Tính năng này của [SP] khiến mình không thể bỏ qua...\"",
  },
  {
    value: "social_proof",
    label: "Bằng chứng xã hội",
    icon: "👥",
    desc: "Dùng review, số liệu, so sánh để thuyết phục. Mạnh nhất với sản phẩm có nhiều đánh giá tốt.",
    example: "\"X người đã dùng và đây là kết quả...\"",
  },
];

// ── Main component ────────────────────────────────────────────────────────────

export default function NewTikTokProjectPage() {
  const router = useRouter();
  const [step, setStep] = useState<Step>(1);
  const [form, setForm] = useState<FormData>({
    product_name: "",
    product_ref_url: "",
    notes: "",
    angle: "",
  });

  const createMutation = useMutation({
    mutationFn: (data: {
      product_name: string;
      angle: TikTokAngle;
      product_ref_url?: string;
      notes?: string;
    }) => apiFetch<TikTokProject>("/tiktok-studio", { method: "POST", body: JSON.stringify(data) }),
    onSuccess: (project) => {
      router.push(`/tiktok-studio/${project.id}`);
    },
  });

  const handleSubmit = () => {
    if (!form.angle) return;
    createMutation.mutate({
      product_name: form.product_name,
      angle: form.angle,
      product_ref_url: form.product_ref_url || undefined,
      notes: form.notes || undefined,
    });
  };

  const canProceedStep1 = form.product_name.trim().length >= 3;
  const canProceedStep2 = form.angle !== "";

  return (
    <div className="max-w-2xl mx-auto">
      {/* Header */}
      <div className="mb-8">
        <button
          onClick={() => router.push("/tiktok-studio")}
          className="text-sm text-slate-400 hover:text-slate-600 mb-3 flex items-center gap-1"
        >
          ← Quay lại TikTok Studio
        </button>
        <h1 className="text-2xl font-bold text-slate-900">🎬 Tạo dự án mới</h1>
        <p className="text-sm text-slate-500 mt-1">
          Điền thông tin để AI tạo kịch bản faceless video affiliate.
        </p>
      </div>

      {/* Stepper */}
      <div className="flex items-center gap-2 mb-8">
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
            <span
              className={`text-sm font-medium ${
                step === s ? "text-slate-900" : "text-slate-400"
              }`}
            >
              {s === 1 ? "Thông tin SP" : s === 2 ? "Góc tiếp cận" : "Xác nhận"}
            </span>
            {s < 3 && <span className="text-slate-300 ml-1">→</span>}
          </div>
        ))}
      </div>

      {/* Step 1: Product info */}
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
              placeholder="https://shopee.vn/..."
              className="w-full px-3 py-2.5 border rounded-lg text-sm focus:ring-2 focus:ring-pink-400 focus:outline-none"
            />
            <p className="text-xs text-slate-400 mt-1">
              Link tham khảo để AI hiểu rõ hơn về sản phẩm.
            </p>
          </div>

          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1.5">
              Ghi chú cho AI (tuỳ chọn)
            </label>
            <textarea
              value={form.notes}
              onChange={(e) => setForm((f) => ({ ...f, notes: e.target.value }))}
              placeholder="VD: Target audience là nữ 20-30 tuổi, nhấn mạnh giá sale 50%..."
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

      {/* Step 2: Angle */}
      {step === 2 && (
        <div className="bg-white rounded-xl border p-6 space-y-4">
          <h2 className="text-lg font-semibold text-slate-800">Chọn góc tiếp cận</h2>
          <p className="text-sm text-slate-500">
            Góc tiếp cận quyết định hướng kịch bản AI sẽ tạo ra.
          </p>

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
                  <p className="text-xs text-slate-400 italic mt-1">{opt.example}</p>
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

      {/* Step 3: Confirm */}
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

          <div className="bg-blue-50 border border-blue-200 rounded-xl p-4 text-sm text-blue-700">
            <p className="font-semibold mb-1">⚡ Sau khi tạo:</p>
            <ul className="list-disc list-inside space-y-0.5 text-xs">
              <li>Dự án tạo với status <strong>script_pending</strong></li>
              <li>Bấm <strong>&quot;Tạo kịch bản&quot;</strong> để Claude AI viết script</li>
              <li>Sau đó chạy ElevenLabs (audio) + HeyGen (clips) tự động</li>
              <li>Nhận thông báo Telegram khi assets sẵn sàng</li>
            </ul>
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
              onClick={handleSubmit}
              disabled={createMutation.isPending}
              className="flex-1 py-2.5 bg-pink-600 text-white rounded-lg font-medium text-sm hover:bg-pink-700 disabled:opacity-50 transition-colors"
            >
              {createMutation.isPending ? "Đang tạo..." : "🎬 Tạo dự án"}
            </button>
          </div>
        </div>
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
