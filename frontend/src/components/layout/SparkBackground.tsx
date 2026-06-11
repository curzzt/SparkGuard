import { useEffect, useRef } from "react";

interface Particle {
  x: number;
  y: number;
  vx: number;
  vy: number;
  r: number;
  hue: number;
  alpha: number;
  life: number;
  maxLife: number;
}

const PARTICLE_COUNT = 70;

export default function SparkBackground() {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;

    const dpr = Math.min(window.devicePixelRatio || 1, 2);
    let width = 0;
    let height = 0;
    let raf = 0;
    const mouse = { x: -9999, y: -9999 };
    const particles: Particle[] = [];

    const resize = () => {
      width = window.innerWidth;
      height = window.innerHeight;
      canvas.width = width * dpr;
      canvas.height = height * dpr;
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    };

    const spawn = (initial: boolean): Particle => {
      const maxLife = 360 + Math.random() * 420;
      return {
        x: Math.random() * width,
        y: initial ? Math.random() * height : height + 12,
        vx: (Math.random() - 0.5) * 0.35,
        vy: -(0.25 + Math.random() * 0.85),
        r: 0.8 + Math.random() * 2.1,
        hue: Math.random() < 0.25 ? 188 + Math.random() * 14 : 14 + Math.random() * 36,
        alpha: 0.25 + Math.random() * 0.55,
        life: initial ? Math.random() * maxLife : 0,
        maxLife,
      };
    };

    const onMouseMove = (e: MouseEvent) => {
      mouse.x = e.clientX;
      mouse.y = e.clientY;
    };

    const onMouseLeave = () => {
      mouse.x = -9999;
      mouse.y = -9999;
    };

    resize();
    for (let i = 0; i < PARTICLE_COUNT; i += 1) {
      particles.push(spawn(true));
    }

    const tick = () => {
      ctx.clearRect(0, 0, width, height);
      ctx.globalCompositeOperation = "lighter";

      for (let i = 0; i < particles.length; i += 1) {
        const p = particles[i];
        p.life += 1;

        const dx = p.x - mouse.x;
        const dy = p.y - mouse.y;
        const distSq = dx * dx + dy * dy;
        if (distSq < 140 * 140 && distSq > 0.01) {
          const dist = Math.sqrt(distSq);
          const force = ((140 - dist) / 140) * 0.6;
          p.vx += (dx / dist) * force;
          p.vy += (dy / dist) * force;
        }

        p.vx *= 0.96;
        p.vy = p.vy * 0.96 - 0.012;
        p.x += p.vx + Math.sin((p.life + p.maxLife) * 0.012) * 0.18;
        p.y += p.vy;

        if (p.life > p.maxLife || p.y < -14 || p.x < -14 || p.x > width + 14) {
          particles[i] = spawn(false);
          continue;
        }

        const fade = Math.min(p.life / 40, 1) * Math.min((p.maxLife - p.life) / 80, 1);
        ctx.beginPath();
        ctx.arc(p.x, p.y, p.r, 0, Math.PI * 2);
        ctx.fillStyle = `hsla(${p.hue}, 92%, 62%, ${p.alpha * fade})`;
        ctx.fill();
      }

      raf = requestAnimationFrame(tick);
    };

    raf = requestAnimationFrame(tick);
    window.addEventListener("resize", resize);
    window.addEventListener("mousemove", onMouseMove);
    document.addEventListener("mouseleave", onMouseLeave);

    return () => {
      cancelAnimationFrame(raf);
      window.removeEventListener("resize", resize);
      window.removeEventListener("mousemove", onMouseMove);
      document.removeEventListener("mouseleave", onMouseLeave);
    };
  }, []);

  return (
    <>
      <div className="aurora" aria-hidden />
      <div className="grid-overlay" aria-hidden />
      <canvas ref={canvasRef} className="spark-canvas" aria-hidden />
    </>
  );
}
