"use client";

import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from "recharts";
import type { DailyStats } from "@/lib/types";

export function PerformanceChart({ data }: { data: DailyStats[] }) {
  return (
    <ResponsiveContainer width="100%" height={300}>
      <LineChart data={data}>
        <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
        <XAxis
          dataKey="date"
          tick={{ fontSize: 12 }}
          tickFormatter={(v) => {
            const d = new Date(v);
            return `${d.getDate()}/${d.getMonth() + 1}`;
          }}
        />
        <YAxis tick={{ fontSize: 12 }} />
        <Tooltip />
        <Legend />
        <Line
          type="monotone"
          dataKey="clicks"
          stroke="#3b82f6"
          strokeWidth={2}
          dot={false}
          name="Lượt click"
        />
        <Line
          type="monotone"
          dataKey="conversions"
          stroke="#10b981"
          strokeWidth={2}
          dot={false}
          name="Chuyển đổi"
        />
        <Line
          type="monotone"
          dataKey="revenue"
          stroke="#f59e0b"
          strokeWidth={2}
          dot={false}
          name="Doanh thu"
        />
      </LineChart>
    </ResponsiveContainer>
  );
}
