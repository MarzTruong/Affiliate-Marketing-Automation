const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000";

export type TagQueueItem = {
  id: string;
  video_id: string;
  tiktok_draft_url: string;
  product_id: string;
  product_name: string;
  commission_rate: number;
  tagged_at: string | null;
  published_at: string | null;
};

export async function fetchPending(): Promise<TagQueueItem[]> {
  const res = await fetch(`${API_BASE}/api/tag-queue/pending`, {
    cache: "no-store",
  });
  if (!res.ok) throw new Error(`fetchPending failed: ${res.status}`);
  return res.json() as Promise<TagQueueItem[]>;
}

export async function markTagged(id: string): Promise<void> {
  const res = await fetch(`${API_BASE}/api/tag-queue/${id}/tagged`, {
    method: "POST",
  });
  if (!res.ok) throw new Error(`markTagged failed: ${res.status}`);
}

export async function markPublished(id: string): Promise<void> {
  const res = await fetch(`${API_BASE}/api/tag-queue/${id}/published`, {
    method: "POST",
  });
  if (!res.ok) throw new Error(`markPublished failed: ${res.status}`);
}
