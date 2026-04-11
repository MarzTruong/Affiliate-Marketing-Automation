"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api-client";
import type { AnalyticsOverview, DailyStats, CostSummary, SystemStats, SystemHealth } from "@/lib/types";
import { StatsCard } from "@/components/stats-card";
import { PerformanceChart } from "@/components/performance-chart";

const DATE_PRESETS = [
  { label: "7 ngày", days: 7 },
  { label: "30 ngày", days: 30 },
  { label: "90 ngày", days: 90 },
];

function getDateRange(days: number) {
  const end = new Date();
  const start = new Date();
  start.setDate(end.getDate() - days);
  return {
    start_date: start.toISOString().slice(0, 10),
    end_date: end.toISOString().slice(0, 10),
  };
}

export default function DashboardPage() {
  const [days, setDays] = useState(30);
  const { start_date, end_date } = getDateRange(days);
  const dateParams = `?start_date=${start_date}&end_date=${end_date}`;

  const { data: overview, isLoading: loadingOverview } = useQuery<AnalyticsOverview>({
    queryKey: ["analytics-overview", days],
    queryFn: () => apiFetch(`/analytics/overview${dateParams}`),
  });

  const { data: dailyStats } = useQuery<DailyStats[]>({
    queryKey: ["analytics-daily", days],
    queryFn: () => apiFetch(`/analytics/daily${dateParams}`),
  });

  const { data: costs } = useQuery<CostSummary[]>({
    queryKey: ["analytics-costs", days],
    queryFn: () => apiFetch(`/analytics/costs${dateParams}`),
  });

  const { data: sysStats } = useQuery<SystemStats>({
    queryKey: ["system-stats"],
    queryFn: () => apiFetch("/system/stats"),
  });

  const { data: sysHealth } = useQuery<SystemHealth>({
    queryKey: ["system-health"],
    queryFn: () => apiFetch("/system/health"),
  });

  const totalCost = costs?.reduce((sum, c) => sum + c.total_cost_usd, 0) ?? 0;

  return (
    <div>
      {/* Header with date range */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 mb-8">
        <h1 className="text-3xl font-extrabold text-slate-900">Tổng quan</h1>
        <div className="flex gap-1 bg-gray-100 rounded-lg p-1">
          {DATE_PRESETS.map((p) => (
            <button
              key={p.days}
              onClick={() => setDays(p.days)}
              className={`px-4 py-1.5 rounded-md text-sm font-medium transition-colors ${
                days === p.days
                  ? "bg-white text-gray-900 shadow-sm"
                  : "text-gray-500 hover:text-gray-700"
              }`}
            >
              {p.label}
            </button>
          ))}
        </div>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
        <StatsCard
          title="Tổng lượt click"
          value={overview?.total_clicks ?? 0}
          loading={loadingOverview}
        />
        <StatsCard
          title="Chuyển đổi"
          value={overview?.total_conversions ?? 0}
          subtitle={`Tỷ lệ: ${overview?.conversion_rate ?? 0}%`}
          loading={loadingOverview}
        />
        <StatsCard
          title="Doanh thu"
          value={`${(overview?.total_revenue ?? 0).toLocaleString("vi-VN")} VND`}
          loading={loadingOverview}
        />
        <StatsCard
          title="Chi phí AI"
          value={`$${totalCost.toFixed(4)}`}
          subtitle={
            overview?.total_revenue
              ? `ROAS: ${((overview.total_revenue / (totalCost * 25000 || 1)) * 100).toFixed(0)}%`
              : undefined
          }
          loading={loadingOverview}
        />
      </div>

      {/* CTR & Impression KPIs */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-8">
        <StatsCard
          title="Lượt hiển thị"
          value={(overview?.total_impressions ?? 0).toLocaleString("vi-VN")}
          loading={loadingOverview}
        />
        <StatsCard
          title="CTR"
          value={`${overview?.ctr ?? 0}%`}
          loading={loadingOverview}
        />
        <StatsCard
          title="Tỷ lệ chuyển đổi"
          value={`${overview?.conversion_rate ?? 0}%`}
          loading={loadingOverview}
        />
      </div>

      {/* Performance Chart */}
      <div className="bg-white rounded-xl shadow-md border border-gray-200 p-6 mb-8">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-bold text-slate-800">Biểu đồ hiệu suất</h2>
          <span className="text-xs text-gray-400">
            {start_date} → {end_date}
          </span>
        </div>
        {dailyStats && dailyStats.length > 0 ? (
          <PerformanceChart data={dailyStats} />
        ) : (
          <div className="h-64 flex items-center justify-center text-gray-400">
            Chưa có dữ liệu. Tạo chiến dịch để bắt đầu.
          </div>
        )}
      </div>

      {/* System Status */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-8">
        {/* System Health */}
        <div className="bg-white rounded-xl shadow-md border border-gray-200 p-6">
          <h2 className="text-lg font-bold text-slate-800 mb-4">Trạng thái hệ thống</h2>
          {sysHealth ? (
            <div className="space-y-3">
              <div className="flex items-center gap-2 mb-3">
                <span
                  className={`w-3 h-3 rounded-full ${
                    sysHealth.status === "healthy" ? "bg-green-500" : "bg-yellow-500"
                  }`}
                />
                <span className="font-medium">
                  {sysHealth.status === "healthy" ? "Hoạt động tốt" : "Có vấn đề"}
                </span>
              </div>
              {Object.entries(sysHealth.checks).map(([name, check]) => (
                <div key={name} className="flex items-center justify-between text-sm">
                  <span className="text-slate-700 font-medium capitalize">{name}</span>
                  <span
                    className={`px-2 py-0.5 rounded-full text-xs ${
                      check.status === "ok" || check.status === "configured"
                        ? "bg-green-100 text-green-700"
                        : "bg-red-100 text-red-700"
                    }`}
                  >
                    {check.status === "ok" || check.status === "configured" ? "OK" : check.status}
                  </span>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-gray-400 text-sm">Đang kiểm tra...</p>
          )}
        </div>

        {/* Quick Stats */}
        <div className="bg-white rounded-xl shadow-md border border-gray-200 p-6">
          <h2 className="text-lg font-bold text-slate-800 mb-4">Tổng quan hệ thống</h2>
          {sysStats ? (
            <div className="grid grid-cols-2 gap-3 text-sm">
              <div className="p-3 bg-blue-50 rounded-lg">
                <p className="text-slate-600 font-medium">Chiến dịch</p>
                <p className="text-xl font-extrabold text-slate-900">
                  {sysStats.campaigns.active}/{sysStats.campaigns.total}
                </p>
              </div>
              <div className="p-3 bg-green-50 rounded-lg">
                <p className="text-slate-600 font-medium">Nội dung đã đăng</p>
                <p className="text-xl font-extrabold text-slate-900">
                  {sysStats.content.published}/{sysStats.content.total}
                </p>
              </div>
              <div className="p-3 bg-purple-50 rounded-lg">
                <p className="text-slate-600 font-medium">Template SOP</p>
                <p className="text-xl font-extrabold text-slate-900">
                  {sysStats.templates.active}/{sysStats.templates.total}
                </p>
              </div>
              <div className="p-3 bg-orange-50 rounded-lg">
                <p className="text-slate-600 font-medium">A/B Test đang chạy</p>
                <p className="text-xl font-extrabold text-slate-900">{sysStats.ab_tests_running}</p>
              </div>
              {sysStats.fraud_unresolved > 0 && (
                <div className="p-3 bg-red-50 rounded-lg col-span-2">
                  <p className="text-red-600 font-medium">
                    {sysStats.fraud_unresolved} cảnh báo gian lận chưa xử lý
                  </p>
                </div>
              )}
            </div>
          ) : (
            <p className="text-gray-400 text-sm">Đang tải...</p>
          )}
        </div>
      </div>

      {/* Cost Breakdown */}
      {costs && costs.length > 0 && (
        <div className="bg-white rounded-xl shadow-md border border-gray-200 p-6">
          <h2 className="text-lg font-bold text-slate-800 mb-4">
            Chi phí AI (Claude API) — {days} ngày gần nhất
          </h2>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b text-left text-gray-500">
                  <th className="pb-3">Loại nội dung</th>
                  <th className="pb-3 text-right">Số lượng</th>
                  <th className="pb-3 text-right">Token vào</th>
                  <th className="pb-3 text-right">Token ra</th>
                  <th className="pb-3 text-right">Chi phí (USD)</th>
                </tr>
              </thead>
              <tbody>
                {costs.map((c) => (
                  <tr key={c.content_type} className="border-b last:border-0">
                    <td className="py-3 font-medium">{c.content_type}</td>
                    <td className="py-3 text-right">{c.count}</td>
                    <td className="py-3 text-right">{c.total_input_tokens.toLocaleString()}</td>
                    <td className="py-3 text-right">{c.total_output_tokens.toLocaleString()}</td>
                    <td className="py-3 text-right font-mono">${c.total_cost_usd.toFixed(4)}</td>
                  </tr>
                ))}
                <tr className="bg-gray-50">
                  <td className="py-2 px-1 font-bold text-sm" colSpan={4}>Tổng</td>
                  <td className="py-2 text-right font-bold font-mono">${totalCost.toFixed(4)}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
