"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api-client";

interface Template {
  id: string;
  name: string;
  content_type: string | null;
  performance_score: number;
  usage_count: number;
  avg_ctr: number | null;
  avg_conversion_rate: number | null;
  is_active: boolean;
  created_at: string;
}

interface ABTestItem {
  id: string;
  campaign_id: string;
  template_a_id: string;
  template_b_id: string;
  status: string;
  sample_size_target: number;
  variant_a_conversions: number;
  variant_a_impressions: number;
  variant_b_conversions: number;
  variant_b_impressions: number;
  winner: string | null;
  statistical_significance: number | null;
  started_at: string;
  concluded_at: string | null;
}

const statusLabels: Record<string, string> = {
  running: "Đang chạy",
  concluded: "Kết thúc",
  inconclusive: "Chưa kết luận",
};

const statusColors: Record<string, string> = {
  running: "bg-blue-100 text-blue-700",
  concluded: "bg-green-100 text-green-700",
  inconclusive: "bg-yellow-100 text-yellow-700",
};

const contentTypeLabels: Record<string, string> = {
  product_description: "Mô tả sản phẩm",
  seo_article: "Bài SEO",
  social_post: "Bài mạng XH",
  video_script: "Kịch bản video",
};

export default function SOPPage() {
  const queryClient = useQueryClient();
  const [activeTab, setActiveTab] = useState<"templates" | "ab-tests">("templates");

  const { data: templates, isLoading: loadingTemplates } = useQuery<Template[]>({
    queryKey: ["sop-templates"],
    queryFn: () => apiFetch("/sop/templates?active_only=false"),
  });

  const { data: abTests, isLoading: loadingTests } = useQuery<ABTestItem[]>({
    queryKey: ["ab-tests"],
    queryFn: () => apiFetch("/sop/ab-tests"),
  });

  const scoreAllMutation = useMutation({
    mutationFn: () => apiFetch("/sop/score-all", { method: "POST" }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["sop-templates"] }),
  });

  const evolveMutation = useMutation({
    mutationFn: (templateId: string) =>
      apiFetch("/sop/evolve", {
        method: "POST",
        body: JSON.stringify({ template_id: templateId }),
      }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["sop-templates"] }),
  });

  const concludeMutation = useMutation({
    mutationFn: (testId: string) =>
      apiFetch(`/sop/ab-tests/${testId}/conclude`, { method: "POST" }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["ab-tests"] });
      queryClient.invalidateQueries({ queryKey: ["sop-templates"] });
    },
  });

  return (
    <div>
      <h1 className="text-2xl font-bold text-gray-900 mb-6">SOP & A/B Test</h1>

      {/* Tab Navigation */}
      <div className="flex gap-1 mb-6 bg-gray-100 rounded-lg p-1 w-fit">
        <button
          onClick={() => setActiveTab("templates")}
          className={`px-4 py-2 rounded-md text-sm font-medium transition-colors ${
            activeTab === "templates"
              ? "bg-white text-gray-900 shadow-sm"
              : "text-gray-500 hover:text-gray-700"
          }`}
        >
          Template
        </button>
        <button
          onClick={() => setActiveTab("ab-tests")}
          className={`px-4 py-2 rounded-md text-sm font-medium transition-colors ${
            activeTab === "ab-tests"
              ? "bg-white text-gray-900 shadow-sm"
              : "text-gray-500 hover:text-gray-700"
          }`}
        >
          A/B Test
        </button>
      </div>

      {/* Templates Tab */}
      {activeTab === "templates" && (
        <div className="bg-white rounded-xl shadow-sm border p-6">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-semibold">Template SOP</h2>
            <button
              onClick={() => scoreAllMutation.mutate()}
              disabled={scoreAllMutation.isPending}
              className="bg-purple-600 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-purple-700 disabled:opacity-50"
            >
              {scoreAllMutation.isPending ? "Đang chấm điểm..." : "Chấm điểm lại"}
            </button>
          </div>

          {loadingTemplates ? (
            <div className="text-center py-8 text-gray-400">Đang tải...</div>
          ) : templates && templates.length > 0 ? (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b text-left text-gray-500">
                    <th className="pb-3 pr-4">Tên</th>
                    <th className="pb-3 pr-4">Loại</th>
                    <th className="pb-3 pr-4 text-right">Điểm</th>
                    <th className="pb-3 pr-4 text-right">Sử dụng</th>
                    <th className="pb-3 pr-4 text-right">CTR</th>
                    <th className="pb-3 pr-4 text-right">Tỷ lệ CĐ</th>
                    <th className="pb-3 pr-4">Trạng thái</th>
                    <th className="pb-3">Hành động</th>
                  </tr>
                </thead>
                <tbody>
                  {templates.map((t) => (
                    <tr key={t.id} className="border-b last:border-0">
                      <td className="py-3 pr-4 font-medium">{t.name}</td>
                      <td className="py-3 pr-4 text-gray-500">
                        {contentTypeLabels[t.content_type || ""] || t.content_type}
                      </td>
                      <td className="py-3 pr-4 text-right">
                        <span
                          className={`px-2 py-0.5 rounded-full text-xs font-bold ${
                            t.performance_score >= 70
                              ? "bg-green-100 text-green-700"
                              : t.performance_score >= 40
                              ? "bg-yellow-100 text-yellow-700"
                              : "bg-gray-100 text-gray-600"
                          }`}
                        >
                          {t.performance_score.toFixed(1)}
                        </span>
                      </td>
                      <td className="py-3 pr-4 text-right text-gray-500">
                        {t.usage_count}
                      </td>
                      <td className="py-3 pr-4 text-right text-gray-500">
                        {t.avg_ctr != null ? `${(t.avg_ctr * 100).toFixed(1)}%` : "—"}
                      </td>
                      <td className="py-3 pr-4 text-right text-gray-500">
                        {t.avg_conversion_rate != null
                          ? `${(t.avg_conversion_rate * 100).toFixed(1)}%`
                          : "—"}
                      </td>
                      <td className="py-3 pr-4">
                        <span
                          className={`px-2 py-0.5 rounded-full text-xs ${
                            t.is_active
                              ? "bg-green-100 text-green-700"
                              : "bg-gray-100 text-gray-500"
                          }`}
                        >
                          {t.is_active ? "Hoạt động" : "Tắt"}
                        </span>
                      </td>
                      <td className="py-3">
                        <button
                          onClick={() => evolveMutation.mutate(t.id)}
                          disabled={evolveMutation.isPending}
                          className="text-sm text-blue-600 hover:text-blue-800 underline disabled:opacity-50"
                        >
                          Tiến hóa
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <p className="text-gray-400 text-center py-8">
              Chưa có template nào. Tạo template mới để bắt đầu.
            </p>
          )}
          {evolveMutation.isSuccess && (
            <p className="text-green-600 text-sm mt-3">
              Template mới đã được tạo thành công từ AI!
            </p>
          )}
          {evolveMutation.isError && (
            <p className="text-red-600 text-sm mt-3">
              Lỗi: {(evolveMutation.error as Error).message}
            </p>
          )}
        </div>
      )}

      {/* A/B Tests Tab */}
      {activeTab === "ab-tests" && (
        <div className="bg-white rounded-xl shadow-sm border p-6">
          <h2 className="text-lg font-semibold mb-4">A/B Test</h2>

          {loadingTests ? (
            <div className="text-center py-8 text-gray-400">Đang tải...</div>
          ) : abTests && abTests.length > 0 ? (
            <div className="space-y-4">
              {abTests.map((test) => {
                const rateA =
                  test.variant_a_impressions > 0
                    ? (test.variant_a_conversions / test.variant_a_impressions) * 100
                    : 0;
                const rateB =
                  test.variant_b_impressions > 0
                    ? (test.variant_b_conversions / test.variant_b_impressions) * 100
                    : 0;
                const total = test.variant_a_impressions + test.variant_b_impressions;
                const progress = Math.min((total / test.sample_size_target) * 100, 100);

                return (
                  <div key={test.id} className="border rounded-lg p-4">
                    <div className="flex items-center justify-between mb-3">
                      <div className="flex items-center gap-3">
                        <span
                          className={`px-2 py-0.5 rounded-full text-xs font-medium ${
                            statusColors[test.status] || "bg-gray-100 text-gray-700"
                          }`}
                        >
                          {statusLabels[test.status] || test.status}
                        </span>
                        {test.winner && (
                          <span className="text-sm font-bold text-green-700">
                            Thắng: Variant {test.winner}
                          </span>
                        )}
                        {test.statistical_significance != null && (
                          <span className="text-xs text-gray-500">
                            Sig: {(test.statistical_significance * 100).toFixed(1)}%
                          </span>
                        )}
                      </div>
                      {test.status === "running" && (
                        <button
                          onClick={() => concludeMutation.mutate(test.id)}
                          disabled={concludeMutation.isPending}
                          className="text-sm text-orange-600 hover:text-orange-800 underline disabled:opacity-50"
                        >
                          Kết thúc sớm
                        </button>
                      )}
                    </div>

                    {/* Progress bar */}
                    <div className="mb-3">
                      <div className="flex justify-between text-xs text-gray-500 mb-1">
                        <span>Tiến độ</span>
                        <span>
                          {total} / {test.sample_size_target} mẫu
                        </span>
                      </div>
                      <div className="w-full bg-gray-200 rounded-full h-2">
                        <div
                          className="bg-blue-600 h-2 rounded-full transition-all"
                          style={{ width: `${progress}%` }}
                        />
                      </div>
                    </div>

                    {/* Variant comparison */}
                    <div className="grid grid-cols-2 gap-4">
                      <div
                        className={`p-3 rounded-lg border ${
                          test.winner === "A"
                            ? "border-green-300 bg-green-50"
                            : "border-gray-200"
                        }`}
                      >
                        <p className="text-sm font-medium mb-1">Variant A</p>
                        <p className="text-xs text-gray-500">
                          {test.variant_a_impressions} hiển thị · {test.variant_a_conversions}{" "}
                          chuyển đổi
                        </p>
                        <p className="text-lg font-bold mt-1">{rateA.toFixed(1)}%</p>
                      </div>
                      <div
                        className={`p-3 rounded-lg border ${
                          test.winner === "B"
                            ? "border-green-300 bg-green-50"
                            : "border-gray-200"
                        }`}
                      >
                        <p className="text-sm font-medium mb-1">Variant B</p>
                        <p className="text-xs text-gray-500">
                          {test.variant_b_impressions} hiển thị · {test.variant_b_conversions}{" "}
                          chuyển đổi
                        </p>
                        <p className="text-lg font-bold mt-1">{rateB.toFixed(1)}%</p>
                      </div>
                    </div>

                    <p className="text-xs text-gray-400 mt-2">
                      Bắt đầu: {new Date(test.started_at).toLocaleString("vi-VN")}
                      {test.concluded_at &&
                        ` · Kết thúc: ${new Date(test.concluded_at).toLocaleString("vi-VN")}`}
                    </p>
                  </div>
                );
              })}
            </div>
          ) : (
            <p className="text-gray-400 text-center py-8">
              Chưa có A/B test nào. Tạo test mới từ API hoặc hệ thống tự động.
            </p>
          )}
        </div>
      )}
    </div>
  );
}
