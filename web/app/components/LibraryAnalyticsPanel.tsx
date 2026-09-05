"use client";

import { useEffect, useMemo, useRef } from "react";
import { BarChart, LineChart, PieChart } from "echarts/charts";
import {
  GridComponent,
  LegendComponent,
  TitleComponent,
  TooltipComponent
} from "echarts/components";
import * as echarts from "echarts/core";
import { LabelLayout } from "echarts/features";
import { SVGRenderer } from "echarts/renderers";
import type { EChartsOption } from "echarts";
import type {
  LibraryAnalytics,
  LibraryAnalyticsDimension,
  LibraryAnalyticsScoreBucket,
  LibraryAnalyticsTrendPoint
} from "../../lib/types";

echarts.use([
  BarChart,
  LineChart,
  PieChart,
  GridComponent,
  LegendComponent,
  TitleComponent,
  TooltipComponent,
  LabelLayout,
  SVGRenderer
]);

type LibraryAnalyticsPanelProps = {
  analytics: LibraryAnalytics | null;
  loading: boolean;
  collapsed: boolean;
  windowDays: string;
  onWindowChange: (value: string) => void;
  onToggleCollapsed: () => void;
  onSourceTypeSelect: (value: string) => void;
  onCategorySelect: (value: string) => void;
  onScoreBucketSelect: (bucket: LibraryAnalyticsScoreBucket) => void;
};

type ChartDatum = {
  key: string;
  name: string;
  value: number;
};

type ScoreChartDatum = ChartDatum & {
  bucket: LibraryAnalyticsScoreBucket;
};

type ChartClickParams = {
  data?: unknown;
};

const windowOptions = [
  { value: "7", label: "最近 7 天" },
  { value: "30", label: "最近 30 天" },
  { value: "0", label: "全部" }
];

const chartPalette = ["#176b5b", "#2f8f83", "#70b7a6", "#f59e0b", "#475467", "#8b5cf6", "#0ea5e9"];

export function LibraryAnalyticsPanel({
  analytics,
  loading,
  collapsed,
  windowDays,
  onWindowChange,
  onToggleCollapsed,
  onSourceTypeSelect,
  onCategorySelect,
  onScoreBucketSelect
}: LibraryAnalyticsPanelProps) {
  const totals = analytics?.totals;

  return (
    <section className="analyticsPanel">
      <div className="analyticsHeader">
        <div>
          <h2>数据概览</h2>
          <p className="mutedText">跟随当前检索条件动态统计，新增来源后会自动进入图表。</p>
        </div>
        <div className="analyticsControls">
          <select value={windowDays} onChange={(event) => onWindowChange(event.target.value)}>
            {windowOptions.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
          <button className="ghostButton" type="button" onClick={onToggleCollapsed}>
            {collapsed ? "展开" : "收起"}
          </button>
        </div>
      </div>

      {collapsed ? null : (
        <>
          <div className="analyticsMetricGrid">
            <MetricCard label="入库总数" value={formatInteger(totals?.item_count)} loading={loading} />
            <MetricCard
              label="已摘要"
              value={
                totals
                  ? `${formatInteger(totals.summarized_count)} / ${formatPercent(totals.summary_rate)}`
                  : "-"
              }
              loading={loading}
            />
            <MetricCard label="来源数" value={formatInteger(totals?.source_count)} loading={loading} />
            <MetricCard label="平均分" value={formatNumber(totals?.average_score)} loading={loading} />
          </div>

          <div className="analyticsChartGrid">
            <TrendChart title="最近入库趋势" points={analytics?.trend ?? []} loading={loading} />
            <DonutChart
              title="来源类型分布"
              items={analytics?.source_types ?? []}
              loading={loading}
              emptyText="暂无来源类型数据"
              onSelect={onSourceTypeSelect}
            />
            <HorizontalBarChart
              title="分类分布"
              items={analytics?.categories ?? []}
              loading={loading}
              emptyText="暂无分类数据"
              onSelect={onCategorySelect}
            />
            <ScoreBucketChart
              title="分数分布"
              buckets={analytics?.score_buckets ?? []}
              loading={loading}
              onSelect={onScoreBucketSelect}
            />
            <HorizontalBarChart
              title="具体来源 Top 12"
              items={analytics?.sources ?? []}
              loading={loading}
              emptyText="暂无来源数据"
            />
          </div>
        </>
      )}
    </section>
  );
}

function MetricCard({ label, value, loading }: { label: string; value: string; loading: boolean }) {
  return (
    <div className="analyticsMetric">
      <span>{label}</span>
      <strong>{loading ? "统计中" : value}</strong>
    </div>
  );
}

function TrendChart({
  title,
  points,
  loading
}: {
  title: string;
  points: LibraryAnalyticsTrendPoint[];
  loading: boolean;
}) {
  const option = useMemo<EChartsOption>(() => {
    const labels = points.map((point) => formatShortDate(point.date));
    const values = points.map((point) => point.count);

    return {
      color: chartPalette,
      tooltip: {
        trigger: "axis",
        backgroundColor: "rgba(23, 32, 42, 0.92)",
        borderWidth: 0,
        textStyle: { color: "#fff" }
      },
      grid: { left: 40, right: 16, top: 28, bottom: 34 },
      xAxis: {
        type: "category",
        data: labels,
        axisLine: { lineStyle: { color: "#d9dee7" } },
        axisTick: { show: false },
        axisLabel: { color: "#667085", fontSize: 11 }
      },
      yAxis: {
        type: "value",
        splitLine: { lineStyle: { color: "#eef1f5" } },
        axisLabel: { color: "#667085", fontSize: 11 }
      },
      series: [
        {
          name: "入库",
          type: "bar",
          barWidth: "44%",
          data: values,
          itemStyle: {
            borderRadius: [5, 5, 0, 0],
            color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
              { offset: 0, color: "#1f8f7a" },
              { offset: 1, color: "#a7dccf" }
            ])
          }
        },
        {
          name: "趋势",
          type: "line",
          data: values,
          smooth: true,
          symbolSize: 7,
          lineStyle: { width: 3, color: "#f59e0b" },
          itemStyle: { color: "#f59e0b" },
          areaStyle: {
            color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
              { offset: 0, color: "rgba(245, 158, 11, 0.18)" },
              { offset: 1, color: "rgba(245, 158, 11, 0.02)" }
            ])
          }
        }
      ]
    };
  }, [points]);

  return (
    <EChartCard
      title={title}
      meta={points.length ? `${points.length} 天` : ""}
      option={option}
      loading={loading}
      isEmpty={points.length === 0}
      emptyText="暂无入库趋势数据"
      className="trendCard"
    />
  );
}

function DonutChart({
  title,
  items,
  loading,
  emptyText,
  onSelect
}: {
  title: string;
  items: LibraryAnalyticsDimension[];
  loading: boolean;
  emptyText: string;
  onSelect?: (value: string) => void;
}) {
  const data = useMemo(() => dimensionData(items), [items]);
  const option = useMemo<EChartsOption>(
    () => ({
      color: chartPalette,
      tooltip: {
        trigger: "item",
        formatter: "{b}<br/>{c} 条 ({d}%)",
        backgroundColor: "rgba(23, 32, 42, 0.92)",
        borderWidth: 0,
        textStyle: { color: "#fff" }
      },
      legend: {
        bottom: 0,
        type: "scroll",
        icon: "circle",
        textStyle: { color: "#667085", fontSize: 11 }
      },
      series: [
        {
          name: title,
          type: "pie",
          radius: ["46%", "72%"],
          center: ["50%", "43%"],
          avoidLabelOverlap: true,
          data,
          label: {
            formatter: "{b}\n{c}",
            color: "#344054",
            fontSize: 11
          },
          labelLine: { length: 8, length2: 6 },
          itemStyle: {
            borderColor: "#fff",
            borderWidth: 2
          },
          emphasis: {
            scale: true,
            scaleSize: 8,
            itemStyle: {
              shadowBlur: 18,
              shadowColor: "rgba(16, 24, 40, 0.18)"
            }
          }
        }
      ]
    }),
    [data, title]
  );

  return (
    <EChartCard
      title={title}
      meta={items.length ? `${items.length} 项` : ""}
      option={option}
      loading={loading}
      isEmpty={items.length === 0}
      emptyText={emptyText}
      onSelect={onSelect}
    />
  );
}

function HorizontalBarChart({
  title,
  items,
  loading,
  emptyText,
  onSelect
}: {
  title: string;
  items: LibraryAnalyticsDimension[];
  loading: boolean;
  emptyText: string;
  onSelect?: (value: string) => void;
}) {
  const data = useMemo(() => dimensionData(items).reverse(), [items]);
  const option = useMemo<EChartsOption>(
    () => ({
      color: chartPalette,
      tooltip: {
        trigger: "axis",
        axisPointer: { type: "shadow" },
        backgroundColor: "rgba(23, 32, 42, 0.92)",
        borderWidth: 0,
        textStyle: { color: "#fff" }
      },
      grid: { left: 92, right: 18, top: 20, bottom: 22 },
      xAxis: {
        type: "value",
        splitLine: { lineStyle: { color: "#eef1f5" } },
        axisLabel: { color: "#667085", fontSize: 11 }
      },
      yAxis: {
        type: "category",
        data: data.map((item) => item.name),
        axisTick: { show: false },
        axisLine: { lineStyle: { color: "#d9dee7" } },
        axisLabel: {
          color: "#344054",
          fontSize: 11,
          width: 82,
          overflow: "truncate"
        }
      },
      series: [
        {
          name: "数量",
          type: "bar",
          data,
          barWidth: 14,
          itemStyle: {
            borderRadius: [0, 7, 7, 0],
            color: new echarts.graphic.LinearGradient(0, 0, 1, 0, [
              { offset: 0, color: "#70b7a6" },
              { offset: 1, color: "#176b5b" }
            ])
          },
          label: {
            show: true,
            position: "right",
            color: "#475467",
            fontSize: 11,
            formatter: "{c}"
          }
        }
      ]
    }),
    [data]
  );

  return (
    <EChartCard
      title={title}
      meta={items.length ? `${items.length} 项` : ""}
      option={option}
      loading={loading}
      isEmpty={items.length === 0}
      emptyText={emptyText}
      onSelect={onSelect}
    />
  );
}

function ScoreBucketChart({
  title,
  buckets,
  loading,
  onSelect
}: {
  title: string;
  buckets: LibraryAnalyticsScoreBucket[];
  loading: boolean;
  onSelect: (bucket: LibraryAnalyticsScoreBucket) => void;
}) {
  const data = useMemo<ScoreChartDatum[]>(
    () =>
      buckets.map((bucket) => ({
        key: bucket.key,
        name: bucket.label,
        value: bucket.value,
        bucket
      })),
    [buckets]
  );
  const option = useMemo<EChartsOption>(
    () => ({
      color: chartPalette,
      tooltip: {
        trigger: "axis",
        axisPointer: { type: "shadow" },
        backgroundColor: "rgba(23, 32, 42, 0.92)",
        borderWidth: 0,
        textStyle: { color: "#fff" }
      },
      grid: { left: 34, right: 16, top: 20, bottom: 30 },
      xAxis: {
        type: "category",
        data: data.map((bucket) => bucket.name),
        axisTick: { show: false },
        axisLine: { lineStyle: { color: "#d9dee7" } },
        axisLabel: { color: "#667085", fontSize: 11 }
      },
      yAxis: {
        type: "value",
        splitLine: { lineStyle: { color: "#eef1f5" } },
        axisLabel: { color: "#667085", fontSize: 11 }
      },
      series: [
        {
          name: "数量",
          type: "bar",
          data,
          barWidth: "46%",
          itemStyle: {
            borderRadius: [6, 6, 0, 0],
            color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
              { offset: 0, color: "#f59e0b" },
              { offset: 1, color: "#fedf89" }
            ])
          },
          label: {
            show: true,
            position: "top",
            color: "#475467",
            fontSize: 11,
            formatter: "{c}"
          }
        }
      ]
    }),
    [data]
  );

  return (
    <EChartCard
      title={title}
      meta={buckets.length ? "4 档" : ""}
      option={option}
      loading={loading}
      isEmpty={buckets.length === 0}
      emptyText="暂无分数数据"
      onSelect={(key) => {
        const selected = buckets.find((bucket) => bucket.key === key);
        if (selected) {
          onSelect(selected);
        }
      }}
    />
  );
}

function EChartCard({
  title,
  meta,
  option,
  loading,
  isEmpty,
  emptyText,
  className,
  onSelect
}: {
  title: string;
  meta: string;
  option: EChartsOption;
  loading: boolean;
  isEmpty: boolean;
  emptyText: string;
  className?: string;
  onSelect?: (key: string) => void;
}) {
  return (
    <section className={`analyticsCard ${onSelect ? "interactiveChart" : ""} ${className ?? ""}`}>
      <div className="sectionHead tight">
        <h3>{title}</h3>
        <span className="mutedText">{meta}</span>
      </div>
      {!loading && isEmpty ? (
        <div className="chartEmpty">{emptyText}</div>
      ) : (
        <EChartView option={option} loading={loading} onSelect={onSelect} />
      )}
    </section>
  );
}

function EChartView({
  option,
  loading,
  onSelect
}: {
  option: EChartsOption;
  loading: boolean;
  onSelect?: (key: string) => void;
}) {
  const containerRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    if (!containerRef.current) {
      return;
    }

    const chart =
      echarts.getInstanceByDom(containerRef.current) ??
      echarts.init(containerRef.current, undefined, { renderer: "svg" });
    chart.setOption(option, true);

    if (loading) {
      chart.showLoading("default", {
        text: "统计中",
        color: "#176b5b",
        textColor: "#667085",
        maskColor: "rgba(255, 255, 255, 0.72)"
      });
    } else {
      chart.hideLoading();
    }

    const resizeObserver = new ResizeObserver(() => chart.resize());
    resizeObserver.observe(containerRef.current);

    const handleClick = (params: ChartClickParams) => {
      if (!onSelect) {
        return;
      }
      const key = chartDatumKey(params.data);
      if (key) {
        onSelect(key);
      }
    };

    if (onSelect) {
      chart.on("click", handleClick);
    }

    return () => {
      resizeObserver.disconnect();
      if (onSelect) {
        chart.off("click", handleClick);
      }
      chart.dispose();
    };
  }, [loading, onSelect, option]);

  return <div ref={containerRef} className="echartsCanvas" />;
}

function dimensionData(items: LibraryAnalyticsDimension[]): ChartDatum[] {
  return items.map((item) => ({
    key: item.key,
    name: item.label,
    value: item.value
  }));
}

function chartDatumKey(data: unknown) {
  if (typeof data !== "object" || data === null || !("key" in data)) {
    return null;
  }
  const key = (data as { key?: unknown }).key;
  return typeof key === "string" ? key : null;
}

function formatInteger(value: number | undefined) {
  return value === undefined ? "-" : new Intl.NumberFormat("zh-CN").format(value);
}

function formatNumber(value: number | undefined) {
  return value === undefined ? "-" : value.toFixed(1);
}

function formatPercent(value: number) {
  return `${value.toFixed(1)}%`;
}

function formatShortDate(value: string) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value.slice(5);
  }
  return new Intl.DateTimeFormat("zh-CN", {
    month: "2-digit",
    day: "2-digit"
  }).format(date);
}
