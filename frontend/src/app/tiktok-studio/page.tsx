"use client";

import Link from "next/link";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api-client";
import type { TikTokProject, TikTokStatus } from "@/lib/types";

// ── Stage definitions ────────────────────────────────────────────────────────

type KanbanColumn = {
  label: string;
  icon: string;
  statuses: TikTokStatus[];
  color: string;
  bgColor: string;
};

const COLUMNS: KanbanColumn[] = [
  {
    label: "Kịch bản",
    icon: "📝",
    statuses: ["script_pending", "script_ready"],
    color: "text-blue-700",
    bgColor: "bg-blue-50 border-blue-200",
  },
  {
    label: "Audio",
    icon: "🎵",
    statuses: ["audio_ready"],
    color: "text-purple-700",
    bgColor: "bg-purple-50 border-purple-200",
  },
  {
    label: "Clips",
    icon: "🎬",
    statuses: ["clips_ready"],
    color: "text-pink-700",
    bgColor: "bg-pink-50 border-pink-200",
  },
  {
    label: "Dựng phim",
    icon: "✂️",
    statuses: ["b_roll_filmed", "editing"],
    color: "text-orange-700",
    bgColor: "bg-orange-50 border-orange-200",
  },
  {
    label: "Hoàn thành",
    icon: "✅",
    statuses: ["uploaded", "live"],
    color: "text-green-700",
    bgColor: "bg-green-50 border-green-200",
  },
];

const STATUS_LABELS: Record<TikTokStatus, string> = {
  script_pending: "Chờ kịch bản",
  script_ready: "Kịch bản sẵn",
  audio_ready: "Audio sẵn",
  clips_ready: "Clips sẵn",
  b_roll_filmed: "B-roll đã quay",
  editing: "Đang dựng",
  uploaded: "Đã upload",
  live: "Đang chiếu",
};

const ANGLE_LABELS: Record<string, string> = {
  pain_point: "😤 Vấn đề",
  feature: "⭐ Tính năng",
  social_proof: "👥 Bằng chứng XH",
};

// ── Component ────────────────────────────────────────────────────────────────

export default function TikTokStudioPage() {
  const qc = useQueryClient();

  const { data: projects = [], isLoading } = useQuery<TikTokProject[]>({
    queryKey: ["tiktok-projects"],
    queryFn: () => apiFetch("/tiktok-studio"),
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) =>
      apiFetch(`/tiktok-studio/${id}`, { method: "DELETE" }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["tiktok-projects"] }),
  });

  const totalProjects = projects.length;
  const liveCount = projects.filter((p) => p.status === "live").length;
  const pendingCount = projects.filter((p) =>
    ["script_pending", "script_ready"].includes(p.status)
  ).length;

  return (
    <div>
      {/* Header */}
      <div className="flex justify-between items-center mb-6">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">🎬 TikTok Studio</h1>
          <p className="text-sm text-slate-500 mt-1">
            Quản lý toàn bộ quy trình sản xuất video faceless affiliate — từ kịch bản đến live.
          </p>
        </div>
        <Link
          href="/tiktok-studio/new"
          className="px-4 py-2 bg-pink-600 text-white rounded-lg hover:bg-pink-700 transition-colors text-sm font-medium"
        >
          ➕ Dự án mới
        </Link>
      </div>

      {/* Stats row */}
      <div className="grid grid-cols-3 gap-4 mb-6">
        <div className="bg-white rounded-xl border p-4">
          <p className="text-sm text-slate-500">Tổng dự án</p>
          <p className="text-2xl font-bold text-slate-900 mt-1">{totalProjects}</p>
        </div>
        <div className="bg-white rounded-xl border p-4">
          <p className="text-sm text-slate-500">Đang chờ kịch bản</p>
          <p className="text-2xl font-bold text-blue-600 mt-1">{pendingCount}</p>
        </div>
        <div className="bg-white rounded-xl border p-4">
          <p className="text-sm text-slate-500">Đang live</p>
          <p className="text-2xl font-bold text-green-600 mt-1">{liveCount}</p>
        </div>
      </div>

      {/* Kanban */}
      {isLoading ? (
        <div className="grid grid-cols-5 gap-4">
          {COLUMNS.map((col) => (
            <div key={col.label} className="space-y-3">
              <div className="h-8 bg-slate-200 rounded animate-pulse" />
              <div className="h-24 bg-slate-100 rounded-xl animate-pulse" />
            </div>
          ))}
        </div>
      ) : totalProjects === 0 ? (
        <div className="bg-white rounded-xl border p-16 text-center">
          <p className="text-5xl mb-4">🎬</p>
          <p className="text-slate-700 font-semibold text-lg mb-1">Chưa có dự án nào</p>
          <p className="text-sm text-slate-400 mb-6">
            Tạo dự án đầu tiên để bắt đầu sản xuất video TikTok affiliate.
          </p>
          <Link
            href="/tiktok-studio/new"
            className="inline-block px-6 py-2.5 bg-pink-600 text-white rounded-lg hover:bg-pink-700 transition-colors text-sm font-medium"
          >
            ➕ Tạo dự án đầu tiên
          </Link>
        </div>
      ) : (
        <div className="grid grid-cols-5 gap-4 items-start">
          {COLUMNS.map((col) => {
            const cards = projects.filter((p) =>
              (col.statuses as string[]).includes(p.status)
            );
            return (
              <div key={col.label}>
                {/* Column header */}
                <div className={`flex items-center justify-between mb-3 px-2`}>
                  <span className={`text-sm font-semibold ${col.color}`}>
                    {col.icon} {col.label}
                  </span>
                  <span className="text-xs bg-slate-200 text-slate-600 px-2 py-0.5 rounded-full">
                    {cards.length}
                  </span>
                </div>

                {/* Cards */}
                <div className="space-y-3">
                  {cards.length === 0 ? (
                    <div className="border-2 border-dashed border-slate-200 rounded-xl p-4 text-center">
                      <p className="text-xs text-slate-400">Trống</p>
                    </div>
                  ) : (
                    cards.map((project) => (
                      <ProjectCard
                        key={project.id}
                        project={project}
                        colColor={col.bgColor}
                        onDelete={() => {
                          if (confirm(`Xoá dự án "${project.product_name}"?`)) {
                            deleteMutation.mutate(project.id);
                          }
                        }}
                      />
                    ))
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

// ── Project card ─────────────────────────────────────────────────────────────

function ProjectCard({
  project,
  colColor,
  onDelete,
}: {
  project: TikTokProject;
  colColor: string;
  onDelete: () => void;
}) {
  return (
    <div className="bg-white rounded-xl border shadow-sm overflow-hidden hover:shadow-md transition-shadow">
      {/* Color stripe */}
      <div className={`h-1 ${colColor.replace("border-", "bg-").split(" ")[0]}`} />

      <div className="p-3">
        <div className="flex items-start justify-between gap-1 mb-2">
          <h3 className="text-sm font-semibold text-slate-800 leading-snug line-clamp-2">
            {project.product_name}
          </h3>
          <button
            onClick={onDelete}
            className="text-slate-300 hover:text-red-400 transition-colors shrink-0 text-xs p-0.5"
          >
            ✕
          </button>
        </div>

        <div className="space-y-1.5 mb-3">
          <span className="inline-block text-xs px-1.5 py-0.5 bg-slate-100 text-slate-600 rounded">
            {ANGLE_LABELS[project.angle] ?? project.angle}
          </span>
          <p className="text-xs text-slate-400">
            {STATUS_LABELS[project.status]}
          </p>
        </div>

        {/* Performance (if live) */}
        {project.status === "live" && project.views > 0 && (
          <div className="flex gap-2 text-xs text-slate-500 mb-3">
            <span>👁 {project.views.toLocaleString("vi-VN")}</span>
            <span>❤️ {project.likes}</span>
          </div>
        )}

        <Link
          href={`/tiktok-studio/${project.id}`}
          className="block w-full text-center text-xs py-1.5 rounded-lg bg-slate-50 hover:bg-slate-100 text-slate-600 font-medium transition-colors border border-slate-200"
        >
          Xem chi tiết →
        </Link>
      </div>
    </div>
  );
}
