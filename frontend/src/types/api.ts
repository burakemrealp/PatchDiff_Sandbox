export interface HealthResponse {
  status: string;
  services: {
    postgresql: string;
    redis: string;
  };
  active_llm_provider: string;
}

export interface ChampionSummary {
  key: string;
  name: string;
  title: string;
  patch_version: string;
  base_stats: Record<string, number>;
}

export interface ItemSummary {
  item_id: string;
  name: string;
  gold_total: number;
  stats: Record<string, number>;
  icon_url?: string | null;
}

export interface StatDelta {
  stat_name: string;
  stat_label?: string | null;
  old_value: number;
  new_value: number;
  direction: 'BUFF' | 'NERF' | 'ADJUSTMENT';
  delta_percent: number;
}

export interface ScalingDelta {
  scaling_stat: string;
  old_ratio: number;
  new_ratio: number;
}

export interface AbilityDelta {
  slot: 'P' | 'Q' | 'W' | 'E' | 'R';
  ability_name?: string | null;
  damage_type: 'physical' | 'magic' | 'true';
  old_base_damage?: number[] | null;
  new_base_damage?: number[] | null;
  old_cooldown?: number[] | null;
  new_cooldown?: number[] | null;
  old_mana_cost?: number[] | null;
  new_mana_cost?: number[] | null;
  scaling_changes: ScalingDelta[];
  direction: 'BUFF' | 'NERF' | 'ADJUSTMENT';
}

export interface MechanicDelta {
  spell_name: string;
  spell_label?: string | null;
  field_name: string;
  field_label?: string | null;
  old_values: number[];
  new_values: number[];
  display_old?: string | null;
  display_new?: string | null;
  direction: 'BUFF' | 'NERF' | 'ADJUSTMENT';
}

export interface ChampionPatchDiff {
  champion_key: string;
  summary?: string | null;
  stat_deltas: StatDelta[];
  ability_deltas: AbilityDelta[];
  mechanic_deltas?: MechanicDelta[];
}

export interface PatchPayload {
  patch_version: string;
  champions: ChampionPatchDiff[];
}

export interface ParsePatchResponse {
  patch_version: string;
  engine_used: string;
  latency_ms: number;
  payload: PatchPayload;
  sanity_warnings: string[];
}

export interface LevelCurvePoint {
  level: number;
  target_hp: number;
  old_burst: number;
  new_burst: number;
  burst_delta_pct: number;
  old_dps: number;
  new_dps: number;
  dps_delta_pct: number;
  old_ttk_sec: number;
  new_ttk_sec: number;
  ttk_diff_sec: number;
  ehp_delta_pct: number;
  magic_ehp_delta_pct?: number;
}

export interface SimulationResult {
  champion_key: string;
  target_profile: 'squishy' | 'bruiser' | 'tank';
  target_label: string;
  game_context?: GameContext;
  summary: {
    early_game_lvl6: LevelCurvePoint;
    mid_game_lvl11: LevelCurvePoint;
    late_game_lvl18: LevelCurvePoint;
    late_game_lvl20?: LevelCurvePoint;
    avg_burst_delta_pct: number;
    avg_dps_delta_pct: number;
    avg_ehp_delta_pct: number;
    avg_magic_ehp_delta_pct?: number;
  };
  abilities: Record<
    string,
    {
      name: string;
      old_net_damage: number[];
      new_net_damage: number[];
      delta_percent: number[];
      old_cooldown: number[];
      new_cooldown: number[];
    }
  >;
  level_curves: LevelCurvePoint[];
}

export interface SimulateResponse {
  cached: boolean;
  cache_key: string;
  result: SimulationResult;
}

export type RoleKey = 'top' | 'jungle' | 'mid' | 'adc' | 'support';
export type MapKey = 'sr' | 'aram' | 'swiftplay';

export interface GameContext {
  role: RoleKey;
  role_label: string;
  game_map: MapKey;
  map_label: string;
  role_quests_enabled: boolean;
  quest_reward: string;
  max_level: number;
  legendary_slots: number;
  separate_boot_slot: boolean;
  total_item_slots: number;
  tier3_boots: boolean;
}

export interface LatestPatchInfo {
  version: string;
  display_version?: string | null;
  previous_version: string | null;
  previous_display_version?: string | null;
  sync_status: string;
  champions_count: number;
  items_count: number;
  runes_count: number;
  champions_changed: number;
  items_changed: number;
  runes_changed?: number;
  synced_at: string | null;
}

export interface LatestPatchResponse {
  synced: boolean;
  is_syncing: boolean;
  patch: LatestPatchInfo | null;
}

export interface SyncPatchResponse {
  status: 'up_to_date' | 'synced' | 'already_running' | 'error';
  message?: string;
  latest_version?: string;
  previous_version?: string | null;
  champions_count?: number;
  items_count?: number;
  runes_count?: number;
  champions_changed?: number;
  items_changed?: number;
}

export interface AutoChampionDiffEntry {
  entity_key: string;
  entity_name: string;
  direction: 'BUFF' | 'NERF' | 'ADJUSTMENT';
  diff: ChampionPatchDiff;
}

export interface AutoItemDiffEntry {
  entity_key: string;
  entity_name: string;
  direction: 'BUFF' | 'NERF' | 'ADJUSTMENT';
  icon_url?: string | null;
  diff: {
    item_id: string;
    name: string;
    gold_change: { old_gold: number; new_gold: number; delta: number; direction: string } | null;
    stat_changes: {
      stat_name: string;
      old_value: number;
      new_value: number;
      delta_percent: number;
      direction: string;
    }[];
    direction: 'BUFF' | 'NERF' | 'ADJUSTMENT';
    summary: string;
  };
}

export interface AutoRuneDiffEntry {
  entity_key: string;
  entity_name: string;
  direction: 'BUFF' | 'NERF' | 'ADJUSTMENT';
  diff: {
    rune_id: number;
    key: string;
    name: string;
    tree_name: string;
    summary: string;
  };
}

export interface PatchDiffsResponse {
  from_version: string | null;
  from_display_version?: string | null;
  to_version: string;
  to_display_version?: string | null;
  champions_count: number;
  items_count: number;
  runes_count?: number;
  champions: AutoChampionDiffEntry[];
  items: AutoItemDiffEntry[];
  runes?: AutoRuneDiffEntry[];
}

export interface RunePageEntry {
  rune_id: number;
  key: string;
  name: string;
  slot_index?: number;
}

export interface FullRunePage {
  primary_tree: {
    key: string;
    name: string;
    keystone: RunePageEntry;
    runes: RunePageEntry[];
  };
  secondary_tree: {
    key: string;
    name: string;
    runes: RunePageEntry[];
  };
  stat_shards: {
    slot: string;
    key: string;
    label: string;
  }[];
  synergy_notes: string[];
  stat_bonuses: Record<string, number>;
}

export interface RecommendedVariation {
  rank: number;
  playstyle: 'burst' | 'dps' | 'balanced';
  playstyle_label: string;
  score: number;
  total_gold: number;
  item_count?: number;
  items: {
    item_id: string;
    name: string;
    gold_total: number;
    stats: Record<string, number>;
    icon_url?: string | null;
    buy_order?: number;
    is_boot?: boolean;
    slot_type?: 'legendary' | 'standard_boot' | 'tier3_boot' | 'role_quest_boot';
  }[];
  keystone: {
    key: string;
    label: string;
    tree: string;
  };
  rune_page?: FullRunePage;
  metrics: {
    lvl11_burst: number;
    lvl18_burst: number;
    lvl_max_burst?: number;
    lvl11_dps: number;
    lvl18_dps: number;
    lvl_max_dps?: number;
    lvl11_ttk_sec: number;
    lvl18_ttk_sec: number;
    max_level?: number;
    phys_ehp_lvl11: number;
    magic_ehp_lvl11: number;
    ability_haste: number;
    gold_efficiency_index: number;
  };
  patch_shift: {
    from_version: string;
    to_version: string;
    lvl18_burst_delta_pct: number;
    lvl18_dps_delta_pct: number;
    lvl18_ttk_diff_sec: number;
    gold_delta: number;
    avg_power_shift_pct: number;
    status: 'GAINED' | 'LOST' | 'STABLE';
  };
  vs_old_meta: {
    burst_diff_pct: number;
    dps_diff_pct: number;
    ttk_diff_sec: number;
    gold_diff: number;
    is_new_meta_discovery: boolean;
  } | null;
  ai_review?: {
    playstyle: string;
    practicality_score: number;
    verdict: 'RECOMMENDED' | 'SITUATIONAL' | 'RISKY';
    title: string;
    rationale: string;
    rune_item_synergy?: string;
    strengths: string[];
    watchouts: string[];
  } | null;
}

export interface RecommendBuildsReport {
  champion_key: string;
  champion_name: string;
  from_version: string;
  from_display_version?: string | null;
  to_version: string;
  to_display_version?: string | null;
  target_profile: 'squishy' | 'bruiser' | 'tank';
  game_context?: GameContext;
  profile?: {
    kit_archetype_label?: string;
    patch_signals?: {
      adaptation_notes?: string[];
    };
  };
  champion_changed_in_patch: boolean;
  ai_summary?: string;
  old_meta_baseline: {
    playstyle: string;
    items: { item_id: string; name: string; gold_total: number; icon_url?: string | null }[];
    keystone: { key: string; label: string; tree: string };
    total_gold: number;
  } | null;
  variations: RecommendedVariation[];
}

export interface RecommendBuildsResponse {
  cached: boolean;
  cache_key: string;
  engine_used: string;
  latency_ms: number;
  report: RecommendBuildsReport;
}

export interface FeedbackSubmitPayload {
  patch_version: string;
  champion_key: string;
  role: string;
  game_map: string;
  target_profile: string;
  playstyle: string;
  items: { item_id: string; name: string; buy_order?: number }[];
  rune_page?: FullRunePage | null;
  rating: number;
  is_helpful: boolean;
  comment?: string;
}

export interface FeedbackCreateResponse {
  id: number;
  status: string;
  rating: number;
  is_helpful: boolean;
  created_at: string;
}

export interface FeedbackSummaryResponse {
  total_count: number;
  avg_rating: number;
  helpful_rate_pct: number;
  by_playstyle: Record<
    string,
    { count: number; avg_rating: number; helpful_rate_pct: number }
  >;
  recent_comments: {
    id: number;
    champion_key: string;
    playstyle: string;
    rating: number;
    is_helpful: boolean;
    comment: string;
    created_at: string;
  }[];
}