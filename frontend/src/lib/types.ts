export interface Campaign {
  id: string;
  name: string;
  platform: string;
  platform_account_id: string | null;
  status: string;
  budget_daily: number | null;
  target_category: string | null;
  config: Record<string, unknown> | null;
  created_at: string;
  updated_at: string;
}

export interface ContentPiece {
  id: string;
  product_id: string | null;
  campaign_id: string;
  content_type: string;
  title: string | null;
  body: string;
  seo_keywords: string[] | null;
  template_id: string | null;
  variant: string | null;
  claude_model: string | null;
  token_cost_input: number | null;
  token_cost_output: number | null;
  estimated_cost_usd: number | null;
  status: string;
  published_at: string | null;
  created_at: string;
}

export interface AnalyticsOverview {
  period: { start: string; end: string };
  total_clicks: number;
  total_conversions: number;
  total_revenue: number;
  total_impressions: number;
  ctr: number;
  conversion_rate: number;
}

export interface DailyStats {
  date: string;
  clicks: number;
  conversions: number;
  revenue: number;
  impressions: number;
}

export interface CostSummary {
  content_type: string;
  count: number;
  total_input_tokens: number;
  total_output_tokens: number;
  total_cost_usd: number;
}

export interface Product {
  id: string;
  campaign_id: string;
  platform: string;
  external_product_id: string | null;
  name: string;
  original_url: string;
  affiliate_url: string | null;
  price: number | null;
  category: string | null;
  created_at: string;
}

export interface Publication {
  id: string;
  content_id: string;
  platform: string;
  channel: string | null;
  external_post_id: string | null;
  published_at: string | null;
  scheduled_at: string | null;
  status: string;
}

export interface SystemStats {
  campaigns: { total: number; active: number };
  content: { total: number; published: number };
  publications: { total: number; success: number };
  templates: { total: number; active: number };
  ab_tests_running: number;
  fraud_unresolved: number;
  total_ai_cost_usd: number;
  analytics_events: number;
}

export interface SystemHealth {
  status: string;
  timestamp: string;
  checks: Record<string, { status: string; detail?: string }>;
}

// ── Automation types ────────────────────────────────────────────────────

export interface AutomationRule {
  id: string;
  name: string;
  platform: string;
  category: string | null;
  is_active: boolean;
  cron_expression: string;
  min_commission_pct: number | null;
  min_price: number | null;
  max_price: number | null;
  publish_channels: Record<string, boolean> | null;
  content_types: Record<string, boolean> | null;
  generate_visual: boolean;
  created_at: string;
}

export interface PipelineRun {
  id: string;
  rule_id: string;
  status: string;
  products_found: number;
  products_filtered: number;
  content_created: number;
  visuals_created: number;
  posts_scheduled: number;
  started_at: string;
  finished_at: string | null;
  error_log: string | null;
}

export interface ScheduledPost {
  id: string;
  content_id: string;
  channel: string;
  scheduled_at: string;
  published_at: string | null;
  status: string;
  visual_url: string | null;
}

export interface CalendarDay {
  id: string;
  title: string;
  channel: string;
  hour: string;
  status: string;
  visual_url: string | null;
}

export interface WeekCalendar {
  week_start: string;
  week_end: string;
  days: Record<string, CalendarDay[]>;
}

export interface ChatMessage {
  role: "user" | "assistant";
  content: string;
  timestamp: string;
}

export interface PlatformBreakdown {
  platform: string;
  clicks: number;
  conversions: number;
  revenue: number;
  impressions: number;
  ctr: number;
  conversion_rate: number;
}
