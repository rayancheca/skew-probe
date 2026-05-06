import { useState } from 'react';
import type { ColumnScore, PartitionHints } from '../../lib/types';
import { severityColor, severityDim } from '../../lib/utils';
import './PartitionAdvisor.css';

interface Props {
  scores: ColumnScore[];
  hints: PartitionHints[];
}

type Engine = 'duckdb' | 'pyspark';
type HintType = 'repartition' | 'salting';

export function PartitionAdvisor({ scores, hints }: Props) {
  const [activeCol, setActiveCol] = useState<string>(scores[0]?.column ?? '');
  const [engine, setEngine] = useState<Engine>('duckdb');
  const [hintType, setHintType] = useState<HintType>('salting');
  const [copied, setCopied] = useState(false);

  const activeScore = scores.find(s => s.column === activeCol);
  const activeHints = hints.find(h => h.column === activeCol);

  const codeSnippet = activeHints
    ? engine === 'duckdb'
      ? hintType === 'repartition'
        ? activeHints.duckdb_repartition
        : activeHints.duckdb_salting
      : hintType === 'repartition'
        ? activeHints.pyspark_repartition
        : activeHints.pyspark_salting
    : '';

  const copyCode = async () => {
    await navigator.clipboard.writeText(codeSnippet);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="advisor-wrap">
      <div className="advisor-header">
        <h2 className="advisor-title">Partition Advisor</h2>
      </div>

      <div className="score-list" role="list">
        {scores.map(score => (
          <button
            key={score.column}
            className={`score-row ${activeCol === score.column ? 'active' : ''}`}
            onClick={() => setActiveCol(score.column)}
            type="button"
            role="listitem"
          >
            <div className="score-col-name mono">{score.column}</div>
            <div className="score-bar-wrap">
              <div
                className="score-bar-fill"
                style={{
                  width: `${score.composite_score}%`,
                  background: severityColor(score.severity),
                }}
              />
            </div>
            <div
              className="score-num mono"
              style={{ color: severityColor(score.severity) }}
            >
              {score.composite_score.toFixed(0)}
            </div>
            <div
              className="severity-badge"
              style={{
                color: severityColor(score.severity),
                background: severityDim(score.severity),
              }}
            >
              {score.severity}
            </div>
          </button>
        ))}
      </div>

      {activeScore && activeHints && (
        <div className="hints-panel">
          <div
            className="explanation-box"
            style={{ borderColor: severityColor(activeScore.severity) }}
          >
            <span
              className="explain-icon"
              style={{ color: severityColor(activeScore.severity) }}
            >
              ↳
            </span>
            {activeHints.explanation}
          </div>

          <div className="hint-controls">
            <div className="toggle-group" role="group" aria-label="Engine">
              {(['duckdb', 'pyspark'] as Engine[]).map(e => (
                <button
                  key={e}
                  className={`toggle-btn ${engine === e ? 'active' : ''}`}
                  onClick={() => setEngine(e)}
                  type="button"
                >
                  {e === 'duckdb' ? 'DuckDB' : 'PySpark'}
                </button>
              ))}
            </div>
            <div className="toggle-group" role="group" aria-label="Hint type">
              {(['salting', 'repartition'] as HintType[]).map(h => (
                <button
                  key={h}
                  className={`toggle-btn ${hintType === h ? 'active' : ''}`}
                  onClick={() => setHintType(h)}
                  type="button"
                >
                  {h.charAt(0).toUpperCase() + h.slice(1)}
                </button>
              ))}
            </div>
          </div>

          <div className="code-block-wrap">
            <button className="copy-btn" onClick={copyCode} type="button">
              {copied ? '✓ Copied' : 'Copy'}
            </button>
            <pre className="code-block"><code>{codeSnippet}</code></pre>
          </div>

          <div className="score-breakdown">
            <ScoreBar label="Entropy" value={activeScore.entropy_score} max={100} color="var(--info)" />
            <ScoreBar label="Null Penalty" value={activeScore.null_penalty} max={100} color="var(--warning)" invert />
            <ScoreBar label="Skew Penalty" value={activeScore.skew_penalty} max={100} color="var(--danger)" invert />
          </div>
        </div>
      )}
    </div>
  );
}

function ScoreBar({
  label,
  value,
  max,
  color,
  invert = false,
}: {
  label: string;
  value: number;
  max: number;
  color: string;
  invert?: boolean;
}) {
  const pct = (value / max) * 100;
  return (
    <div className="score-breakdown-row">
      <div className="breakdown-label">{label}</div>
      <div className="breakdown-bar-bg">
        <div
          className="breakdown-bar-fill"
          style={{ width: `${pct}%`, background: color }}
        />
      </div>
      <div
        className="breakdown-val mono"
        style={{ color: invert && value > 30 ? color : 'var(--text-secondary)' }}
      >
        {value.toFixed(0)}
      </div>
    </div>
  );
}
