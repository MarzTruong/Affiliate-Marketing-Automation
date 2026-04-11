"use client";

import { useQuery } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api-client";
import type { AnalyticsOverview, DailyStats, PlatformBreakdown } from "@/lib/types";
import { StatsCard } from "@/components/stats-card";
import { PerformanceChart } from "@/components/performance-chart";

const fraudTypeLabels: Record<string, string> = {
  click_spam: "SPAM CLICK",
  timing_anomaly: "BẤT THƯỜNG THỜI GIAN",
  conversion_rate_spike: "ĐỘT BIẾN TỶ LỆ CHUYỂN ĐỔI",
  geo_mismatch: "SAI VÙNG ĐỊA LÝ",
};

export default function AnalyticsPage() {
  const { data: overview, isLoading } = useQuery<AnalyticsOverview>({
    queryKey: ["analytics-overview"],
    queryFn: () => apiFetch("/analytics/overview"),
  });

  const { data: dailyStats } = useQuery<DailyStats[]>({
    queryKey: ["analytics-daily"],
    queryFn: () => apiFetch("/analytics/daily"),
  });

  const { data: platformStats } = useQuery<PlatformBreakdown[]>({
    queryKey: ["analytics-platform"],
    queryFn: () => apiFetch("/analytics/by-platform"),
  });

  const { data: fraudAlerts } = useQuery<
    { id: string; fraud_type: string; confidence: number; details: Record<string, unknown> }[]
  >({
    queryKey: ["fraud-alerts"],
    queryFn: () => apiFetch("/analytics/fraud-alerts?resolved=false"),
  });

  return (
    <div>
      <h1 className="text-2xl font-bold text-gray-900 mb-6">Phân tích</h1>

      {/* Overview KPIs */}
      <div className="grid grid-cols-1 md:grid-cols-3 lg:grid-cols-6 gap-4 mb-8">
        <StatsCard
          title="Lượt hiển thị"
          value={overview?.total_impressions ?? 0}
          loading={isLoading}
        />
        <StatsCard
          title="Lượt click"
          value={overview?.total_clicks ?? 0}
          loading={isLoading}
        />
        <StatsCard
          title="CTR"
          value={`${overview?.ctr ?? 0}%`}
          loading={isLoading}
        />
        <StatsCard
          title="Chuyển đổi"
          value={overview?.total_conversions ?? 0}
          loading={isLoading}
        />
        <StatsCard
          title="Tỷ lệ CĐ"
          value={`${overview?.conversion_rate ?? 0}%`}
          loading={isLoading}
        />
        <StatsCard
          title="Doanh thu"
          value={`${(overview?.total_revenue ?? 0).toLocaleString("vi-VN")}`}
          loading={isLoading}
        />
      </div>

      {/* Chart */}
      <div className="bg-white rounded-xl shadow-sm border p-6 mb-8">
        <h2 className="text-lg font-semibold mb-4">Xu hướng theo ngày</h2>
        {dailyStats && dailyStats.length > 0 ? (
          <PerformanceChart data={dailyStats} />
        ) : (
          <div className="h-64 flex items-center justify-center text-gray-400">
            Chưa có dữ liệu phân tích.
          </div>
        )}
      </div>

      {/* Platform Breakdown */}
      <div className="bg-white rounded-xl shadow-sm border p-6 mb-8">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold">Hiệu suất theo nền tảng</h2>
          <a
            href={`${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1"}/analytics/export`}
            className="text-sm text-blue-600 hover:text-blue-800 underline"
          >
            Xuất CSV
          </a>
        </div>
        {platformStats && platformStats.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b text-left text-gray-500">
                  <th className="pb-3 pr-4">Nền tảng</th>
                  <th className="pb-3 pr-4 text-right">Hiển thị</th>
                  <th className="pb-3 pr-4 text-right">Click</th>
                  <th className="pb-3 pr-4 text-right">CTR</th>
                  <th className="pb-3 pr-4 text-right">Chuyển đổi</th>
                  <th className="pb-3 pr-4 text-right">Tỷ lệ CĐ</th>
                  <th className="pb-3 text-right">Doanh thu</th>
                </tr>
              </thead>
              <tbody>
                {platformStats.map((p) => (
                  <tr key={p.platform} className="border-b last:border-0">
                    <td className="py-3 pr-4 font-medium capitalize">{p.platform}</td>
                    <td className="py-3 pr-4 text-right">{p.impressions.toLocaleString("vi-VN")}</td>
                    <td className="py-3 pr-4 text-right">{p.clicks.toLocaleString("vi-VN")}</td>
                    <td className="py-3 pr-4 text-right">{p.ctr}%</td>
                    <td className="py-3 pr-4 text-right">{p.conversions.toLocaleString("vi-VN")}</td>
                    <td className="py-3 pr-4 text-right">{p.conversion_rate}%</td>
                    <td className="py-3 text-right">{p.revenue.toLocaleString("vi-VN")}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <p className="text-gray-400 text-center py-8">
            Chưa có dữ liệu theo nền tảng.
          </p>
        )}
      </div>

      {/* Fraud Alerts */}
      <div className="bg-white rounded-xl shadow-sm border p-6">
        <h2 className="text-lg font-semibold mb-4">
          Cảnh báo gian lận
          {fraudAlerts && fraudAlerts.length > 0 && (
            <span className="ml-2 px-2 py-0.5 bg-red-100 text-red-700 rounded-full text-xs">
              {fraudAlerts.length}
            </span>
          )}
        </h2>
        {fraudAlerts && fraudAlerts.length > 0 ? (
          <div className="space-y-3">
            {fraudAlerts.map((alert) => (
              <div
                key={alert.id}
                className="flex items-center justify-between p-4 bg-red-50 rounded-lg border border-red-100"
              >
                <div>
                  <p className="font-medium text-red-800">
                    {fraudTypeLabels[alert.fraud_type] || alert.fraud_type.replace(/_/g, " ").toUpperCase()}
                  </p>
                  <p className="text-sm text-red-600 mt-1">
                    Độ tin cậy: {(alert.confidence * 100).toFixed(0)}%
                  </p>
                </div>
                <button className="text-sm text-red-700 hover:text-red-900 underline">
                  Xem xét
                </button>
              </div>
            ))}
          </div>
        ) : (
          <p className="text-gray-400 text-center py-8">
            Không phát hiện gian lận.
          </p>
        )}
      </div>
    </div>
  );
}
