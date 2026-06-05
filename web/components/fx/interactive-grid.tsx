"use client";

import { useRef } from "react";

import { type GridFxEnv, useGridFx } from "./use-grid-fx";

/** Parse #rgb / #rrggbb to [r, g, b]; falls back to lime. */
function toRgb(color: string): [number, number, number] {
  let hex = color.trim();
  if (hex.startsWith("#")) hex = hex.slice(1);
  if (hex.length === 3) hex = hex.split("").map((ch) => ch + ch).join("");
  const n = Number.parseInt(hex, 16);
  if (Number.isNaN(n) || hex.length !== 6) return [190, 242, 100];
  return [(n >> 16) & 255, (n >> 8) & 255, n & 255];
}

function mix(value: number, target: number, t: number): number {
  return Math.round(value + (target - value) * t);
}

interface TrailCell {
  col: number;
  row: number;
  life: number;
}
interface Ripple {
  x: number;
  y: number;
  start: number;
}

const RIPPLE_LIFE = 1.1;

/**
 * A faint grid where cells light up along the cursor (a fading snake) and a
 * click sends an expanding 3D wave that lifts cells. Decorative + pointer-thru.
 * Ported from the Plinth lab and retuned for the dark theme.
 */
export function InteractiveGrid({
  className,
  cell = 56,
  trailMax = 22,
  trailDecay = 0.022,
  lineColor = "rgba(231, 233, 236, 0.05)",
  shadowColor = "rgba(0, 0, 0, 0.35)",
}: {
  className?: string;
  cell?: number;
  trailMax?: number;
  trailDecay?: number;
  lineColor?: string;
  shadowColor?: string;
}) {
  const trail = useRef<TrailCell[]>([]);
  const ripples = useRef<Ripple[]>([]);
  const last = useRef({ col: Number.NaN, row: Number.NaN });

  const drawGrid = (env: GridFxEnv) => {
    const { ctx, width, height } = env;
    ctx.clearRect(0, 0, width, height);
    ctx.strokeStyle = lineColor;
    ctx.lineWidth = 1;
    ctx.beginPath();
    for (let x = 0; x <= width; x += cell) {
      ctx.moveTo(x + 0.5, 0);
      ctx.lineTo(x + 0.5, height);
    }
    for (let y = 0; y <= height; y += cell) {
      ctx.moveTo(0, y + 0.5);
      ctx.lineTo(width, y + 0.5);
    }
    ctx.stroke();
  };

  const drawTrail = (env: GridFxEnv) => {
    const { ctx } = env;
    const cells = trail.current;
    for (let i = cells.length - 1; i >= 0; i--) {
      const c = cells[i];
      if (!c) continue;
      c.life -= trailDecay;
      if (c.life <= 0) {
        cells.splice(i, 1);
        continue;
      }
      const headness = (i + 1) / cells.length;
      ctx.globalAlpha = c.life * (0.08 + headness * 0.5);
      ctx.fillStyle = env.accent;
      ctx.fillRect(c.col * cell + 1, c.row * cell + 1, cell - 1, cell - 1);
    }
    ctx.globalAlpha = 1;
  };

  const drawRipples = (env: GridFxEnv, time: number) => {
    const { ctx, width, height, accent } = env;
    const [cr, cg, cb] = toRgb(accent);
    const face = `rgb(${cr}, ${cg}, ${cb})`;
    const topHi = `rgb(${mix(cr, 255, 0.62)}, ${mix(cg, 255, 0.62)}, ${mix(cb, 255, 0.62)})`;
    const wall = `rgb(${mix(cr, 0, 0.72)}, ${mix(cg, 0, 0.72)}, ${mix(cb, 0, 0.72)})`;
    const cols = Math.ceil(width / cell) + 1;
    const rows = Math.ceil(height / cell) + 1;
    const s = cell - 1;
    const all = ripples.current;
    for (let i = all.length - 1; i >= 0; i--) {
      const ripple = all[i];
      if (!ripple) continue;
      const age = (time - ripple.start) / 1000;
      if (age > RIPPLE_LIFE) {
        all.splice(i, 1);
        continue;
      }
      const radius = age * 540;
      const fade = 1 - age / RIPPLE_LIFE;
      for (let c = 0; c < cols; c++) {
        for (let r = 0; r < rows; r++) {
          const cx = c * cell + cell / 2;
          const cy = r * cell + cell / 2;
          const offset = Math.hypot(cx - ripple.x, cy - ripple.y) - radius;
          const h = 22 * Math.exp(-(offset * offset) / (2 * 70 * 70)) * fade;
          if (h < 1) continue;
          const k = h / 22;
          const x = c * cell + 1;
          const y = r * cell;
          const ty = y - h;
          ctx.globalAlpha = 0.16 * k;
          ctx.fillStyle = shadowColor;
          ctx.fillRect(x + h * 0.18, y + 1 + h * 0.18, s, s);
          ctx.globalAlpha = Math.min(1, 0.32 + 0.5 * k);
          ctx.fillStyle = wall;
          ctx.fillRect(x, ty + s, s, h + 1);
          ctx.globalAlpha = Math.min(1, 0.5 + 0.45 * k);
          ctx.fillStyle = face;
          ctx.fillRect(x, ty, s, s);
          ctx.globalAlpha = Math.min(1, 0.3 + 0.55 * k);
          ctx.fillStyle = topHi;
          ctx.fillRect(x, ty, s, Math.max(2, h * 0.3));
        }
      }
    }
    ctx.globalAlpha = 1;
  };

  const canvasRef = useGridFx({
    draw: (env, time) => {
      drawGrid(env);
      drawTrail(env);
      if (ripples.current.length > 0) drawRipples(env, time);
    },
    onPointerMove: (x, y) => {
      const col = Math.floor(x / cell);
      const row = Math.floor(y / cell);
      if (col === last.current.col && row === last.current.row) return;
      last.current = { col, row };
      trail.current.push({ col, row, life: 1 });
      if (trail.current.length > trailMax) trail.current.shift();
    },
    onPointerDown: (x, y) => {
      ripples.current.push({ x, y, start: performance.now() });
    },
  });

  return <canvas ref={canvasRef} className={className} aria-hidden="true" />;
}
