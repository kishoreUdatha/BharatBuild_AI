'use client'

import { Check } from 'lucide-react'
import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import type { ApiStage, ApiStagePoint } from '@/lib/faculty-api'
import { sectionLabel, seriesColors, stageAppearance, type Tone } from '@/lib/faculty-data'
import { cn } from '@/lib/utils'

/**
 * The stepper and the chart plot the same eight stages, so they have to share
 * one horizontal grid or the two rows visibly drift apart. Both are inset by
 * the same amounts: the y-axis gutter on the left, the chart margin on the
 * right. With `scale="band"` the chart puts each point at the centre of its
 * eighth, which is exactly where the stepper centres its node.
 */
const AXIS_WIDTH = 34
const RIGHT_MARGIN = 8

const RING: Record<Tone, string> = {
  green: 'border-[#16A34A]',
  amber: 'border-[#F59E0B]',
  red: 'border-[#EF4444]',
  indigo: 'border-[#6366F1]',
  blue: 'border-[#3B82F6]',
  teal: 'border-[#0D9488]',
  slate: 'border-[#C7CBDD]',
}

const FILL: Record<Tone, string> = {
  green: 'bg-[#16A34A]',
  amber: 'bg-[#F59E0B]',
  red: 'bg-[#EF4444]',
  indigo: 'bg-[#6366F1]',
  blue: 'bg-[#3B82F6]',
  teal: 'bg-[#0D9488]',
  slate: 'bg-[#C7CBDD]',
}

const CONNECTOR: Record<Tone, string> = {
  ...FILL,
  slate: 'bg-[#DDE0EE]',
}

interface Props {
  stages: ApiStage[]
  series: ApiStagePoint[]
  seriesNames: string[]
}

export function ProgressOverview({ stages, series, seriesNames }: Props) {
  const colors = seriesColors(seriesNames)
  const appearances = stages.map((s) => stageAppearance(s.percent))

  // Recharts wants one flat object per x-value, with a key per line.
  const chartData = series.map((point) => ({
    stage: point.stage,
    ...Object.fromEntries(seriesNames.map((name) => [sectionLabel(name), point.values[name] ?? null])),
  }))

  return (
    <section className="rounded-xl border border-[#E8E9F2] bg-white p-4">
      <div className="mb-2 flex flex-wrap items-center justify-between gap-3">
        <h2 className="text-[14px] font-semibold text-[#1B1B3A]">Project Progress Overview</h2>
        <div className="flex items-center gap-5">
          {seriesNames.map((name) => (
            <span key={name} className="flex items-center gap-2 text-[12px] text-[#5A5F7A]">
              <span className="h-[3px] w-5 rounded-full" style={{ backgroundColor: colors[name] }} />
              {sectionLabel(name)}
            </span>
          ))}
        </div>
      </div>

      {/* Stage stepper - inset to match the chart's plot area below it. */}
      <div className="flex" style={{ paddingLeft: AXIS_WIDTH, paddingRight: RIGHT_MARGIN }}>
        {stages.map((stage, i) => {
          const { state, tone } = appearances[i]
          const nextTone = appearances[i + 1]?.tone ?? 'slate'
          return (
            <div key={stage.key} className="flex min-w-0 flex-1 flex-col items-center">
              {/* Fixed row height: completed nodes are 20px and the rest
                  16px, so without this each column would push its own
                  label down by a different amount. */}
              <div className="flex h-5 w-full items-center">
                <div className={cn('h-[2px] flex-1', i === 0 ? 'bg-transparent' : CONNECTOR[tone])} />
                {state === 'complete' ? (
                  <div className={cn('flex h-5 w-5 items-center justify-center rounded-full', FILL[tone])}>
                    <Check className="h-3 w-3 text-white" strokeWidth={3} />
                  </div>
                ) : (
                  <div className={cn('h-4 w-4 rounded-full border-2 bg-white', RING[tone])} />
                )}
                <div
                  className={cn('h-[2px] flex-1', i === stages.length - 1 ? 'bg-transparent' : CONNECTOR[nextTone])}
                />
              </div>

              <div className="mt-1.5 whitespace-nowrap text-center text-[10.5px] leading-none text-[#5A5F7A]">
                {stage.label}
              </div>
              <div className="mt-1 text-[11.5px] font-semibold leading-none text-[#1B1B3A]">{stage.percent}%</div>
            </div>
          )
        })}
      </div>

      {/* Per-section trend. With scale="band" each point sits at the centre of
          its eighth, so the axis labels land directly under the matching
          stepper node rather than drifting across the row. */}
      <div className="mt-2 h-[112px] w-full">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={chartData} margin={{ top: 4, right: RIGHT_MARGIN, bottom: 6, left: 0 }}>
            <CartesianGrid stroke="#EEF0F7" vertical={false} />
            <XAxis
              dataKey="stage"
              scale="band"
              tick={false}
              tickLine={false}
              height={6}
              axisLine={{ stroke: '#E8E9F2' }}
            />
            <YAxis
              width={AXIS_WIDTH}
              domain={[0, 100]}
              ticks={[0, 50, 100]}
              tickFormatter={(v) => `${v}%`}
              tick={{ fontSize: 10, fill: '#5A5F7A' }}
              tickLine={false}
              axisLine={false}
            />
            <Tooltip
              formatter={(value: number) => `${value}%`}
              contentStyle={{
                borderRadius: 8,
                border: '1px solid #E8E9F2',
                fontSize: 12,
                boxShadow: '0 4px 12px rgba(27,27,58,0.08)',
              }}
            />
            {seriesNames.map((name) => (
              <Line
                key={name}
                type="linear"
                dataKey={sectionLabel(name)}
                stroke={colors[name]}
                strokeWidth={1.8}
                dot={{ r: 2.5, fill: colors[name], strokeWidth: 0 }}
                activeDot={{ r: 4 }}
              />
            ))}
          </LineChart>
        </ResponsiveContainer>
      </div>

      {/* Axis labels drawn as HTML on the stepper's grid. Recharts places
          band-scale ticks at the band start, half a band left of the points
          they belong to; these columns match the plot exactly. */}
      <div className="mt-1 flex" style={{ paddingLeft: AXIS_WIDTH, paddingRight: RIGHT_MARGIN }}>
        {stages.map((stage) => (
          <div
            key={stage.key}
            className="min-w-0 flex-1 truncate px-0.5 text-center text-[9.5px] leading-none text-[#8A8FA8]"
          >
            {stage.label}
          </div>
        ))}
      </div>
    </section>
  )
}
