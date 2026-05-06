import type { ColumnStats, ColumnScore } from '../../lib/types';
import { formatNumber, formatPercent, skewColor, skewLabel, severityColor, severityDim } from '../../lib/utils';
import './SkewMetrics.css';

interface SkewMetricsProps {
  stats: ColumnStats;
  score: ColumnScore | undefined;
}

export function SkewMetrics({ stats, score }: SkewMetricsProps) {
  const skewCol = skewColor(stats.skew_ratio);
  const skewLbl = skewLabel(stats.skew_ratio);

  return (
    <div className="metrics-grid">
      <MetricTile
        label="Skew Ratio"
        value={`${stats.skew_ratio.toFixed(1)}×`}
        sub={skewLbl}
        color={skewCol}
        title="Max partition count / mean partition count"
      />
      <MetricTile
        label="Cardinality"
        value={formatNumber(stats.cardinality_estimate)}
        sub={`±${(stats.hll_error * 100).toFixed(1)}% HLL error`}
        color="var(--info)"
        title="Estimated distinct key count (HyperLogLog)"
      />
      <MetricTile
        label="Total Rows"
        value={formatNumber(stats.total_rows)}
        sub={`${stats.batch_count} batch${stats.batch_count !== 1 ? 'es' : ''}`}
        color="var(--text-secondary)"
      />
      <MetricTile
        label="Null Rate"
        value={formatPercent(stats.null_fraction)}
        sub={`${formatNumber(stats.null_count)} nulls`}
        color={stats.null_fraction > 0.1 ? 'var(--warning)' : 'var(--text-secondary)'}
      />
      {score && (
        <div
          className="metric-tile score-tile"
          style={{
            borderColor: severityColor(score.severity),
            background: severityDim(score.severity),
          }}
        >
          <div className="metric-label">Advisor Score</div>
          <div
            className="metric-value"
            style={{ color: severityColor(score.severity) }}
          >
            {score.composite_score.toFixed(0)}
            <span className="metric-max">/100</span>
          </div>
          <div className="metric-sub">{score.recommendation}</div>
        </div>
      )}
    </div>
  );
}

interface TileProps {
  label: string;
  value: string;
  sub: string;
  color: string;
  title?: string;
}

function MetricTile({ label, value, sub, color, title }: TileProps) {
  return (
    <div className="metric-tile" title={title}>
      <div className="metric-label">{label}</div>
      <div className="metric-value mono" style={{ color }}>{value}</div>
      <div className="metric-sub">{sub}</div>
    </div>
  );
}
