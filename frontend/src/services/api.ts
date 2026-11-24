import type {
  ChampionPatchDiff,
  ChampionSummary,
  FeedbackCreateResponse,
  FeedbackSubmitPayload,
  FeedbackSummaryResponse,
  HealthResponse,
  ItemSummary,
  LatestPatchResponse,
  MapKey,
  ParsePatchResponse,
  PatchDiffsResponse,
  RecommendBuildsResponse,
  RoleKey,
  SimulateResponse,
  SyncPatchResponse,
  ZeroDayRadarResponse,
} from '../types/api';

const API_BASE = (
  import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000/api/v1'
).replace(/\/+$/, '');

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  });

  if (!res.ok) {
    const errText = await res.text();
    throw new Error(`API Error (${res.status}): ${errText}`);
  }
  return res.json() as Promise<T>;
}

export const api = {
  getHealth: () => request<HealthResponse>('/health'),
  getChampions: (lang?: string) =>
    request<ChampionSummary[]>(`/champions${lang ? `?lang=${encodeURIComponent(lang)}` : ''}`),
  getItems: (lang?: string) =>
    request<ItemSummary[]>(`/items${lang ? `?lang=${encodeURIComponent(lang)}` : ''}`),

  parsePatch: (raw_text: string, patch_version = '26.23') =>
    request<ParsePatchResponse>('/parse-patch', {
      method: 'POST',
      body: JSON.stringify({ raw_text, patch_version }),
    }),

  simulate: (payload: {
    champion_key: string;
    item_ids: string[];
    target_profile: 'squishy' | 'bruiser' | 'tank';
    patch_diff: ChampionPatchDiff | null;
    from_version?: string | null;
    keystone_key?: string | null;
    role?: RoleKey;
    game_map?: MapKey;
    lang?: string;
    raw_patch_text?: string;
  }) =>
    request<SimulateResponse>('/simulate', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),

  getLatestPatch: () => request<LatestPatchResponse>('/patches/latest'),

  syncPatches: (force = false) =>
    request<SyncPatchResponse>(`/patches/sync?force=${force}`, {
      method: 'POST',
    }),

  getPatchDiffs: (version: string, lang?: string) =>
    request<PatchDiffsResponse>(
      `/patches/${encodeURIComponent(version)}/diffs${lang ? `?lang=${encodeURIComponent(lang)}` : ''}`
    ),

  getZeroDayRadar: (params?: {
    to_version?: string | null;
    target_profile?: 'squishy' | 'bruiser' | 'tank';
    game_map?: MapKey;
    limit?: number;
    lang?: string;
  }) => {
    const query = new URLSearchParams();
    if (params?.to_version) query.set('to_version', params.to_version);
    if (params?.target_profile) query.set('target_profile', params.target_profile);
    if (params?.game_map) query.set('game_map', params.game_map);
    if (params?.limit) query.set('limit', String(params.limit));
    if (params?.lang) query.set('lang', params.lang);
    const qs = query.toString();
    return request<ZeroDayRadarResponse>(`/patches/zero-day-radar${qs ? `?${qs}` : ''}`);
  },

  recommendBuilds: (payload: {
    champion_key: string;
    target_profile: 'squishy' | 'bruiser' | 'tank';
    role?: RoleKey | null;
    game_map?: MapKey;
    to_version?: string | null;
    use_ai?: boolean;
    lang?: string;
  }) =>
    request<RecommendBuildsResponse>('/recommend-builds', {
      method: 'POST',
      body: JSON.stringify({ use_ai: true, ...payload }),
    }),

  submitFeedback: (payload: FeedbackSubmitPayload) =>
    request<FeedbackCreateResponse>('/feedback', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),

  getFeedbackSummary: (championKey?: string, patchVersion?: string) => {
    const params = new URLSearchParams();
    if (championKey) params.set('champion_key', championKey);
    if (patchVersion) params.set('patch_version', patchVersion);
    const qs = params.toString();
    return request<FeedbackSummaryResponse>(`/feedback/summary${qs ? `?${qs}` : ''}`);
  },
};