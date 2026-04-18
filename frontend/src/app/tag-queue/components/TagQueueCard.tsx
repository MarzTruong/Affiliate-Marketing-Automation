"use client";

import { useState } from "react";
import { markPublished, markTagged, type TagQueueItem } from "../lib/api";

type Props = {
  item: TagQueueItem;
  onUpdate: () => void;
};

export function TagQueueCard({ item, onUpdate }: Props) {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleTagged() {
    setLoading(true);
    setError(null);
    try {
      await markTagged(item.id);
      onUpdate();
    } catch (e) {
      setError(String(e));
    } finally {
      setLoading(false);
    }
  }

  async function handlePublished() {
    setLoading(true);
    setError(null);
    try {
      await markPublished(item.id);
      onUpdate();
    } catch (e) {
      setError(String(e));
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="rounded-lg border border-neutral-200 bg-white p-4 shadow-sm">
      <h3 className="truncate text-base font-semibold">{item.product_name}</h3>
      <p className="mt-1 text-sm text-neutral-500">
        Commission:{" "}
        <span className="font-medium text-green-600">
          {(item.commission_rate * 100).toFixed(0)}%
        </span>{" "}
        · SP: {item.product_id}
      </p>

      <a
        href={item.tiktok_draft_url}
        target="_blank"
        rel="noreferrer"
        className="mt-2 inline-flex items-center gap-1 text-sm text-blue-600 underline hover:text-blue-800"
      >
        Mở TikTok Draft ↗
      </a>

      {error && <p className="mt-2 text-xs text-red-600">{error}</p>}

      <div className="mt-3 flex gap-2">
        <button
          onClick={() => void handleTagged()}
          disabled={loading || !!item.tagged_at}
          className="rounded-md bg-yellow-100 px-3 py-1.5 text-sm font-medium text-yellow-900 hover:bg-yellow-200 disabled:opacity-50"
        >
          {item.tagged_at ? "✓ Đã tag SP" : "Đánh dấu đã tag"}
        </button>
        <button
          onClick={() => void handlePublished()}
          disabled={loading || !item.tagged_at}
          className="rounded-md bg-green-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-green-700 disabled:opacity-50"
        >
          ✓ Đã publish
        </button>
      </div>
    </div>
  );
}
