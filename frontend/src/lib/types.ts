export type Platform = "instagram" | "linkedin" | "x";
export type Status = "pending" | "approved" | "publishing" | "published" | "failed" | "rejected";

export interface Slide { title: string; body?: string; layout?: string; items?: string[]; stat?: string; source?: string; image_prompt?: string; left?: string; right?: string; highlight?: string }
export interface DraftContent {
  caption?: string;
  thread?: string[];
  slides?: Slide[];
  reel_script?: { text: string; seconds: number }[];
  hashtags?: string[];
  cta?: string;
  alt_text?: string;
  image_headline?: string;
  archetype?: string;
  goal?: string;
  template?: string;
  hook?: string;
  hook_options?: { type: string; text: string; score?: number; hookscore?: number; verdict?: string }[];
  why_viral?: string;
  sources?: { title: string; url: string }[];
  unverified?: string[];
  permalink?: string;
}
export interface Critic {
  scores?: Record<string, number>;
  overall?: number;
  viral_score?: number;
  predicted_action?: string;
  artefacts_stripped?: number;
  quality?: {
    human?: { score: number; verdict: string; weakest: string; checks: Record<string, number> };
    hook?: { score: number; verdict: string; weakest: string; dealbreakers: string[] };
    beats?: { seconds: number; problems: string[]; notes: string[] };
    caption?: { verdict: string; visible: string; fails: string[]; warns: string[] };
  };
  verdict?: string;
  feedback?: string;
  violations?: string[];
}
export interface Metrics { impressions: number; likes: number; comments: number; shares: number; saves: number; follows: number; engagement: number }
export interface Draft {
  id: number;
  page_id: string;
  platform: Platform;
  kind: "post" | "reply";
  format: string;
  pillar: string;
  topic: string;
  angle: string;
  content: DraftContent;
  media: { url: string; type: string }[];
  critic: Critic;
  trace: string[];
  reply_context?: string | null;
  status: Status;
  scheduled_at: string | null;
  published_id?: string | null;
  error?: string | null;
  created_at: string;
  updated_at: string;
  metrics: Metrics | null;
}
export interface Page {
  id: string;
  platform: Platform;
  handle: string;
  niche: string;
  audience: string;
  goal: string;
  voice: string;
  pillars: { name: string; description: string }[];
  formats: string[];
  posts_per_week: number;
  preferred_slots: string[];
  hashtags: { core: string[]; max_per_post: number };
  brand: { bg: string; fg: string; accent: string };
  avoid: string[];
  cta_options: string[];
}
export interface PageStats {
  platform: Platform; handle: string; niche: string; followers: number | null; growth_7d: number; growth_30d: number;
  published: number; pending: number; avg_engagement: number; posts_per_week: number;
}
export interface Overview {
  mode: string;
  counts: Record<Status, number>;
  pages: Record<string, PageStats>;
  followers_series: ({ date: string } & Record<string, number | string>)[];
  by_format: { key: string; platform: Platform; format: string; posts: number; avg_engagement: number }[];
  by_hour: { hour: number; posts: number; avg_engagement: number }[];
  activity: { id: number; page_id: string; platform: Platform; kind: string; format: string; topic: string; status: Status; at: string }[];
  upcoming: Draft[];
}
export interface Analytics {
  posts_analysed: number;
  by_pillar: Record<string, { posts: number; avg_engagement: number }>;
  by_format: Record<string, { posts: number; avg_engagement: number }>;
  by_hour: Record<string, { posts: number; avg_engagement: number }>;
  top_posts: { topic: string; angle: string; format: string; engagement: number }[];
  by_archetype?: Record<string, { posts: number; avg_engagement: number }>;
  by_template?: Record<string, { posts: number; avg_engagement: number }>;
  followers: { start: number; now: number; delta: number } | null;
}
