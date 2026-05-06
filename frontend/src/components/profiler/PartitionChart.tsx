import { useEffect, useRef } from 'react';
import * as d3 from 'd3';
import type { ColumnStats } from '../../lib/types';
import { formatNumber, barColor } from '../../lib/utils';
import './PartitionChart.css';

interface PartitionChartProps {
  stats: ColumnStats;
}

export function PartitionChart({ stats }: PartitionChartProps) {
  const svgRef = useRef<SVGSVGElement>(null);

  useEffect(() => {
    if (!svgRef.current || !stats.top_keys.length) return;

    const el = svgRef.current;
    const margin = { top: 8, right: 16, bottom: 56, left: 64 };
    const totalWidth = el.clientWidth || 600;
    const height = 200;
    const width = totalWidth - margin.left - margin.right;
    const innerHeight = height - margin.top - margin.bottom;

    d3.select(el).selectAll('*').remove();

    const svg = d3
      .select(el)
      .attr('height', height)
      .append('g')
      .attr('transform', `translate(${margin.left},${margin.top})`);

    const data = stats.top_keys.slice(0, 20);
    const maxCount = d3.max(data, d => d.count) ?? 1;

    const x = d3
      .scaleBand()
      .domain(data.map(d => d.key))
      .range([0, width])
      .padding(0.18);

    const y = d3
      .scaleLinear()
      .domain([0, maxCount * 1.08])
      .range([innerHeight, 0]);

    // Mean line
    const mean = data.reduce((s, d) => s + d.count, 0) / data.length;
    svg
      .append('line')
      .attr('class', 'mean-line')
      .attr('x1', 0)
      .attr('x2', width)
      .attr('y1', y(mean))
      .attr('y2', y(mean));

    svg
      .append('text')
      .attr('class', 'mean-label')
      .attr('x', width + 4)
      .attr('y', y(mean) + 4)
      .text('mean');

    // Bars
    svg
      .selectAll('.bar')
      .data(data)
      .join('rect')
      .attr('class', 'bar')
      .attr('x', d => x(d.key) ?? 0)
      .attr('y', innerHeight)
      .attr('width', x.bandwidth())
      .attr('height', 0)
      .attr('rx', 2)
      .attr('fill', (_, i) => barColor(i, data.length))
      .transition()
      .duration(500)
      .ease(d3.easeCubicOut)
      .attr('y', d => y(d.count))
      .attr('height', d => innerHeight - y(d.count));

    // Tooltip rects (invisible, for hover)
    svg
      .selectAll('.bar-hit')
      .data(data)
      .join('rect')
      .attr('class', 'bar-hit')
      .attr('x', d => x(d.key) ?? 0)
      .attr('y', 0)
      .attr('width', x.bandwidth())
      .attr('height', innerHeight)
      .attr('fill', 'transparent')
      .on('mouseenter', function (event, d) {
        const tooltip = document.getElementById('chart-tooltip');
        if (!tooltip) return;
        tooltip.style.opacity = '1';
        tooltip.style.left = `${event.pageX + 12}px`;
        tooltip.style.top = `${event.pageY - 28}px`;
        tooltip.innerHTML = `<span class="tt-key">${d.key}</span><br/>${formatNumber(d.count)} rows`;
      })
      .on('mousemove', function (event) {
        const tooltip = document.getElementById('chart-tooltip');
        if (!tooltip) return;
        tooltip.style.left = `${event.pageX + 12}px`;
        tooltip.style.top = `${event.pageY - 28}px`;
      })
      .on('mouseleave', () => {
        const tooltip = document.getElementById('chart-tooltip');
        if (tooltip) tooltip.style.opacity = '0';
      });

    // Y axis
    svg
      .append('g')
      .attr('class', 'axis y-axis')
      .call(
        d3
          .axisLeft(y)
          .ticks(4)
          .tickFormat(d => formatNumber(d as number))
      );

    // X axis — only show first, middle, last labels if many bars
    const xAxis = d3.axisBottom(x).tickSize(0);
    if (data.length > 8) {
      xAxis.tickValues(
        data
          .filter((_, i) => i === 0 || i === Math.floor(data.length / 2) || i === data.length - 1)
          .map(d => d.key)
      );
    }

    svg
      .append('g')
      .attr('class', 'axis x-axis')
      .attr('transform', `translate(0,${innerHeight})`)
      .call(xAxis)
      .selectAll('text')
      .attr('y', 10)
      .style('text-anchor', 'end')
      .attr('dx', '-0.4em')
      .attr('dy', '0.4em')
      .attr('transform', 'rotate(-35)');
  }, [stats]);

  return (
    <div className="partition-chart-wrap">
      <div className="chart-title">
        Top Key Distribution
        <span className="chart-subtitle mono">top {Math.min(stats.top_keys.length, 20)} of {formatNumber(stats.cardinality_estimate)} keys</span>
      </div>
      <svg ref={svgRef} className="partition-svg" />
      <div id="chart-tooltip" className="chart-tooltip" />
    </div>
  );
}
