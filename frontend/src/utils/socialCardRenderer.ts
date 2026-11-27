import type { TranslationDict } from '../i18n';
import type { ZeroDayChampionEntry, ZeroDayRadarReport } from '../types/api';

function formatSignedPct(val: number): string {
  const sign = val > 0 ? '+' : '';
  return `${sign}${val.toFixed(2)}%`;
}

export function buildZeroDayShareText(radar: ZeroDayRadarReport, t: TranslationDict): string {
  const sc = radar.share_card;
  const lines: string[] = [
    sc.headline,
    sc.subtitle,
    '',
    `- ${t.zeroDayStatScanned}: ${radar.champions_scanned} | ${t.zeroDayStatMyths}: ${radar.summary_counts.myths_busted} | ${t.zeroDayStatHiddenWinners}: ${radar.summary_counts.hidden_winners} | ${t.zeroDayStatHiddenLosers}: ${radar.summary_counts.hidden_losers}`,
  ];

  if (sc.top_winner) {
    lines.push(
      `- ${t.zeroDayCardBestWinner}: ${sc.top_winner.champion_name} (${formatSignedPct(sc.top_winner.power_shift_score)})`
    );
  }
  if (sc.top_hidden_mover) {
    const cat = sc.top_hidden_mover.catalysts.map((c) => c.entity_name).join(', ');
    lines.push(
      `- ${t.zeroDayCardHiddenMover}: ${sc.top_hidden_mover.champion_name} (${formatSignedPct(sc.top_hidden_mover.power_shift_score)})${cat ? ` [${cat}]` : ''}`
    );
  }
  if (sc.top_myth) {
    lines.push(
      `- ${t.zeroDayCardTopMyth}: ${sc.top_myth.champion_name} — ${sc.top_myth.verdict_label || sc.top_myth.verdict_code || ''} (${formatSignedPct(sc.top_myth.power_shift_score)})`
    );
  }

  lines.push(
    '',
    'Live Web App: https://patchdiff-sandbox.pages.dev',
    'Open Source: https://github.com/burakemrealp/PatchDiff_Sandbox'
  );
  return lines.join('\n');
}

function drawCanvasHextechCrest(
  ctx: CanvasRenderingContext2D,
  ox: number,
  oy: number,
  boxSize: number
): void {
  const k = boxSize / 64;
  const px = (x: number) => ox + x * k;
  const py = (y: number) => oy + y * k;

  ctx.save();
  // Outer chamfered octagon shield
  ctx.beginPath();
  ctx.moveTo(px(20), py(4));
  ctx.lineTo(px(44), py(4));
  ctx.lineTo(px(60), py(20));
  ctx.lineTo(px(60), py(44));
  ctx.lineTo(px(44), py(60));
  ctx.lineTo(px(20), py(60));
  ctx.lineTo(px(4), py(44));
  ctx.lineTo(px(4), py(20));
  ctx.closePath();
  ctx.fillStyle = '#0e1e38';
  ctx.fill();
  ctx.lineWidth = Math.max(1.5, 2.5 * k);
  ctx.strokeStyle = '#d8ad52';
  ctx.stroke();

  // Left gold facet ("Before")
  ctx.beginPath();
  ctx.moveTo(px(30.5), py(19));
  ctx.lineTo(px(18.5), py(33));
  ctx.lineTo(px(30.5), py(49));
  ctx.closePath();
  ctx.fillStyle = '#c49434';
  ctx.fill();

  // Right teal facet ("After / Buff Spike")
  ctx.beginPath();
  ctx.moveTo(px(33.5), py(13));
  ctx.lineTo(px(47), py(31.5));
  ctx.lineTo(px(33.5), py(48.5));
  ctx.closePath();
  ctx.fillStyle = '#0abcb2';
  ctx.fill();

  // Apex nexus diamond
  ctx.beginPath();
  ctx.moveTo(px(33.5), py(7.5));
  ctx.lineTo(px(36.5), py(11.5));
  ctx.lineTo(px(33.5), py(15.5));
  ctx.lineTo(px(30.5), py(11.5));
  ctx.closePath();
  ctx.fillStyle = '#f8e09b';
  ctx.fill();
  ctx.restore();
}

function drawRoundedRect(
  ctx: CanvasRenderingContext2D,
  x: number,
  y: number,
  w: number,
  h: number,
  r: number
): void {
  ctx.beginPath();
  ctx.moveTo(x + r, y);
  ctx.lineTo(x + w - r, y);
  ctx.quadraticCurveTo(x + w, y, x + w, y + r);
  ctx.lineTo(x + w, y + h - r);
  ctx.quadraticCurveTo(x + w, y + h, x + w - r, y + h);
  ctx.lineTo(x + r, y + h);
  ctx.quadraticCurveTo(x, y + h, x, y + h - r);
  ctx.lineTo(x, y + r);
  ctx.quadraticCurveTo(x, y, x + r, y);
  ctx.closePath();
}

function drawWrappedText(
  ctx: CanvasRenderingContext2D,
  text: string,
  x: number,
  y: number,
  maxWidth: number,
  lineHeight: number,
  maxLines: number
): number {
  const words = text.split(/\s+/).filter(Boolean);
  if (words.length === 0) return y;
  let line = '';
  let currentY = y;
  let rendered = 0;

  for (let i = 0; i < words.length; i += 1) {
    const candidate = line ? `${line} ${words[i]}` : words[i];
    if (ctx.measureText(candidate).width > maxWidth && line) {
      ctx.fillText(line, x, currentY);
      rendered += 1;
      currentY += lineHeight;
      line = words[i];
      if (rendered >= maxLines - 1) {
        const remaining = [line, ...words.slice(i + 1)].join(' ');
        const trimmed =
          ctx.measureText(remaining).width > maxWidth
            ? `${remaining.slice(0, Math.max(8, Math.floor(remaining.length * 0.72)))}...`
            : remaining;
        ctx.fillText(trimmed, x, currentY);
        return currentY + lineHeight;
      }
    } else {
      line = candidate;
    }
  }
  if (line) {
    ctx.fillText(line, x, currentY);
    currentY += lineHeight;
  }
  return currentY;
}

function drawSpotlightColumn(
  ctx: CanvasRenderingContext2D,
  x: number,
  y: number,
  w: number,
  h: number,
  accentHex: string,
  title: string,
  entry: ZeroDayChampionEntry | null,
  fallbackText: string,
  subtitleText: string
): void {
  drawRoundedRect(ctx, x, y, w, h, 16);
  ctx.fillStyle = 'rgba(15, 23, 42, 0.88)';
  ctx.fill();
  ctx.lineWidth = 1.5;
  ctx.strokeStyle = accentHex;
  ctx.stroke();

  ctx.textAlign = 'left';
  ctx.fillStyle = accentHex;
  ctx.font = '700 13px system-ui, -apple-system, Segoe UI, sans-serif';
  ctx.fillText(title.toUpperCase(), x + 22, y + 34);

  if (!entry) {
    ctx.fillStyle = '#94a3b8';
    ctx.font = '500 15px system-ui, -apple-system, Segoe UI, sans-serif';
    drawWrappedText(ctx, fallbackText, x + 22, y + 84, w - 44, 22, 3);
    return;
  }

  ctx.fillStyle = '#f8fafc';
  ctx.font = '800 30px system-ui, -apple-system, Segoe UI, sans-serif';
  ctx.fillText(entry.champion_name, x + 22, y + 84);

  const scoreStr = formatSignedPct(entry.power_shift_score);
  ctx.fillStyle = entry.power_shift_score >= 0 ? '#34d399' : '#fb7185';
  ctx.font = '800 40px ui-monospace, SFMono-Regular, Menlo, monospace';
  ctx.fillText(scoreStr, x + 22, y + 142);

  ctx.fillStyle = '#cbd5e1';
  ctx.font = '500 14px system-ui, -apple-system, Segoe UI, sans-serif';
  drawWrappedText(ctx, subtitleText, x + 22, y + 182, w - 44, 21, 3);
}

export function downloadZeroDayCardPng(
  radar: ZeroDayRadarReport,
  t: TranslationDict,
  localeCode: string,
  dir: 'ltr' | 'rtl'
): void {
  const width = 1200;
  const height = 630;
  const scale = 2;

  const canvas = document.createElement('canvas');
  canvas.width = width * scale;
  canvas.height = height * scale;
  const ctx = canvas.getContext('2d');
  if (!ctx) return;

  ctx.scale(scale, scale);

  // Hextech Twilight background gradient
  const bg = ctx.createLinearGradient(0, 0, width, height);
  bg.addColorStop(0, '#091428');
  bg.addColorStop(0.55, '#10203a');
  bg.addColorStop(1, '#141c3c');
  ctx.fillStyle = bg;
  ctx.fillRect(0, 0, width, height);

  // Subtle background grid & Hextech outer gold border
  ctx.strokeStyle = 'rgba(10, 200, 185, 0.06)';
  ctx.lineWidth = 1;
  for (let gx = 0; gx < width; gx += 48) {
    ctx.beginPath();
    ctx.moveTo(gx, 0);
    ctx.lineTo(gx, height);
    ctx.stroke();
  }
  for (let gy = 0; gy < height; gy += 48) {
    ctx.beginPath();
    ctx.moveTo(0, gy);
    ctx.lineTo(width, gy);
    ctx.stroke();
  }
  drawRoundedRect(ctx, 16, 16, width - 32, height - 32, 18);
  ctx.strokeStyle = 'rgba(200, 155, 60, 0.48)';
  ctx.lineWidth = 1.5;
  ctx.stroke();

  // Top Hextech Diff-Crystal crest + brand pill & patch transition badge
  drawCanvasHextechCrest(ctx, 48, 32, 44);
  drawRoundedRect(ctx, 104, 37, 345, 34, 17);
  ctx.fillStyle = 'rgba(10, 200, 185, 0.14)';
  ctx.fill();
  ctx.strokeStyle = 'rgba(10, 200, 185, 0.45)';
  ctx.lineWidth = 1;
  ctx.stroke();
  ctx.fillStyle = '#73eae1';
  ctx.font = '700 13px system-ui, -apple-system, Segoe UI, sans-serif';
  ctx.textAlign = 'left';
  ctx.fillText('PATCHDIFF SANDBOX · ZERO-VANGUARD MATH ENGINE', 120, 59);

  drawRoundedRect(ctx, width - 228, 38, 180, 34, 17);
  ctx.fillStyle = 'rgba(168, 85, 247, 0.2)';
  ctx.fill();
  ctx.strokeStyle = 'rgba(192, 132, 252, 0.5)';
  ctx.stroke();
  ctx.fillStyle = '#e9d5ff';
  ctx.textAlign = 'center';
  ctx.font = '700 14px ui-monospace, SFMono-Regular, Menlo, monospace';
  ctx.fillText(radar.share_card.patch_transition, width - 138, 60);

  // Headline & subtitle
  const textAnchorX = dir === 'rtl' ? width - 48 : 48;
  ctx.textAlign = dir === 'rtl' ? 'right' : 'left';
  ctx.fillStyle = '#f8fafc';
  ctx.font = '800 32px system-ui, -apple-system, Segoe UI, sans-serif';
  drawWrappedText(ctx, radar.share_card.headline, textAnchorX, 118, width - 96, 38, 2);

  ctx.fillStyle = '#94a3b8';
  ctx.font = '500 16px system-ui, -apple-system, Segoe UI, sans-serif';
  drawWrappedText(ctx, radar.share_card.subtitle, textAnchorX, 162, width - 96, 22, 2);

  // 3 Spotlight columns
  const colW = 344;
  const colH = 264;
  const colY = 216;
  const gap = 36;
  const sc = radar.share_card;

  const winnerSub = sc.top_winner
    ? `${sc.top_winner.role_label} · ${sc.top_winner.kit_archetype_label}`
    : '';
  const hiddenSub = sc.top_hidden_mover
    ? `${t.zeroDayCatalystsLabel}: ${
        sc.top_hidden_mover.catalysts.map((c) => c.entity_name).join(', ') || '-'
      }`
    : '';
  const mythSub = sc.top_myth
    ? sc.top_myth.verdict_label || sc.top_myth.verdict_summary || ''
    : '';

  drawSpotlightColumn(
    ctx,
    48,
    colY,
    colW,
    colH,
    'rgba(16, 185, 129, 0.55)',
    t.zeroDayCardBestWinner,
    sc.top_winner,
    '-',
    winnerSub
  );

  drawSpotlightColumn(
    ctx,
    48 + colW + gap,
    colY,
    colW,
    colH,
    'rgba(245, 158, 11, 0.55)',
    t.zeroDayCardHiddenMover,
    sc.top_hidden_mover,
    t.zeroDayEmptyHiddenLosers,
    hiddenSub
  );

  drawSpotlightColumn(
    ctx,
    48 + (colW + gap) * 2,
    colY,
    colW,
    colH,
    'rgba(168, 85, 247, 0.6)',
    t.zeroDayCardTopMyth,
    sc.top_myth,
    '-',
    mythSub
  );

  // Footer summary strip
  drawRoundedRect(ctx, 48, 506, width - 96, 52, 12);
  ctx.fillStyle = 'rgba(30, 41, 59, 0.72)';
  ctx.fill();
  ctx.textAlign = 'center';
  ctx.fillStyle = '#e2e8f0';
  ctx.font = '600 15px system-ui, -apple-system, Segoe UI, sans-serif';
  const kpiLine = `${t.zeroDayStatScanned}: ${radar.champions_scanned}   ·   ${t.zeroDayStatMyths}: ${radar.summary_counts.myths_busted}   ·   ${t.zeroDayStatHiddenWinners}: ${radar.summary_counts.hidden_winners}   ·   ${t.zeroDayStatHiddenLosers}: ${radar.summary_counts.hidden_losers}`;
  ctx.fillText(kpiLine, width / 2, 537);

  ctx.fillStyle = '#9eb3d1';
  ctx.font = '600 12px system-ui, -apple-system, Segoe UI, sans-serif';
  ctx.fillText(
    "patchdiff-sandbox.pages.dev  ·  github.com/burakemrealp/PatchDiff_Sandbox  ·  PatchDiff Sandbox isn't endorsed by Riot Games",
    width / 2,
    594
  );

  const safeVer = (radar.to_display_version || radar.to_version || 'patch').replace(/[^a-zA-Z0-9._-]/g, '_');
  const link = document.createElement('a');
  link.download = `patchdiff-zero-day-${safeVer}-${localeCode}.png`;
  link.href = canvas.toDataURL('image/png');
  link.click();
}
