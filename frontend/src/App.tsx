import { useState } from 'react';
import type { ProfileResponse, ColumnStats } from './lib/types';
import { FileUpload } from './components/upload/FileUpload';
import { PartitionChart } from './components/profiler/PartitionChart';
import { SkewMetrics } from './components/profiler/SkewMetrics';
import { StragglerTimeline } from './components/simulator/StragglerTimeline';
import { PartitionAdvisor } from './components/advisor/PartitionAdvisor';
import { ColumnTabs } from './components/ui/ColumnTabs';
import './styles/tokens.css';
import './App.css';

const API_BASE = 'http://localhost:8000/api';

export default function App() {
  const [result, setResult] = useState<ProfileResponse | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [activeCol, setActiveCol] = useState<string>('');
  const [uploadedFileName, setUploadedFileName] = useState('');

  const handleAnalyze = async (file: File, columns: string, numWorkers: number) => {
    setIsLoading(true);
    setError(null);
    setResult(null);
    setUploadedFileName(file.name);

    const form = new FormData();
    form.append('file', file);
    form.append('partition_columns', columns);
    form.append('num_workers', String(numWorkers));
    form.append('rows_per_sec', '1000000');

    try {
      const res = await fetch(`${API_BASE}/analyze`, {
        method: 'POST',
        body: form,
      });

      if (!res.ok) {
        const body = await res.json().catch(() => ({ detail: res.statusText }));
        throw new Error(body.detail ?? 'Analysis failed');
      }

      const data: ProfileResponse = await res.json();
      setResult(data);
      setActiveCol(data.column_stats[0]?.column ?? '');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setIsLoading(false);
    }
  };

  const activeStats: ColumnStats | undefined = result?.column_stats.find(s => s.column === activeCol);
  const activeScore = result?.scores.find(s => s.column === activeCol);

  return (
    <div className="app">
      <header className="app-header">
        <div className="header-left">
          <div className="logo">
            <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="var(--good)" strokeWidth="1.8" aria-hidden="true">
              <path d="M22 12h-4l-3 9L9 3l-3 9H2" />
            </svg>
            <span className="logo-text">Skew<span className="logo-accent">Probe</span></span>
          </div>
          <div className="header-tagline">Partition health profiler</div>
        </div>
        {result && (
          <div className="header-file mono">
            {uploadedFileName} ·{' '}
            {result.column_stats[0]?.total_rows.toLocaleString()} rows
          </div>
        )}
      </header>

      <main className="app-main">
        {!result ? (
          <div className="landing">
            <div className="landing-hero">
              <h1 className="hero-title">
                Profile your partition keys.<br />
                <span className="hero-accent">Find the skew before Spark does.</span>
              </h1>
              <p className="hero-body">
                Upload a Parquet or CSV file. Skew Probe profiles key distributions
                using Count-Min Sketch and HyperLogLog, simulates straggler impact
                across your worker pool, and generates ready-to-paste salting SQL.
              </p>
            </div>
            <div className="upload-card">
              <FileUpload
                onSubmit={handleAnalyze}
                isLoading={isLoading}
              />
              {error && (
                <div className="error-box" role="alert">
                  <strong>Error:</strong> {error}
                </div>
              )}
            </div>
            <div className="feature-grid">
              <Feature
                icon="⬡"
                title="Count-Min Sketch"
                body="Sub-linear frequency estimation for streaming Arrow batches without materializing full histograms."
              />
              <Feature
                icon="∿"
                title="HyperLogLog"
                body="±0.81% cardinality estimates with b=14 registers — 16 KB vs gigabytes of exact counting."
              />
              <Feature
                icon="⌛"
                title="Straggler Simulator"
                body="Models wall-clock job completion using greedy LPT assignment. Quantifies idle worker time."
              />
              <Feature
                icon="⚡"
                title="Partition Advisor"
                body="Scores by entropy, null rate, and skew. Emits ready-to-paste DuckDB and PySpark salting SQL."
              />
            </div>
          </div>
        ) : (
          <div className="results">
            <div className="results-sidebar">
              <div className="sidebar-section">
                <div className="section-label">Analyze Another File</div>
                <FileUpload
                  onSubmit={handleAnalyze}
                  isLoading={isLoading}
                  schemaColumns={Object.keys(result.schema_info)}
                />
                {error && (
                  <div className="error-box" role="alert">
                    <strong>Error:</strong> {error}
                  </div>
                )}
              </div>
              <div className="sidebar-section">
                <PartitionAdvisor
                  scores={result.scores}
                  hints={result.hints}
                />
              </div>
            </div>

            <div className="results-main">
              {result.column_stats.length > 1 && (
                <ColumnTabs
                  columns={result.column_stats.map(s => s.column)}
                  active={activeCol}
                  stats={result.column_stats}
                  scores={result.scores}
                  onChange={setActiveCol}
                />
              )}

              {activeStats && (
                <>
                  <SkewMetrics stats={activeStats} score={activeScore} />
                  <PartitionChart stats={activeStats} />
                </>
              )}

              {result.simulation && (
                <StragglerTimeline simulation={result.simulation} />
              )}

              <div className="schema-card">
                <div className="schema-title">Schema</div>
                <div className="schema-grid">
                  {Object.entries(result.schema_info).map(([col, type]) => (
                    <div key={col} className="schema-row">
                      <span className="schema-col mono">{col}</span>
                      <span className="schema-type mono">{type}</span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}

function Feature({ icon, title, body }: { icon: string; title: string; body: string }) {
  return (
    <div className="feature-card">
      <div className="feature-icon">{icon}</div>
      <div className="feature-title">{title}</div>
      <div className="feature-body">{body}</div>
    </div>
  );
}
