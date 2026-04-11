"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api-client";

interface NotificationItem {
  id: string;
  type: string;
  title: string;
  message: string;
  severity: string;
  is_read: boolean;
  created_at: string;
}

const severityColors: Record<string, string> = {
  info: "border-l-blue-500 bg-blue-50",
  warning: "border-l-yellow-500 bg-yellow-50",
  error: "border-l-red-500 bg-red-50",
  critical: "border-l-red-700 bg-red-100",
};

const typeLabels: Record<string, string> = {
  fraud: "Gian lận",
  ab_test: "A/B Test",
  error: "Lỗi",
  info: "Thông tin",
  evolution: "Tiến hóa",
  publish: "Đăng bài",
};

export default function NotificationsPage() {
  const queryClient = useQueryClient();

  const { data: notifications, isLoading } = useQuery<NotificationItem[]>({
    queryKey: ["notifications"],
    queryFn: () => apiFetch("/notifications"),
  });

  const markReadMutation = useMutation({
    mutationFn: (id: string) =>
      apiFetch(`/notifications/${id}/read`, { method: "PATCH" }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["notifications"] });
      queryClient.invalidateQueries({ queryKey: ["unread-notifications"] });
    },
  });

  const markAllReadMutation = useMutation({
    mutationFn: () => apiFetch("/notifications/read-all", { method: "POST" }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["notifications"] });
      queryClient.invalidateQueries({ queryKey: ["unread-notifications"] });
    },
  });

  const unreadCount = notifications?.filter((n) => !n.is_read).length ?? 0;

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-gray-900">
          Thông báo
          {unreadCount > 0 && (
            <span className="ml-2 px-2 py-0.5 bg-red-100 text-red-700 rounded-full text-sm">
              {unreadCount} mới
            </span>
          )}
        </h1>
        {unreadCount > 0 && (
          <button
            onClick={() => markAllReadMutation.mutate()}
            className="text-sm text-blue-600 hover:text-blue-800 underline"
          >
            Đánh dấu tất cả đã đọc
          </button>
        )}
      </div>

      {isLoading ? (
        <div className="text-center py-8 text-gray-400">Đang tải...</div>
      ) : notifications && notifications.length > 0 ? (
        <div className="space-y-3">
          {notifications.map((notif) => (
            <div
              key={notif.id}
              className={`border-l-4 rounded-r-lg p-4 ${
                severityColors[notif.severity] || "border-l-gray-300 bg-gray-50"
              } ${!notif.is_read ? "ring-1 ring-blue-200" : "opacity-75"}`}
            >
              <div className="flex items-start justify-between">
                <div>
                  <div className="flex items-center gap-2 mb-1">
                    <span className="text-xs px-1.5 py-0.5 bg-white rounded border text-gray-600">
                      {typeLabels[notif.type] || notif.type}
                    </span>
                    <span className="font-medium text-sm">{notif.title}</span>
                  </div>
                  <p className="text-sm text-gray-600">{notif.message}</p>
                  <p className="text-xs text-gray-400 mt-1">
                    {new Date(notif.created_at).toLocaleString("vi-VN")}
                  </p>
                </div>
                {!notif.is_read && (
                  <button
                    onClick={() => markReadMutation.mutate(notif.id)}
                    className="text-xs text-blue-600 hover:text-blue-800 whitespace-nowrap ml-4"
                  >
                    Đã đọc
                  </button>
                )}
              </div>
            </div>
          ))}
        </div>
      ) : (
        <div className="bg-white rounded-xl shadow-sm border p-8 text-center text-gray-400">
          Không có thông báo nào.
        </div>
      )}
    </div>
  );
}
