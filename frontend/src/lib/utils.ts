import type { Severity } from './types';

export function formatNumber(n: number): string {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1_000) return `${(n / 1_000).toFixed(1)}K`;
  return n.toLocaleString();
}

export function formatDuration(sec: number): string {
  if (sec < 0.001) return `${(sec * 1000).toFixed(2)}ms`;
  if (sec < 60) return `${sec.toFixed(2)}s`;
  const m = Math.floor(sec / 60);
  const s = (sec % 60).toFixed(0);
  return `${m}m ${s}s`;
}

export function formatPercent(fraction: number): string {
  return `${(fraction * 100).toFixed(1)}%`;
}

export function severityColor(severity: Severity): string {
  const map: Record<Severity, string> = {
    good: 'var(--good)',
    info: 'var(--info)',
    warning: 'var(--warning)',
    danger: 'var(--danger)',
    critical: 'var(--critical)',
  };
  return map[severity];
}

export function severityDim(severity: Severity): string {
  const map: Record<Severity, string> = {
    good: 'var(--good-dim)',
    info: 'var(--info-dim)',
    warning: 'var(--warning-dim)',
    danger: 'var(--danger-dim)',
    critical: 'var(--critical-dim)',
  };
  return map[severity];
}

export function skewColor(skewRatio: number): string {
  if (skewRatio <= 1.5) return 'var(--good)';
  if (skewRatio <= 3) return 'var(--info)';
  if (skewRatio <= 8) return 'var(--warning)';
  if (skewRatio <= 20) return 'var(--danger)';
  return 'var(--critical)';
}

export function skewLabel(ratio: number): string {
  if (ratio <= 1.5) return 'Healthy';
  if (ratio <= 3) return 'Mild Skew';
  if (ratio <= 8) return 'Moderate Skew';
  if (ratio <= 20) return 'High Skew';
  return 'Severe Skew';
}

export function barColor(index: number, total: number): string {
  const t = index / Math.max(total - 1, 1);
  const colors = [
    '#00d4aa', '#4dc9a3', '#7aba78', '#a8aa4e',
    '#d09830', '#e87025', '#f04b1a', '#e53e3e',
  ];
  const i = Math.min(Math.floor(t * (colors.length - 1)), colors.length - 1);
  return colors[i];
}
