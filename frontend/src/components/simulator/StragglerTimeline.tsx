import { useEffect, useRef } from 'react';
import * as d3 from 'd3';
import type { SimulationResult } from '../../lib/types';
import { formatNumber, formatDuration, formatPercent } from '../../lib/utils';
import './StragglerTimeline.css';

interface Props {
  simulation: SimulationResult;
}

export function StragglerTimeline({ simulation }: Props) {
  const svgRef = useRef<SVGSVGElement>(null);

  useEffect(() => {
    if (!svgRef.current) return;
    drawTimeline(svgRef.current, simulation);
  }, [simulation]);

  return (
    <div className="timeline-wrap">
      <div className="timeline-header">
        <div>
          <div className="timeline-title">Straggler Simulation</div>
          <div className="timeline-sub">
            {simulation.num_workers} workers · {formatNumber(simulation.total_rows)} rows
          </div>
        </div>
        <div className="timeline-stats">
          <Stat label="Ideal" value={formatDuration(simulation.ideal_finish_sec)} color="var(--good)" />
          <Stat label="Actual" value={formatDuration(simulation.actual_finish_sec)} color="var(--danger)" />
          <Stat label="Slowdown" value={`${simulation.slowdown_factor.toFixed(2)}×`} color="var(--warning)" />
          <Stat label="Idle" value={formatPercent(simulation.idle_fraction)} color="var(--text-secondary)" />
        </div>
      </div>
      <svg ref={svgRef} className="timeline-svg" />
    </div>
  );
}

function Stat({ label, value, color }: { label: string; value: string; color: string }) {
  return (
    <div className="timeline-stat">
      <div className="stat-label">{label}</div>
      <div className="stat-value mono" style={{ color }}>{value}</div>
    </div>
  );
}

function drawTimeline(el: SVGSVGElement, sim: SimulationResult) {
  d3.select(el).selectAll('*').remove();

  const margin = { top: 12, right: 16, bottom: 30, left: 56 };
  const totalWidth = el.clientWidth || 600;
  const barH = Math.max(14, Math.min(24, 300 / sim.num_workers));
  const gap = 4;
  const innerH = sim.num_workers * (barH + gap);
  const height = innerH + margin.top + margin.bottom;
  const width = totalWidth - margin.left - margin.right;

  d3.select(el).attr('height', height);

  const svg = d3
    .select(el)
    .append('g')
    .attr('transform', `translate(${margin.left},${margin.top})`);

  const maxTime = sim.actual_finish_sec;
  const x = d3.scaleLinear().domain([0, maxTime * 1.05]).range([0, width]);

  // Ideal finish line
  svg
    .append('line')
    .attr('class', 'ideal-line')
    .attr('x1', x(sim.ideal_finish_sec))
    .attr('x2', x(sim.ideal_finish_sec))
    .attr('y1', 0)
    .attr('y2', innerH);

  svg
    .append('text')
    .attr('class', 'ideal-label')
    .attr('x', x(sim.ideal_finish_sec) + 4)
    .attr('y', 10)
    .text('ideal');

  // Actual finish line
  svg
    .append('line')
    .attr('class', 'actual-line')
    .attr('x1', x(sim.actual_finish_sec))
    .attr('x2', x(sim.actual_finish_sec))
    .attr('y1', 0)
    .attr('y2', innerH);

  svg
    .append('text')
    .attr('class', 'actual-label')
    .attr('x', x(sim.actual_finish_sec) + 4)
    .attr('y', 10)
    .text('straggler');

  // Worker bars
  sim.worker_timelines.forEach((worker, i) => {
    const y = i * (barH + gap);
    const barColor = worker.is_straggler ? 'var(--danger)' : 'var(--info)';
    const barWidth = Math.max(2, x(worker.finish_time_sec));

    // Background track
    svg
      .append('rect')
      .attr('x', 0)
      .attr('y', y)
      .attr('width', width)
      .attr('height', barH)
      .attr('rx', 2)
      .attr('fill', 'var(--surface-elevated)');

    // Worker bar (animated)
    svg
      .append('rect')
      .attr('x', 0)
      .attr('y', y)
      .attr('width', 0)
      .attr('height', barH)
      .attr('rx', 2)
      .attr('fill', barColor)
      .attr('opacity', worker.is_straggler ? 1 : 0.6)
      .transition()
      .duration(600)
      .delay(i * 30)
      .ease(d3.easeCubicOut)
      .attr('width', barWidth);

    // Idle overlay (space between worker finish and straggler finish)
    if (!worker.is_straggler && sim.actual_finish_sec > worker.finish_time_sec) {
      svg
        .append('rect')
        .attr('x', x(worker.finish_time_sec))
        .attr('y', y)
        .attr('width', x(sim.actual_finish_sec) - x(worker.finish_time_sec))
        .attr('height', barH)
        .attr('rx', 0)
        .attr('fill', 'rgba(255,107,53,0.12)')
        .attr('stroke', 'var(--danger)')
        .attr('stroke-width', 0.5)
        .attr('stroke-dasharray', '2 3');
    }

    // Worker label
    svg
      .append('text')
      .attr('x', -6)
      .attr('y', y + barH / 2 + 4)
      .attr('text-anchor', 'end')
      .attr('class', 'worker-label')
      .attr('fill', worker.is_straggler ? 'var(--danger)' : 'var(--text-muted)')
      .text(`W${worker.worker_id}`);
  });

  // X axis
  svg
    .append('g')
    .attr('class', 'axis x-axis')
    .attr('transform', `translate(0,${innerH})`)
    .call(
      d3
        .axisBottom(x)
        .ticks(5)
        .tickFormat(d => formatDuration(d as number))
    );
}
