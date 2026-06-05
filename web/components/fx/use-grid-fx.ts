"use client";

import { useEffect, useRef } from "react";

export interface GridFxEnv {
  ctx: CanvasRenderingContext2D;
  width: number; // CSS px
  height: number;
  accent: string; // current --color-accent
}

export interface GridFxHandlers {
  draw: (env: GridFxEnv, time: number) => void;
  onPointerMove?: (x: number, y: number, env: GridFxEnv) => void;
  onPointerDown?: (x: number, y: number, env: GridFxEnv) => void;
  onPointerLeave?: () => void;
}

/**
 * Canvas backdrop plumbing for the grid effects: dpr-aware sizing, a rAF loop,
 * accent read from --color-accent, window pointer mapping, and a reduced-motion
 * path that draws one static frame. Handlers are read live each frame.
 * Ported from the Plinth lab (packages/ui/src/fx/use-grid-fx).
 */
export function useGridFx(handlers: GridFxHandlers) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const handlersRef = useRef(handlers);
  handlersRef.current = handlers;

  useEffect(() => {
    const view = canvasRef.current;
    if (!view) return;
    const ctx = view.getContext("2d");
    if (!ctx) return;

    const readAccent = () =>
      getComputedStyle(view).getPropertyValue("--color-accent").trim() || "#bef264";
    const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    const env: GridFxEnv = { ctx, width: 0, height: 0, accent: readAccent() };
    let raf = 0;

    const resize = () => {
      const rect = view.getBoundingClientRect();
      const dpr = Math.min(window.devicePixelRatio || 1, 2);
      env.width = rect.width;
      env.height = rect.height;
      view.width = Math.max(1, Math.round(rect.width * dpr));
      view.height = Math.max(1, Math.round(rect.height * dpr));
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    };
    const drawOnce = () => handlersRef.current.draw(env, performance.now());
    const locate = (cx: number, cy: number) => {
      const rect = view.getBoundingClientRect();
      const x = cx - rect.left;
      const y = cy - rect.top;
      return { x, y, inside: x >= 0 && y >= 0 && x <= env.width && y <= env.height };
    };
    const onMove = (e: PointerEvent) => {
      const h = handlersRef.current.onPointerMove;
      if (!h) return;
      const { x, y, inside } = locate(e.clientX, e.clientY);
      if (inside) h(x, y, env);
    };
    const onDown = (e: PointerEvent) => {
      const h = handlersRef.current.onPointerDown;
      if (!h) return;
      const { x, y, inside } = locate(e.clientX, e.clientY);
      if (inside) h(x, y, env);
    };
    const frame = () => {
      handlersRef.current.draw(env, performance.now());
      raf = requestAnimationFrame(frame);
    };
    const ro = new ResizeObserver(() => {
      resize();
      if (reduceMotion) drawOnce();
    });
    ro.observe(view);
    resize();
    const onLeave = () => handlersRef.current.onPointerLeave?.();

    if (reduceMotion) {
      drawOnce();
    } else {
      window.addEventListener("pointermove", onMove);
      window.addEventListener("pointerdown", onDown);
      view.addEventListener("pointerleave", onLeave);
      raf = requestAnimationFrame(frame);
    }
    return () => {
      cancelAnimationFrame(raf);
      ro.disconnect();
      window.removeEventListener("pointermove", onMove);
      window.removeEventListener("pointerdown", onDown);
      view.removeEventListener("pointerleave", onLeave);
    };
  }, []);

  return canvasRef;
}
