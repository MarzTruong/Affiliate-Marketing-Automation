"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api-client";

type NavItem = { href: string; label: string; icon: string };
type NavSection = { title: string; items: NavItem[] };

const navSections: NavSection[] = [
  {
    title: "",
    items: [
      { href: "/", label: "Tổng quan", icon: "📊" },
    ],
  },
  {
    title: "TỰ ĐỘNG HÓA",
    items: [
      { href: "/automation", label: "Tự động hoá", icon: "🤖" },
      { href: "/calendar", label: "Lịch đăng bài", icon: "📅" },
      { href: "/chat", label: "AI Chat", icon: "💬" },
    ],
  },
  {
    title: "THỦ CÔNG",
    items: [
      { href: "/campaigns", label: "Chiến dịch", icon: "🎯" },
      { href: "/content", label: "Nội dung", icon: "📝" },
    ],
  },
  {
    title: "HỆ THỐNG",
    items: [
      { href: "/sop", label: "SOP & A/B Test", icon: "🧪" },
      { href: "/analytics", label: "Phân tích", icon: "📈" },
      { href: "/settings", label: "Cài đặt", icon: "⚙️" },
    ],
  },
];

export function Sidebar() {
  const pathname = usePathname();
  const { data: unreadData } = useQuery<{ unread: number }>({
    queryKey: ["unread-notifications"],
    queryFn: () => apiFetch("/notifications/unread-count"),
    refetchInterval: 30000,
  });
  const unreadCount = unreadData?.unread ?? 0;

  const isActive = (href: string) =>
    href === "/" ? pathname === "/" : pathname.startsWith(href);

  return (
    <aside className="fixed left-0 top-0 h-full w-64 bg-slate-900 text-white flex flex-col shadow-xl">
      <div className="p-6 border-b border-slate-700">
        <h1 className="text-xl font-extrabold tracking-tight">Affiliate AI</h1>
        <p className="text-sm text-slate-400 mt-1">Nền tảng tự động hóa</p>
      </div>

      <nav className="flex-1 p-4 overflow-y-auto">
        {navSections.map((section, si) => (
          <div key={si} className={si > 0 ? "mt-4" : ""}>
            {section.title && (
              <p className="px-3 mb-1.5 text-[10px] font-semibold tracking-widest text-slate-500 uppercase">
                {section.title}
              </p>
            )}
            <div className="space-y-0.5">
              {section.items.map((item) => (
                <Link
                  key={item.href}
                  href={item.href}
                  className={`flex items-center gap-3 px-3 py-2.5 rounded-lg text-[14px] font-medium transition-colors ${
                    isActive(item.href)
                      ? "bg-blue-600 text-white shadow-md"
                      : "text-slate-300 hover:bg-slate-800 hover:text-white"
                  }`}
                >
                  <span className="text-base">{item.icon}</span>
                  <span>{item.label}</span>
                </Link>
              ))}
            </div>
          </div>
        ))}
      </nav>

      <div className="p-4 border-t border-slate-700 space-y-1">
        <Link
          href="/notifications"
          className="flex items-center justify-between px-3 py-2.5 rounded-lg text-[14px] font-medium text-slate-300 hover:bg-slate-800 hover:text-white transition-colors"
        >
          <span className="flex items-center gap-3">
            <span className="text-base">🔔</span>
            <span>Thông báo</span>
          </span>
          {unreadCount > 0 && (
            <span className="bg-red-500 text-white text-xs px-1.5 py-0.5 rounded-full min-w-[20px] text-center">
              {unreadCount}
            </span>
          )}
        </Link>
        <p className="text-xs text-slate-500 px-3">v0.3.0</p>
      </div>
    </aside>
  );
}
