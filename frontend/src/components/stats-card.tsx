interface StatsCardProps {
  title: string;
  value: string | number;
  subtitle?: string;
  loading?: boolean;
}

export function StatsCard({ title, value, subtitle, loading }: StatsCardProps) {
  return (
    <div className="bg-white rounded-xl shadow-md border border-gray-200 p-6">
      <p className="text-sm font-semibold text-gray-600 mb-2">{title}</p>
      {loading ? (
        <div className="h-9 w-28 bg-gray-200 rounded animate-pulse" />
      ) : (
        <p className="text-3xl font-extrabold text-gray-900">{value}</p>
      )}
      {subtitle && (
        <p className="text-sm text-gray-500 mt-2">{subtitle}</p>
      )}
    </div>
  );
}
