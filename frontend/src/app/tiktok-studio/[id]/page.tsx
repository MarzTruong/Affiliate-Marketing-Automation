"use client";

import { useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api-client";
import type { TikTokProject, TikTokStatus } from "@/lib/types";

// ── Constants ─────────────────────────────────────────────────────────────────

type DetailTab = "script" | "assets" | "checklist" | "timeline";

const ANGLE_LABELS: Record<string, string> = {
  pain_point: "😤 Vấn đề & Giải pháp",
  feature: "⭐ Tính năng nổi bật",
  social_proof: "👥 Bằng chứng xã hội",
};

const STATUS_LABELS: Record<TikTokStatus, string> = {
  script_pending: "Chờ kịch bản",
  script_ready: "Kịch bản sẵn sàng",
  audio_ready: "Audio sẵn sàng",
  clips_ready: "Clips sẵn sàng",
  b_roll_filmed: "B-roll đã quay",
  editing: "Đang dựng phim",
  uploaded: "Đã upload",
  live: "Đang chiếu",
};

const STATUS_COLOR: Record<TikTokStatus, string> = {
  script_pending: "bg-slate-100 text-slate-600",
  script_ready: "bg-blue-100 text-blue-700",
  audio_ready: "bg-purple-100 text-purple-700",
  clips_ready: "bg-pink-100 text-pink-700",
  b_roll_filmed: "bg-orange-100 text-orange-700",
  editing: "bg-yellow-100 text-yellow-700",
  uploaded: "bg-cyan-100 text-cyan-700",
  live: "bg-green-100 text-green-700",
};

// Timeline stages for display
const TIMELINE_STAGES: { key: keyof TikTokProject; label: string; icon: string }[] = [
  { key: "created_at", label: "Tạo dự án", icon: "🆕" },
  { key: "script_ready_at", label: "Kịch bản sẵn", icon: "📝" },
  { key: "audio_ready_at", label: "Audio sẵn", icon: "🎵" },
  { key: "clips_ready_at", label: "Clips sẵn", icon: "🎬" },
  { key: "b_roll_filmed_at", label: "B-roll quay xong", icon: "📷" },
  { key: "editing_done_at", label: "Dựng xong", icon: "✂️" },
  { key: "uploaded_at", label: "Đã upload", icon: "⬆️" },
];

// ── Main component ────────────────────────────────────────────────────────────

export default function TikTokProjectDetailPage() {
  const params = useParams();
  const router = useRouter();
  const qc = useQueryClient();
  const projectId = params.id as string;
  const [activeTab, setActiveTab] = useState<DetailTab>("script");
  const [perfForm, setPerfForm] = useState({
    views: "",
    likes: "",
    comments: "",
    shares: "",
    tiktok_video_url: "",
  });

  const { data: project, isLoading, isError } = useQuery<TikTokProject>({
    queryKey: ["tiktok-project", projectId],
    queryFn: () => apiFetch(`/tiktok-studio/${projectId}`),
  });

  const generateMutation = useMutation({
    mutationFn: () =>
      apiFetch(`/tiktok-studio/${projectId}/generate`, { method: "POST" }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["tiktok-project", projectId] });
    },
  });

  const statusMutation = useMutation({
    mutationFn: (status: string) =>
      apiFetch(`/tiktok-studio/${projectId}/status`, {
        method: "PATCH",
        body: JSON.stringify({ status }),
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["tiktok-project", projectId] });
      qc.invalidateQueries({ queryKey: ["tiktok-projects"] });
    },
  });

  const perfMutation = useMutation({
    mutationFn: (data: object) =>
      apiFetch(`/tiktok-studio/${projectId}/performance`, {
        method: "PATCH",
        body: JSON.stringify(data),
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["tiktok-project", projectId] });
    },
  });

  const handlePerfSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    perfMutation.mutate({
      views: perfForm.views ? Number(perfForm.views) : undefined,
      likes: perfForm.likes ? Number(perfForm.likes) : undefined,
      comments: perfForm.comments ? Number(perfForm.comments) : undefined,
      shares: perfForm.shares ? Number(perfForm.shares) : undefined,
      tiktok_video_url: perfForm.tiktok_video_url || undefined,
    });
  };

  if (isLoading) {
    return (
      <div className="max-w-3xl mx-auto space-y-4">
        <div className="h-8 bg-slate-200 rounded animate-pulse w-48" />
        <div className="h-32 bg-slate-100 rounded-xl animate-pulse" />
      </div>
    );
  }

  if (isError || !project) {
    return (
      <div className="max-w-3xl mx-auto text-center py-20">
        <p className="text-4xl mb-3">❌</p>
        <p className="text-slate-600 font-medium">Không tìm thấy dự án</p>
        <button
          onClick={() => router.push("/tiktok-studio")}
          className="mt-4 text-sm text-blue-600 hover:underline"
        >
          ← Quay lại TikTok Studio
        </button>
      </div>
    );
  }

  const statusLabel = STATUS_LABELS[project.status] ?? project.status;
  const statusColor = STATUS_COLOR[project.status] ?? "bg-slate-100 text-slate-600";
  const canGenerate = ["script_pending", "script_ready", "audio_ready"].includes(project.status);
  const channelLabel = project.channel_type === "kenh1_faceless" ? "🤖 Kênh 1 AI" : "🎥 Kênh 2 Thật";

  return (
    <div className="max-w-3xl mx-auto">
      {/* Back */}
      <button
        onClick={() => router.push("/tiktok-studio")}
        className="text-sm text-slate-400 hover:text-slate-600 mb-4 flex items-center gap-1"
      >
        ← Quay lại TikTok Studio
      </button>

      {/* Project header */}
      <div className="bg-white rounded-xl border p-5 mb-5">
        <div className="flex items-start justify-between gap-4">
          <div className="flex-1 min-w-0">
            <h1 className="text-xl font-bold text-slate-900 leading-snug">
              {project.product_name}
            </h1>
            {project.title && project.title !== project.product_name && (
              <p className="text-sm text-slate-500 mt-0.5">{project.title}</p>
            )}
            <div className="flex items-center gap-2 mt-2 flex-wrap">
              <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${statusColor}`}>
                {statusLabel}
              </span>
              <span className="text-xs px-2 py-0.5 bg-slate-100 text-slate-600 rounded-full">
                {ANGLE_LABELS[project.angle] ?? project.angle}
              </span>
              <span className="text-xs px-2 py-0.5 bg-violet-100 text-violet-700 rounded-full font-medium">
                {channelLabel}
              </span>
              {project.product_ref_url && (
                <a
                  href={project.product_ref_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-xs text-blue-600 hover:underline"
                >
                  🔗 Link SP
                </a>
              )}
            </div>
          </div>

          {canGenerate && (
            <button
              onClick={() => generateMutation.mutate()}
              disabled={generateMutation.isPending}
              className="px-4 py-2 bg-pink-600 text-white text-sm font-medium rounded-lg hover:bg-pink-700 disabled:opacity-50 transition-colors shrink-0"
            >
              {generateMutation.isPending ? "Đang tạo..." : "⚡ Tạo kịch bản"}
            </button>
          )}
        </div>

        {generateMutation.isPending && (
          <div className="mt-3 text-xs text-blue-600 bg-blue-50 border border-blue-200 rounded-lg px-3 py-2">
            🔄 Claude AI đang viết kịch bản → ElevenLabs audio → HeyGen clips... (2-5 phút)
          </div>
        )}
      </div>

      {/* Tabs */}
      <div className="flex gap-1 mb-5 bg-slate-100 p-1 rounded-xl w-fit">
        {([
          ["script", "📝 Kịch bản"],
          ["assets", "🎵 Assets"],
          ["checklist", "✅ Checklist"],
          ["timeline", "📊 Timeline"],
        ] as [DetailTab, string][]).map(([tab, label]) => (
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

      {/* Tab: Kịch bản */}
      {activeTab === "script" && (
        <div className="bg-white rounded-xl border p-5">
          <h2 className="text-base font-semibold text-slate-800 mb-4">Kịch bản video</h2>
          {!project.script_body ? (
            <div className="text-center py-12">
              <p className="text-4xl mb-3">📝</p>
              <p className="text-slate-600 font-medium mb-1">Chưa có kịch bản</p>
              <p className="text-sm text-slate-400 mb-5">
                Bấm <strong>Tạo kịch bản</strong> ở trên để Claude AI viết script faceless review 45-60 giây.
              </p>
              {canGenerate && (
                <button
                  onClick={() => generateMutation.mutate()}
                  disabled={generateMutation.isPending}
                  className="px-5 py-2 bg-pink-600 text-white text-sm font-medium rounded-lg hover:bg-pink-700 disabled:opacity-50 transition-colors"
                >
                  {generateMutation.isPending ? "Đang tạo..." : "⚡ Tạo kịch bản ngay"}
                </button>
              )}
            </div>
          ) : (
            <div className="space-y-4">
              <div className="bg-slate-50 rounded-xl p-4 border font-mono text-sm text-slate-700 whitespace-pre-wrap leading-relaxed">
                {project.script_body}
              </div>
              <div className="flex gap-3">
                <button
                  onClick={() => navigator.clipboard.writeText(project.script_body ?? "")}
                  className="px-4 py-2 text-sm border rounded-lg hover:bg-slate-50 text-slate-600 transition-colors"
                >
                  📋 Copy kịch bản
                </button>
                {canGenerate && (
                  <button
                    onClick={() => generateMutation.mutate()}
                    disabled={generateMutation.isPending}
                    className="px-4 py-2 text-sm bg-pink-600 text-white rounded-lg hover:bg-pink-700 disabled:opacity-50 transition-colors"
                  >
                    {generateMutation.isPending ? "Đang tạo..." : "🔄 Tạo lại"}
                  </button>
                )}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Tab: Assets */}
      {activeTab === "assets" && (
        <div className="bg-white rounded-xl border p-5 space-y-5">
          <h2 className="text-base font-semibold text-slate-800">Audio & Video Clips</h2>

          {/* Audio */}
          <AssetRow
            label="🎵 Audio (ElevenLabs)"
            available={!!project.audio_url}
            pendingMsg="Chưa có audio. Chạy pipeline để ElevenLabs TTS tự tạo."
          >
            {project.audio_url && (
              <div className="space-y-2">
                <audio controls src={`http://localhost:8000${project.audio_url}`} className="w-full h-10" />
                <div className="flex gap-2">
                  <a
                    href={`http://localhost:8000${project.audio_url}`}
                    download
                    className="px-3 py-1.5 text-xs bg-purple-50 text-purple-700 rounded-lg hover:bg-purple-100 border border-purple-200 transition-colors"
                  >
                    ⬇️ Tải MP3
                  </a>
                  {project.audio_duration_s && (
                    <span className="text-xs text-slate-400 self-center">
                      ⏱ {project.audio_duration_s.toFixed(1)}s
                    </span>
                  )}
                </div>
              </div>
            )}
          </AssetRow>

          {/* Hook clip */}
          <AssetRow
            label="🎬 Hook Clip (HeyGen)"
            available={!!project.heygen_hook_url}
            pendingMsg="Chưa có hook clip. HeyGen tạo tự động sau khi có audio."
          >
            {project.heygen_hook_url && (
              <a
                href={project.heygen_hook_url}
                download
                className="inline-block px-3 py-1.5 text-xs bg-pink-50 text-pink-700 rounded-lg hover:bg-pink-100 border border-pink-200 transition-colors"
              >
                ⬇️ Tải Hook MP4
              </a>
            )}
          </AssetRow>

          {/* CTA clip */}
          <AssetRow
            label="🎬 CTA Clip (HeyGen)"
            available={!!project.heygen_cta_url}
            pendingMsg="Chưa có CTA clip. HeyGen tạo tự động sau khi có audio."
          >
            {project.heygen_cta_url && (
              <a
                href={project.heygen_cta_url}
                download
                className="inline-block px-3 py-1.5 text-xs bg-pink-50 text-pink-700 rounded-lg hover:bg-pink-100 border border-pink-200 transition-colors"
              >
                ⬇️ Tải CTA MP4
              </a>
            )}
          </AssetRow>

          {/* TikTok video URL (if live) */}
          {project.tiktok_video_url && (
            <AssetRow label="📱 Video TikTok" available>
              <a
                href={project.tiktok_video_url}
                target="_blank"
                rel="noopener noreferrer"
                className="text-sm text-blue-600 hover:underline break-all"
              >
                {project.tiktok_video_url}
              </a>
            </AssetRow>
          )}
        </div>
      )}

      {/* Tab: Checklist */}
      {activeTab === "checklist" && (
        <div className="bg-white rounded-xl border p-5 space-y-5">
          <h2 className="text-base font-semibold text-slate-800">Checklist thủ công</h2>
          <p className="text-sm text-slate-500">
            Các bước cần thực hiện thủ công ngoài pipeline AI. Bấm xác nhận để cập nhật trạng thái.
          </p>

          <div className="space-y-3">
            <ChecklistItem
              done={!!project.b_roll_filmed_at}
              label="📷 Quay B-roll"
              desc="Quay video sản phẩm thực tế (unboxing, cận cảnh, demo sử dụng). Tối thiểu 10-15 clip ngắn 3-5 giây mỗi clip."
              action={
                !project.b_roll_filmed_at && (
                  <button
                    onClick={() => statusMutation.mutate("b_roll_filmed")}
                    disabled={statusMutation.isPending}
                    className="px-3 py-1.5 text-xs bg-orange-600 text-white rounded-lg hover:bg-orange-700 disabled:opacity-50 transition-colors"
                  >
                    {statusMutation.isPending ? "Đang lưu..." : "✓ Xác nhận đã quay xong"}
                  </button>
                )
              }
            />

            <ChecklistItem
              done={!!project.editing_done_at}
              label="✂️ Dựng phim (CapCut)"
              desc="Ghép: Hook clip → B-roll có voiceover → CTA clip. Thêm sub, hiệu ứng chữ, nhạc nền. Xuất 1080×1920 (9:16)."
              action={
                !project.editing_done_at && project.b_roll_filmed_at && (
                  <button
                    onClick={() => statusMutation.mutate("editing_done")}
                    disabled={statusMutation.isPending}
                    className="px-3 py-1.5 text-xs bg-yellow-600 text-white rounded-lg hover:bg-yellow-700 disabled:opacity-50 transition-colors"
                  >
                    {statusMutation.isPending ? "Đang lưu..." : "✓ Xác nhận dựng xong"}
                  </button>
                )
              }
            />

            <ChecklistItem
              done={!!project.uploaded_at}
              label="⬆️ Upload TikTok"
              desc='Upload video lên TikTok. Caption ngắn + hashtag. CTA "link in bio" → landing page affiliate.'
              action={
                !project.uploaded_at && project.editing_done_at && (
                  <button
                    onClick={() => statusMutation.mutate("uploaded")}
                    disabled={statusMutation.isPending}
                    className="px-3 py-1.5 text-xs bg-cyan-600 text-white rounded-lg hover:bg-cyan-700 disabled:opacity-50 transition-colors"
                  >
                    {statusMutation.isPending ? "Đang lưu..." : "✓ Xác nhận đã upload"}
                  </button>
                )
              }
            />
          </div>

          {/* Performance update form */}
          {project.uploaded_at && (
            <div className="border-t pt-5">
              <h3 className="text-sm font-semibold text-slate-700 mb-3">
                📊 Cập nhật hiệu suất video
              </h3>
              <form onSubmit={handlePerfSubmit} className="space-y-3">
                <div className="grid grid-cols-2 gap-3">
                  {[
                    ["views", "👁 Lượt xem"],
                    ["likes", "❤️ Like"],
                    ["comments", "💬 Bình luận"],
                    ["shares", "↗️ Share"],
                  ].map(([key, label]) => (
                    <div key={key}>
                      <label className="block text-xs text-slate-500 mb-1">{label}</label>
                      <input
                        type="number"
                        min="0"
                        value={perfForm[key as keyof typeof perfForm]}
                        onChange={(e) =>
                          setPerfForm((f) => ({ ...f, [key]: e.target.value }))
                        }
                        placeholder={String(
                          project[key as keyof TikTokProject] ?? 0
                        )}
                        className="w-full px-3 py-2 border rounded-lg text-sm focus:ring-2 focus:ring-pink-400 focus:outline-none"
                      />
                    </div>
                  ))}
                </div>
                <div>
                  <label className="block text-xs text-slate-500 mb-1">Link video TikTok</label>
                  <input
                    type="url"
                    value={perfForm.tiktok_video_url}
                    onChange={(e) =>
                      setPerfForm((f) => ({ ...f, tiktok_video_url: e.target.value }))
                    }
                    placeholder={project.tiktok_video_url ?? "https://tiktok.com/@..."}
                    className="w-full px-3 py-2 border rounded-lg text-sm focus:ring-2 focus:ring-pink-400 focus:outline-none"
                  />
                </div>
                <button
                  type="submit"
                  disabled={perfMutation.isPending}
                  className="px-4 py-2 bg-slate-800 text-white text-sm font-medium rounded-lg hover:bg-slate-700 disabled:opacity-50 transition-colors"
                >
                  {perfMutation.isPending ? "Đang lưu..." : "💾 Lưu hiệu suất"}
                </button>
                {perfMutation.isSuccess && (
                  <p className="text-xs text-green-600">✅ Đã cập nhật!</p>
                )}
              </form>
            </div>
          )}
        </div>
      )}

      {/* Tab: Timeline */}
      {activeTab === "timeline" && (
        <div className="bg-white rounded-xl border p-5 space-y-5">
          <h2 className="text-base font-semibold text-slate-800">Timeline dự án</h2>

          {/* Timeline */}
          <div className="relative pl-6">
            <div className="absolute left-2.5 top-0 bottom-0 w-px bg-slate-200" />
            {TIMELINE_STAGES.map((stage) => {
              const value = project[stage.key] as string | null;
              const done = !!value;
              return (
                <div key={stage.key} className="relative mb-5">
                  <div
                    className={`absolute -left-6 w-4 h-4 rounded-full border-2 flex items-center justify-center text-[10px] ${
                      done
                        ? "bg-green-500 border-green-500 text-white"
                        : "bg-white border-slate-300"
                    }`}
                  >
                    {done ? "✓" : ""}
                  </div>
                  <div className={done ? "opacity-100" : "opacity-40"}>
                    <p className="text-sm font-medium text-slate-800">
                      {stage.icon} {stage.label}
                    </p>
                    <p className="text-xs text-slate-400 mt-0.5">
                      {done
                        ? new Date(value!).toLocaleString("vi-VN")
                        : "Chưa hoàn thành"}
                    </p>
                  </div>
                </div>
              );
            })}
          </div>

          {/* Performance stats */}
          {(project.views > 0 || project.likes > 0) && (
            <div className="border-t pt-4">
              <h3 className="text-sm font-semibold text-slate-700 mb-3">📊 Hiệu suất video</h3>
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                {[
                  ["👁", "Lượt xem", project.views.toLocaleString("vi-VN")],
                  ["❤️", "Like", project.likes.toLocaleString("vi-VN")],
                  ["💬", "Bình luận", project.comments.toLocaleString("vi-VN")],
                  ["↗️", "Share", project.shares.toLocaleString("vi-VN")],
                ].map(([icon, label, value]) => (
                  <div key={label} className="bg-slate-50 rounded-xl p-3 border text-center">
                    <p className="text-lg">{icon}</p>
                    <p className="text-xs text-slate-500">{label}</p>
                    <p className="text-base font-bold text-slate-800 mt-0.5">{value}</p>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Notes */}
          {project.notes && (
            <div className="border-t pt-4">
              <h3 className="text-sm font-semibold text-slate-700 mb-2">📌 Ghi chú</h3>
              <p className="text-sm text-slate-600 bg-slate-50 rounded-lg p-3 border">
                {project.notes}
              </p>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

// ── Helper components ─────────────────────────────────────────────────────────

function AssetRow({
  label,
  available,
  pendingMsg,
  children,
}: {
  label: string;
  available: boolean;
  pendingMsg?: string;
  children?: React.ReactNode;
}) {
  return (
    <div className="border rounded-xl p-4">
      <div className="flex items-center gap-2 mb-2">
        <span className={`w-2 h-2 rounded-full ${available ? "bg-green-500" : "bg-slate-300"}`} />
        <span className="text-sm font-medium text-slate-700">{label}</span>
      </div>
      {available ? (
        children
      ) : (
        <p className="text-xs text-slate-400">{pendingMsg}</p>
      )}
    </div>
  );
}

function ChecklistItem({
  done,
  label,
  desc,
  action,
}: {
  done: boolean;
  label: string;
  desc: string;
  action?: React.ReactNode;
}) {
  return (
    <div
      className={`border rounded-xl p-4 transition-colors ${
        done ? "border-green-200 bg-green-50" : "border-slate-200"
      }`}
    >
      <div className="flex items-start gap-3">
        <span
          className={`mt-0.5 w-5 h-5 rounded-full border-2 flex items-center justify-center text-xs shrink-0 ${
            done ? "bg-green-500 border-green-500 text-white" : "border-slate-300"
          }`}
        >
          {done ? "✓" : ""}
        </span>
        <div className="flex-1">
          <p className={`text-sm font-medium ${done ? "text-green-700" : "text-slate-800"}`}>
            {label}
          </p>
          <p className="text-xs text-slate-500 mt-0.5">{desc}</p>
          {action && <div className="mt-2">{action}</div>}
        </div>
      </div>
    </div>
  );
}
