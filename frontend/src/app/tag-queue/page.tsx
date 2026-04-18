"use client";

import { useCallback, useEffect, useState } from "react";
import { TagQueueCard } from "./components/TagQueueCard";
import { fetchPending, type TagQueueItem } from "./lib/api";

export default function TagQueuePage() {
  const [items, setItems] = useState<TagQueueItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      setItems(await fetchPending());
    } catch (e) {
      setError(String(e));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  return (
    <main className="mx-auto max-w-5xl p-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Tag Queue</h1>
          <p className="mt-1 text-sm text-neutral-500">
            Video chờ tag sản phẩm TikTok Shop — mở draft, tag SP, bấm publish.
          </p>
        </div>
        <button
          onClick={() => void load()}
          disabled={loading}
          className="rounded-md bg-neutral-100 px-3 py-1.5 text-sm hover:bg-neutral-200 disabled:opacity-50"
        >
          {loading ? "Đang tải..." : "Làm mới"}
        </button>
      </div>

      {error && (
        <div className="mt-4 rounded-md bg-red-50 p-3 text-sm text-red-700">
          Lỗi: {error}
        </div>
      )}

      {!loading && !error && items.length === 0 && (
        <div className="mt-8 rounded-lg border border-dashed border-neutral-300 p-12 text-center">
          <p className="text-neutral-500">Không có video nào cần tag.</p>
          <p className="mt-1 text-sm text-neutral-400">
            Khi có video được gen xong, chúng sẽ xuất hiện ở đây.
          </p>
        </div>
      )}

      <div className="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
        {items.map((item) => (
          <TagQueueCard key={item.id} item={item} onUpdate={() => void load()} />
        ))}
      </div>

      {!loading && items.length > 0 && (
        <p className="mt-4 text-right text-xs text-neutral-400">
          {items.length} video đang chờ tag
        </p>
      )}
    </main>
  );
}
