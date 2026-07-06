// date: 2026-07-06
// dev: Claude Code (glm-5.2)
// changelog: 新建 PurpleTeamPanel——紫队对抗校验面板（critique + review + 时间线回放）

import { useCallback, useState } from "react";
import { useAppStore } from "@/lib/store";
import { cyberApi } from "@/services/api/cyber";

/**
 * 紫队校验面板。
 *
 * 调用 purple-review 端点，展示 critic 对红队攻击链的对抗性校验
 * 和 reviewer 对跨产出一致性的审查结果。支持步进式时间线回放
 * （逐步显示攻击链步骤）。
 */
export function PurpleTeamPanel() {
  const redAttackResult = useAppStore((s) => s.redAttackResult);
  const blueDefenseResult = useAppStore((s) => s.blueDefenseResult);
  const purpleReviewResult = useAppStore((s) => s.purpleReviewResult);
  const cyberLoading = useAppStore((s) => s.cyberLoading);
  const setPurpleReviewResult = useAppStore((s) => s.setPurpleReviewResult);
  const setCyberLoading = useAppStore((s) => s.setCyberLoading);
  const setCyberError = useAppStore((s) => s.setCyberError);

  const [timelineStep, setTimelineStep] = useState(0);
  const [isPlaying, setIsPlaying] = useState(false);

  const handleReview = useCallback(async () => {
    const chain = redAttackResult?.chain;
    const plan = blueDefenseResult?.plan;
    const alerts = blueDefenseResult?.alerts ?? [];

    if (!chain || !plan) {
      setCyberError("Execute red attack and blue defense first.");
      return;
    }

    setCyberLoading(true);
    setCyberError(null);
    try {
      const result = await cyberApi.purpleReview({
        attack_chain: chain,
        response_plan: plan,
        alerts: alerts as Record<string, any>[],
      });
      setPurpleReviewResult(result);
      setTimelineStep(0);
      setIsPlaying(false);
    } catch (err) {
      setCyberError(err instanceof Error ? err.message : "Purple review failed");
    } finally {
      setCyberLoading(false);
    }
  }, [redAttackResult, blueDefenseResult, setPurpleReviewResult, setCyberLoading, setCyberError]);

  // Timeline replay
  const chainSteps: any[] = redAttackResult?.chain?.steps ?? [];
  const visibleSteps = chainSteps.slice(0, timelineStep + 1);

  const handlePlay = () => {
    if (isPlaying) {
      setIsPlaying(false);
      return;
    }
    setIsPlaying(true);
    setTimelineStep(0);
    const interval = setInterval(() => {
      setTimelineStep((prev) => {
        if (prev >= chainSteps.length - 1) {
          clearInterval(interval);
          setIsPlaying(false);
          return prev;
        }
        return prev + 1;
      });
    }, 800);
  };

  if (!purpleReviewResult) {
    return (
      <div className="cyber-panel cyber-panel--empty">
        <p className="cyber-panel__hint">
          No purple review yet. Execute red attack and blue defense first, then
          click <strong>Run Purple Review</strong> for adversarial validation.
        </p>
        <button
          className="cyber-view__btn cyber-view__btn--primary"
          onClick={() => void handleReview()}
          disabled={cyberLoading || !redAttackResult || !blueDefenseResult}
        >
          {cyberLoading ? "Executing…" : "Run Purple Review"}
        </button>
        {(!redAttackResult || !blueDefenseResult) && (
          <p className="cyber-panel__warn">
            ⚠ Requires both red attack and blue defense results.
          </p>
        )}
      </div>
    );
  }

  const { critique, review } = purpleReviewResult;
  const critiqueIssues: string[] = critique?.issues ?? [];
  const reviewFindings: string[] = review?.findings ?? [];

  return (
    <div className="cyber-panel">
      {/* Action bar */}
      <div className="cyber-panel__actions">
        <button
          className="cyber-view__btn cyber-view__btn--primary"
          onClick={() => void handleReview()}
          disabled={cyberLoading}
        >
          {cyberLoading ? "Executing…" : "Re-run Purple Review"}
        </button>
      </div>

      {/* Critique + Review summary */}
      <div className="cyber-panel__grid">
        {/* Critique */}
        <div className="cyber-panel__section">
          <h4 className="cyber-panel__subtitle">Critique (Attack Chain)</h4>
          <div className="cyber-verdict">
            <span className={`cyber-verdict__status ${critique?.valid ? "cyber-verdict__status--ok" : "cyber-verdict__status--fail"}`}>
              {critique?.valid ? "✓ Valid" : "✗ Invalid"}
            </span>
            {critique?.severity ? (
              <span className={`badge badge--${critique.severity === "none" ? "idle" : "danger"}`}>
                {critique.severity}
              </span>
            ) : null}
          </div>
          {critique?.suggestion ? (
            <p className="cyber-panel__text">{critique.suggestion}</p>
          ) : null}
          {critiqueIssues.length > 0 ? (
            <ul className="cyber-issue-list">
              {critiqueIssues.map((issue, i) => (
                <li key={i} className="cyber-issue">
                  <span className="cyber-issue__icon">!</span>
                  <span>{issue}</span>
                </li>
              ))}
            </ul>
          ) : (
            <p className="cyber-panel__empty">No issues found.</p>
          )}
        </div>

        {/* Review */}
        <div className="cyber-panel__section">
          <h4 className="cyber-panel__subtitle">Review (Consistency)</h4>
          <div className="cyber-verdict">
            <span className={`cyber-verdict__status ${review?.consistent ? "cyber-verdict__status--ok" : "cyber-verdict__status--fail"}`}>
              {review?.consistent ? "✓ Consistent" : "✗ Inconsistent"}
            </span>
          </div>
          {review?.overall_assessment ? (
            <p className="cyber-panel__text">{review.overall_assessment}</p>
          ) : null}
          {reviewFindings.length > 0 ? (
            <ul className="cyber-issue-list">
              {reviewFindings.map((finding, i) => (
                <li key={i} className="cyber-issue cyber-issue--review">
                  <span className="cyber-issue__icon">i</span>
                  <span>{finding}</span>
                </li>
              ))}
            </ul>
          ) : (
            <p className="cyber-panel__empty">No consistency findings.</p>
          )}
        </div>
      </div>

      {/* Timeline replay */}
      {chainSteps.length > 0 ? (
        <div className="cyber-panel__section">
          <h4 className="cyber-panel__subtitle">
            Attack Chain Replay
            <div className="cyber-timeline__controls">
              <button
                className="cyber-view__btn cyber-view__btn--small"
                onClick={handlePlay}
                disabled={chainSteps.length === 0}
              >
                {isPlaying ? "⏸ Pause" : "▶ Play"}
              </button>
              <button
                className="cyber-view__btn cyber-view__btn--small"
                onClick={() => setTimelineStep(Math.max(0, timelineStep - 1))}
                disabled={timelineStep === 0}
              >
                ◀ Step
              </button>
              <button
                className="cyber-view__btn cyber-view__btn--small"
                onClick={() => setTimelineStep(Math.min(chainSteps.length - 1, timelineStep + 1))}
                disabled={timelineStep >= chainSteps.length - 1}
              >
                Step ▶
              </button>
              <span className="cyber-timeline__progress">
                {timelineStep + 1} / {chainSteps.length}
              </span>
            </div>
          </h4>
          <ul className="cyber-timeline">
            {visibleSteps.map((step: any, i: number) => (
              <li key={step.step_id ?? i} className="cyber-timeline__item">
                <span className="cyber-timeline__num">{i + 1}</span>
                <div className="cyber-timeline__body">
                  <span className="cyber-timeline__technique">{step.technique}</span>
                  <span className="cyber-timeline__path">
                    {step.from_asset} → {step.to_asset}
                  </span>
                  <span className={`cyber-timeline__status ${step.success ? "cyber-timeline__status--ok" : ""}`}>
                    {step.success ? "✓ success" : "○ planned"}
                  </span>
                </div>
              </li>
            ))}
          </ul>
        </div>
      ) : null}
    </div>
  );
}
