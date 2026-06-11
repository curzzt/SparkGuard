interface Segment {
  value: number;
  color: string;
}

interface ProgressRingProps {
  segments: Segment[];
  total: number;
  size?: number;
  strokeWidth?: number;
  children?: React.ReactNode;
}

export default function ProgressRing({ segments, total, size = 148, strokeWidth = 8, children }: ProgressRingProps) {
  const radius = (size - strokeWidth) / 2;
  const circumference = 2 * Math.PI * radius;
  const safeTotal = Math.max(total, 1);

  let offset = 0;
  const arcs = segments
    .filter((s) => s.value > 0)
    .map((s, i) => {
      const fraction = Math.min(s.value / safeTotal, 1);
      const arc = {
        key: i,
        color: s.color,
        dash: `${fraction * circumference} ${circumference}`,
        offset: -offset * circumference,
      };
      offset += fraction;
      return arc;
    });

  return (
    <div className="relative inline-flex items-center justify-center" style={{ width: size, height: size }}>
      <svg width={size} height={size} className="-rotate-90">
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke="rgba(255,255,255,0.07)"
          strokeWidth={strokeWidth}
        />
        {arcs.map((arc) => (
          <circle
            key={arc.key}
            cx={size / 2}
            cy={size / 2}
            r={radius}
            fill="none"
            stroke={arc.color}
            strokeWidth={strokeWidth}
            strokeLinecap="round"
            strokeDasharray={arc.dash}
            strokeDashoffset={arc.offset}
            style={{
              filter: `drop-shadow(0 0 6px ${arc.color})`,
              transition: "stroke-dasharray 0.8s var(--ease-hud), stroke-dashoffset 0.8s var(--ease-hud)",
            }}
          />
        ))}
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center">{children}</div>
    </div>
  );
}
