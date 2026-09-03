'use client'

/**
 * Sprint burndown - points still open on each day against the ideal line.
 *
 * Two marks, not two series of equal weight: the ideal is a guide (recessive
 * grey, dashed) and the remaining line is the data (2px, one hue). Colours were
 * validated against the white card surface - the data hue passes the
 * categorical checks on its own, and the guide grey clears 3:1 contrast.
 *
 * The actual line stops at today. Drawing it on to zero across days that have
 * not happened would claim work nobody has done.
 */

import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { Loader2, Table2, TrendingDown } from 'lucide-react'
import { apiClient } from '@/lib/api-client'
import { cn } from '@/lib/utils'

const DATA = '#2563EB'      // remaining - validated categorical hue
const GUIDE = '#6B7280'     // ideal - guide mark, 4.83:1 on white
const GRID = '#EEF1F8'
const INK = '#1B1B3A'
const MUTED = '#6B7280'

interface Day {
  date: string
  day: number
  remaining: number | null
  ideal: number
  completed: number
  scope: number
  is_today: boolean
}

interface Burndown {
  sprint: { id: string; name: string; state: string; goal: string | null
            start_date: string | null; end_date: string | null }
  total_points: number
  completed_points: number
  remaining_points: number
  days: Day[]
  story_count: number
  variance: number
  unscheduled: boolean
}

const W = 640
const H = 220
const PAD = { top: 14, right: 16, bottom: 28, left: 34 }

export function BurndownChart({ code, sprintId }: { code: string; sprintId: string }) {
  const [data, setData] = useState<Burndown | null>(null)
  const [error, setError] = useState('')
  const [asTable, setAsTable] = useState(false)
  const [hover, setHover] = useState<number | null>(null)
  const svgRef = useRef<SVGSVGElement>(null)

  const load = useCallback(async () => {
    setError('')
    try {
      setData(await apiClient.get<Burndown>(
        `/trainer/batches/${encodeURIComponent(code)}/sprints/${sprintId}/burndown`))
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Could not load the burndown.')
    }
  }, [code, sprintId])

  useEffect(() => { load() }, [load])

  const geometry = useMemo(() => {
    if (!data || data.days.length === 0) return null
    const days = data.days
    const maxY = Math.max(data.total_points, ...days.map((d) => d.scope), 1)
    const plotW = W - PAD.left - PAD.right
    const plotH = H - PAD.top - PAD.bottom
    const x = (i: number) => PAD.left + (days.length === 1 ? plotW / 2
      : (i / (days.length - 1)) * plotW)
    const y = (v: number) => PAD.top + plotH - (v / maxY) * plotH
    const actual = days.map((d, i) => ({ ...d, i, cx: x(i), cy: d.remaining === null ? null : y(d.remaining) }))
    return { days, maxY, x, y, actual, plotW, plotH }
  }, [data])

  if (error) {
    return <p className="px-4 py-6 text-center text-[12px] text-[#DC2626]">{error}</p>
  }
  if (!data) {
    return (
      <p className="flex items-center justify-center gap-2 px-4 py-6 text-[12px] text-[#6B7280]">
        <Loader2 className="h-4 w-4 animate-spin" /> Loading the burndown…
      </p>
    )
  }
  if (data.unscheduled || !geometry) {
    return (
      <p className="px-4 py-6 text-center text-[12px] text-[#6B7280]">
        This sprint has no start and end date yet, so there is nothing to burn down against.
      </p>
    )
  }

  const { days, maxY, x, y, actual, plotH } = geometry
  const drawn = actual.filter((d) => d.cy !== null)
  const line = drawn.map((d, n) => `${n === 0 ? 'M' : 'L'}${d.cx},${d.cy}`).join(' ')
  const idealLine = `M${x(0)},${y(days[0].ideal)} L${x(days.length - 1)},${y(days[days.length - 1].ideal)}`
  const ticks = [0, 0.25, 0.5, 0.75, 1].map((f) => Math.round(maxY * f))
  const active = hover !== null ? actual[hover] : null
  const ahead = data.variance < 0

  const onMove = (e: React.MouseEvent<SVGSVGElement>) => {
    const box = svgRef.current?.getBoundingClientRect()
    if (!box) return
    const px = ((e.clientX - box.left) / box.width) * W
    let nearest = 0
    actual.forEach((d, i) => {
      if (Math.abs(d.cx - px) < Math.abs(actual[nearest].cx - px)) nearest = i
    })
    setHover(nearest)
  }

  return (
    <div className="px-4 pb-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h3 className="flex items-center gap-1.5 text-[12.5px] font-semibold text-[#1B1B3A]">
          <TrendingDown className="h-4 w-4 text-[#6B7280]" /> Burndown
        </h3>
        <div className="flex items-center gap-3">
          {/* A single glance summary: the chart shows the shape, this says
              where it ended up. */}
          <span className="text-[11.5px] text-[#6B7280]">
            {data.completed_points} of {data.total_points} points done ·{' '}
            <span className={cn('font-medium', ahead ? 'text-[#15803D]' : 'text-[#B45309]')}>
              {ahead ? `${Math.abs(data.variance)} ahead of plan`
                : data.variance === 0 ? 'on plan' : `${data.variance} behind plan`}
            </span>
          </span>
          <button type="button" onClick={() => setAsTable((v) => !v)}
            aria-pressed={asTable}
            className="flex items-center gap-1 rounded-lg border border-[#D1D5DB] px-2 py-1 text-[11px] font-medium text-[#374151] hover:bg-[#F9FAFB]">
            <Table2 className="h-3 w-3" /> {asTable ? 'Chart' : 'Table'}
          </button>
        </div>
      </div>

      {/* Identity is never colour alone: both marks are named here, and the
          guide is dashed as well as grey. */}
      <div className="mt-1.5 flex flex-wrap items-center gap-3 text-[11px] text-[#4B5563]">
        <span className="flex items-center gap-1.5">
          <svg width="18" height="8" aria-hidden="true">
            <line x1="0" y1="4" x2="18" y2="4" stroke={DATA} strokeWidth="2" />
          </svg>
          Remaining
        </span>
        <span className="flex items-center gap-1.5">
          <svg width="18" height="8" aria-hidden="true">
            <line x1="0" y1="4" x2="18" y2="4" stroke={GUIDE} strokeWidth="2" strokeDasharray="4 3" />
          </svg>
          Ideal
        </span>
      </div>

      {asTable ? (
        <div className="mt-2 max-h-[220px] overflow-y-auto">
          <table className="w-full text-left text-[11.5px]">
            <thead className="sticky top-0 bg-white">
              <tr className="border-b border-[#E5E7EB] text-[#374151]">
                {['Day', 'Date', 'Remaining', 'Ideal', 'Done'].map((h) => (
                  <th key={h} className="py-1.5 pr-3 font-semibold">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-[#F1F2F8] text-[#4B5563]">
              {days.map((d) => (
                <tr key={d.date} className={cn(d.is_today && 'bg-[#F4F7FF]')}>
                  <td className="py-1 pr-3">{d.day}</td>
                  <td className="py-1 pr-3">{d.date}</td>
                  <td className="py-1 pr-3 font-medium text-[#1B1B3A]">
                    {d.remaining === null ? '—' : d.remaining}
                  </td>
                  <td className="py-1 pr-3">{d.ideal}</td>
                  <td className="py-1 pr-3">{d.completed}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <figure className="mt-1">
          <svg ref={svgRef} viewBox={`0 0 ${W} ${H}`} className="w-full"
            role="img" onMouseMove={onMove} onMouseLeave={() => setHover(null)}
            aria-label={`Burndown for ${data.sprint.name}: ${data.completed_points} of ${data.total_points} points completed`}>
            {/* recessive grid */}
            {ticks.map((t) => (
              <g key={t}>
                <line x1={PAD.left} x2={W - PAD.right} y1={y(t)} y2={y(t)}
                  stroke={GRID} strokeWidth="1" />
                <text x={PAD.left - 6} y={y(t) + 3} textAnchor="end"
                  fontSize="9" fill={MUTED}>{t}</text>
              </g>
            ))}

            {/* day axis: first, last and today only - a label per day is noise */}
            {days.map((d, i) => (
              (i === 0 || i === days.length - 1 || d.is_today) && (
                <text key={d.date} x={x(i)} y={H - 10} textAnchor="middle"
                  fontSize="9" fill={MUTED}>
                  {d.is_today ? 'Today' : `Day ${d.day}`}
                </text>
              )
            ))}

            {days.some((d) => d.is_today) && (
              <line x1={x(days.findIndex((d) => d.is_today))}
                x2={x(days.findIndex((d) => d.is_today))}
                y1={PAD.top} y2={PAD.top + plotH}
                stroke={GRID} strokeWidth="2" />
            )}

            <path d={idealLine} fill="none" stroke={GUIDE} strokeWidth="2"
              strokeDasharray="5 4" strokeLinecap="round" />
            <path d={line} fill="none" stroke={DATA} strokeWidth="2"
              strokeLinejoin="round" strokeLinecap="round" />

            {drawn.map((d) => (
              <circle key={d.date} cx={d.cx} cy={d.cy as number} r="4"
                fill={DATA} stroke="#FFFFFF" strokeWidth="2" />
            ))}

            {active && active.cy !== null && (
              <g pointerEvents="none">
                <line x1={active.cx} x2={active.cx} y1={PAD.top} y2={PAD.top + plotH}
                  stroke={DATA} strokeWidth="1" strokeDasharray="3 3" opacity="0.5" />
                <circle cx={active.cx} cy={active.cy} r="6" fill={DATA}
                  stroke="#FFFFFF" strokeWidth="2" />
              </g>
            )}
          </svg>

          {active && (
            <figcaption className="mt-1 text-center text-[11px] text-[#4B5563]">
              <span className="font-medium text-[#1B1B3A]">Day {active.day}</span>
              {' · '}{active.date}
              {active.remaining !== null && <> · <span style={{ color: DATA }}>●</span> {active.remaining} remaining</>}
              {' · '}<span style={{ color: GUIDE }}>▬</span> {active.ideal} ideal
              {active.completed > 0 && ` · ${active.completed} done`}
            </figcaption>
          )}
        </figure>
      )}
    </div>
  )
}
