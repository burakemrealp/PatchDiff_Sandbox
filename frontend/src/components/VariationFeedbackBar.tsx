import { useState } from 'react';
import { CheckCircle2, Loader2, Send, Star, ThumbsDown, ThumbsUp } from 'lucide-react';
import { api } from '../services/api';
import { useLanguage } from '../i18n/LanguageContext';
import type { FullRunePage, MapKey, RoleKey } from '../types/api';

interface VariationFeedbackBarProps {
  patchVersion: string;
  championKey: string;
  role: RoleKey;
  gameMap: MapKey;
  targetProfile: 'squishy' | 'bruiser' | 'tank';
  playstyle: string;
  items: { item_id: string; name: string; buy_order?: number }[];
  runePage?: FullRunePage | null;
  onSubmitted?: () => void;
}

export function VariationFeedbackBar({
  patchVersion,
  championKey,
  role,
  gameMap,
  targetProfile,
  playstyle,
  items,
  runePage,
  onSubmitted,
}: VariationFeedbackBarProps) {
  const { t } = useLanguage();
  const [rating, setRating] = useState<number>(0);
  const [hoverRating, setHoverRating] = useState<number>(0);
  const [isHelpful, setIsHelpful] = useState<boolean>(true);
  const [comment, setComment] = useState<string>('');
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);
  const [submittedRating, setSubmittedRating] = useState<number | null>(null);
  const [submittedHelpful, setSubmittedHelpful] = useState<boolean>(true);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const handleSubmit = async () => {
    const finalRating = rating || (isHelpful ? 4 : 2);
    setIsSubmitting(true);
    setErrorMsg(null);
    try {
      await api.submitFeedback({
        patch_version: patchVersion,
        champion_key: championKey,
        role,
        game_map: gameMap,
        target_profile: targetProfile,
        playstyle,
        items: items.map((i) => ({
          item_id: i.item_id,
          name: i.name,
          buy_order: i.buy_order,
        })),
        rune_page: runePage ?? null,
        rating: finalRating,
        is_helpful: isHelpful,
        comment: comment.trim() || undefined,
      });
      setSubmittedRating(finalRating);
      setSubmittedHelpful(isHelpful);
      onSubmitted?.();
    } catch (err) {
      setErrorMsg(err instanceof Error ? err.message : t.feedbackError);
    } finally {
      setIsSubmitting(false);
    }
  };

  if (submittedRating !== null) {
    return (
      <div className="pt-3 border-t border-slate-800 flex flex-wrap items-center justify-between gap-2 text-xs text-emerald-300">
        <div className="inline-flex items-center gap-1.5">
          <CheckCircle2 className="w-4 h-4 text-emerald-400" />
          <span>
            {t.feedbackSavedPrefix} ({'★'.repeat(submittedRating)} {submittedRating}/5 ·{' '}
            {submittedHelpful ? t.helpfulBtn : t.needsWorkBtn})
          </span>
        </div>
      </div>
    );
  }

  const activeStars = hoverRating || rating;

  return (
    <div className="pt-3 border-t border-slate-800 space-y-2.5">
      <div className="flex flex-wrap items-center justify-between gap-2 text-xs">
        <div className="flex flex-wrap items-center gap-2.5">
          <span className="text-slate-400 font-medium">{t.feedbackPrompt}</span>

          <div className="flex items-center gap-0.5" onMouseLeave={() => setHoverRating(0)}>
            {[1, 2, 3, 4, 5].map((star) => (
              <button
                key={star}
                type="button"
                aria-label={`${star} ${t.starAriaSuffix}`}
                onMouseEnter={() => setHoverRating(star)}
                onClick={() => {
                  setRating(star);
                  setIsHelpful(star >= 3);
                }}
                className="p-0.5 transition cursor-pointer"
              >
                <Star
                  className={`w-4 h-4 ${
                    star <= activeStars
                      ? 'fill-amber-400 text-amber-400'
                      : 'text-slate-600 hover:text-slate-400'
                  }`}
                />
              </button>
            ))}
          </div>

          <div className="flex items-center gap-1.5">
            <button
              type="button"
              onClick={() => {
                setIsHelpful(true);
                if (rating === 0) setRating(5);
              }}
              className={`inline-flex items-center gap-1 px-2 py-1 rounded-md border text-[11px] font-medium transition cursor-pointer ${
                rating > 0 && isHelpful
                  ? 'bg-emerald-500/15 border-emerald-500/40 text-emerald-300'
                  : 'bg-slate-950 border-slate-800 text-slate-400 hover:text-slate-200'
              }`}
            >
              <ThumbsUp className="w-3 h-3" /> {t.helpfulBtn}
            </button>
            <button
              type="button"
              onClick={() => {
                setIsHelpful(false);
                if (rating === 0 || rating >= 4) setRating(2);
              }}
              className={`inline-flex items-center gap-1 px-2 py-1 rounded-md border text-[11px] font-medium transition cursor-pointer ${
                rating > 0 && !isHelpful
                  ? 'bg-rose-500/15 border-rose-500/40 text-rose-300'
                  : 'bg-slate-950 border-slate-800 text-slate-400 hover:text-slate-200'
              }`}
            >
              <ThumbsDown className="w-3 h-3" /> {t.needsWorkBtn}
            </button>
          </div>
        </div>
      </div>

      {rating > 0 && (
        <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-2">
          <input
            type="text"
            value={comment}
            onChange={(e) => setComment(e.target.value)}
            maxLength={500}
            placeholder={t.commentPlaceholder}
            className="flex-1 px-3 py-1.5 text-xs rounded-lg bg-slate-950 border border-slate-800 text-slate-200 placeholder-slate-500 focus:outline-none focus:border-purple-500"
          />
          <button
            type="button"
            onClick={handleSubmit}
            disabled={isSubmitting}
            className="inline-flex items-center justify-center gap-1.5 px-3.5 py-1.5 rounded-lg text-xs font-semibold bg-purple-500 hover:bg-purple-400 disabled:opacity-50 text-slate-950 transition cursor-pointer shrink-0"
          >
            {isSubmitting ? (
              <Loader2 className="w-3.5 h-3.5 animate-spin" />
            ) : (
              <Send className="w-3.5 h-3.5" />
            )}
            {t.submitBtn} ({rating}/5)
          </button>
        </div>
      )}

      {errorMsg && <p className="text-[11px] text-rose-400">{errorMsg}</p>}
    </div>
  );
}
