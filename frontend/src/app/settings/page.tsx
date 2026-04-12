"use client";

import { useState, useEffect } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api-client";

interface CredentialItem {
  key: string;
  group: string;
  label: string;
  sensitive: boolean;
  value: string;
}

interface CredentialsResponse {
  credentials: CredentialItem[];
}

interface TestResult {
  status: "connected" | "failed" | "error";
  platform: string;
  detail?: string;
}

const GROUP_META: Record<
  string,
  { label: string; icon: string; testPlatform?: string }
> = {
  ai: { label: "AI (Anthropic Claude)", icon: "🤖" },
  facebook: {
    label: "Facebook",
    icon: "📘",
    testPlatform: "facebook",
  },
  wordpress: {
    label: "WordPress",
    icon: "🌐",
    testPlatform: "wordpress",
  },
  telegram: {
    label: "Telegram",
    icon: "✈️",
    testPlatform: "telegram",
  },
  tiktok: {
    label: "TikTok",
    icon: "🎵",
    testPlatform: "tiktok",
  },
  shopee: { label: "Shopee", icon: "🛒", testPlatform: "shopee" },
  shopback: { label: "ShopBack", icon: "💰", testPlatform: "shopback" },
  accesstrade: {
    label: "AccessTrade VN",
    icon: "🔗",
    testPlatform: "accesstrade",
  },
  bannerbear: { label: "Bannerbear (Ảnh tự động)", icon: "🖼️" },
};

export default function SettingsPage() {
  const qc = useQueryClient();
  const [values, setValues] = useState<Record<string, string>>({});
  const [saveStatus, setSaveStatus] = useState<
    "idle" | "saving" | "saved" | "error"
  >("idle");
  const [testResults, setTestResults] = useState<Record<string, TestResult>>(
    {}
  );
  const [testingPlatform, setTestingPlatform] = useState<string | null>(null);
  const [showValues, setShowValues] = useState<Record<string, boolean>>({});

  const { data, isLoading } = useQuery<CredentialsResponse>({
    queryKey: ["settings-credentials"],
    queryFn: () => apiFetch("/settings/credentials"),
  });

  // Khởi tạo local state từ API response
  // Sensitive fields dùng "" thay vì "****" để user gõ thẳng không cần xóa trước
  useEffect(() => {
    if (data?.credentials) {
      const initial: Record<string, string> = {};
      for (const item of data.credentials) {
        initial[item.key] = item.sensitive && item.value === "****" ? "" : item.value;
      }
      setValues(initial);
    }
  }, [data]);

  const saveMutation = useMutation({
    mutationFn: (updates: { key: string; value: string }[]) =>
      apiFetch("/settings/credentials", {
        method: "POST",
        body: JSON.stringify({ updates }),
      }),
    onSuccess: () => {
      setSaveStatus("saved");
      qc.invalidateQueries({ queryKey: ["settings-credentials"] });
      setTimeout(() => setSaveStatus("idle"), 3000);
    },
    onError: () => {
      setSaveStatus("error");
      setTimeout(() => setSaveStatus("idle"), 3000);
    },
  });

  const handleSave = () => {
    if (!data?.credentials) return;
    setSaveStatus("saving");
    const updates = data.credentials.map((item) => ({
      key: item.key,
      value: values[item.key] ?? "",
    }));
    saveMutation.mutate(updates);
  };

  const handleTest = async (platformKey: string) => {
    setTestingPlatform(platformKey);
    try {
      // Gọi test với platform name (không cần platform_id vì dùng config từ .env)
      const result = await apiFetch<TestResult>(
        `/settings/test-connection/${platformKey}`
      );
      setTestResults((prev) => ({ ...prev, [platformKey]: result }));
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Lỗi không xác định";
      setTestResults((prev) => ({
        ...prev,
        [platformKey]: { status: "error", platform: platformKey, detail: msg },
      }));
    } finally {
      setTestingPlatform(null);
    }
  };

  const toggleShow = (key: string) => {
    setShowValues((prev) => ({ ...prev, [key]: !prev[key] }));
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-48 text-gray-400">
        Đang tải cài đặt...
      </div>
    );
  }

  // Nhóm credentials theo group
  const grouped: Record<string, CredentialItem[]> = {};
  for (const item of data?.credentials ?? []) {
    if (!grouped[item.group]) grouped[item.group] = [];
    grouped[item.group].push(item);
  }

  const hasChanges = data?.credentials.some((item) => {
    const current = values[item.key] ?? "";
    return current !== item.value && current !== "****";
  });

  return (
    <div className="max-w-3xl">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Cài đặt Credentials</h1>
        <button
          onClick={handleSave}
          disabled={!hasChanges || saveStatus === "saving"}
          className={`px-5 py-2 rounded-lg text-sm font-medium transition-colors ${
            saveStatus === "saved"
              ? "bg-green-500 text-white"
              : saveStatus === "error"
                ? "bg-red-500 text-white"
                : hasChanges
                  ? "bg-blue-600 hover:bg-blue-700 text-white"
                  : "bg-gray-200 text-gray-400 cursor-not-allowed"
          }`}
        >
          {saveStatus === "saving"
            ? "Đang lưu..."
            : saveStatus === "saved"
              ? "✓ Đã lưu"
              : saveStatus === "error"
                ? "✗ Lỗi"
                : "Lưu thay đổi"}
        </button>
      </div>

      <p className="text-sm text-gray-500 mb-6">
        Nhập API keys và credentials. Giá trị đã lưu hiển thị là{" "}
        <code className="bg-gray-100 px-1 rounded">****</code>. Để trống hoặc
        giữ <code className="bg-gray-100 px-1 rounded">****</code> để giữ
        nguyên giá trị cũ.
      </p>

      <div className="space-y-6">
        {Object.entries(grouped).map(([group, items]) => {
          const meta = GROUP_META[group] ?? { label: group, icon: "⚙️" };
          const testResult = meta.testPlatform
            ? testResults[meta.testPlatform]
            : null;
          const isTesting = testingPlatform === meta.testPlatform;

          return (
            <div
              key={group}
              className="bg-white rounded-xl shadow-sm border overflow-hidden"
            >
              {/* Header nhóm */}
              <div className="flex items-center justify-between px-5 py-3 bg-gray-50 border-b">
                <div className="flex items-center gap-2">
                  <span className="text-lg">{meta.icon}</span>
                  <h2 className="font-semibold text-gray-800">{meta.label}</h2>
                </div>
                {meta.testPlatform && (
                  <div className="flex items-center gap-3">
                    {testResult && (
                      <span
                        className={`text-xs font-medium px-2 py-1 rounded-full ${
                          testResult.status === "connected"
                            ? "bg-green-100 text-green-700"
                            : "bg-red-100 text-red-700"
                        }`}
                      >
                        {testResult.status === "connected"
                          ? "✅ Kết nối OK"
                          : `❌ ${testResult.detail ?? "Thất bại"}`}
                      </span>
                    )}
                    <button
                      onClick={() => handleTest(meta.testPlatform!)}
                      disabled={isTesting}
                      className="text-xs px-3 py-1.5 border border-gray-300 rounded-lg hover:bg-gray-100 transition-colors disabled:opacity-50"
                    >
                      {isTesting ? "Đang test..." : "Test kết nối"}
                    </button>
                  </div>
                )}
              </div>

              {/* Fields */}
              <div className="p-5 space-y-4">
                {items.map((item) => (
                  <div key={item.key}>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      {item.label}
                      <span className="ml-2 text-xs text-gray-400 font-mono">
                        {item.key}
                      </span>
                    </label>
                    <div className="relative">
                      <input
                        type={
                          item.sensitive && !showValues[item.key]
                            ? "password"
                            : "text"
                        }
                        value={values[item.key] ?? ""}
                        onChange={(e) =>
                          setValues((prev) => ({
                            ...prev,
                            [item.key]: e.target.value,
                          }))
                        }
                        placeholder={
                          item.sensitive
                            ? "Nhập để thay đổi (để trống = giữ nguyên)"
                            : "Nhập giá trị..."
                        }
                        className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 pr-10"
                      />
                      {item.sensitive && (
                        <button
                          type="button"
                          onClick={() => toggleShow(item.key)}
                          className="absolute right-2 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600 text-xs"
                        >
                          {showValues[item.key] ? "Ẩn" : "Hiện"}
                        </button>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          );
        })}
      </div>

      {/* Nút lưu bottom */}
      <div className="mt-6 flex justify-end">
        <button
          onClick={handleSave}
          disabled={!hasChanges || saveStatus === "saving"}
          className={`px-6 py-2.5 rounded-lg text-sm font-medium transition-colors ${
            saveStatus === "saved"
              ? "bg-green-500 text-white"
              : saveStatus === "error"
                ? "bg-red-500 text-white"
                : hasChanges
                  ? "bg-blue-600 hover:bg-blue-700 text-white"
                  : "bg-gray-200 text-gray-400 cursor-not-allowed"
          }`}
        >
          {saveStatus === "saving"
            ? "Đang lưu..."
            : saveStatus === "saved"
              ? "✓ Đã lưu thành công"
              : saveStatus === "error"
                ? "✗ Lưu thất bại"
                : "Lưu thay đổi"}
        </button>
      </div>
    </div>
  );
}
