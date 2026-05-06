import type { ColumnStats } from '../../lib/types';
import { skewColor } from '../../lib/utils';
import './ColumnTabs.css';

interface Props {
  columns: string[];
  active: string;
  stats: ColumnStats[];
  scores: unknown[];
  onChange: (col: string) => void;
}

export function ColumnTabs({ columns, active, stats, onChange }: Props) {
  return (
    <div className="col-tabs" role="tablist" aria-label="Partition columns">
      {columns.map(col => {
        const s = stats.find(st => st.column === col);
        const color = s ? skewColor(s.skew_ratio) : 'var(--text-muted)';
        return (
          <button
            key={col}
            role="tab"
            aria-selected={active === col}
            className={`col-tab ${active === col ? 'active' : ''}`}
            onClick={() => onChange(col)}
            type="button"
          >
            <span className="tab-indicator" style={{ background: color }} />
            <span className="tab-name mono">{col}</span>
            {s && (
              <span className="tab-skew" style={{ color }}>
                {s.skew_ratio.toFixed(1)}×
              </span>
            )}
          </button>
        );
      })}
    </div>
  );
}
