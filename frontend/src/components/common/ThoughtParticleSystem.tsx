import React, { useEffect, useRef } from 'react';

export interface ThoughtParticleSystemProps {
  phase?:
    | 'IDLE'
    | 'BRAINS_FORM'
    | 'BRAINS_THINK'
    | 'THINKING'
    | 'TRANSFER'
    | 'CONVERGENCE'
    | 'SYNTHESIS_STABILIZE'
    | 'SYNTHESIS_STREAM'
    | 'SYNTHESIS_LINE'
    | 'JUDGE_ANALYSIS'
    | 'EVALUATION'
    | 'RESULT'
    | 'SYNTHESIZED'
    | 'PRO_THINKING'
    | 'CON_THINKING'
    | 'EXCHANGE';
  intensity?: number;
  showSynthesisLine?: boolean;
  synthesisLineLength?: number; // 0.0 to 1.0 normalized progressive stream length to Judge
  targetJudgeY?: number; // exact relative Y coordinate of the Judge core
  className?: string;
  onConvergenceSnapped?: () => void;
}

interface DigitalDataDot {
  startX: number;
  startY: number;
  targetX: number;
  targetY: number;
  x: number;
  y: number;
  speed: number;
  life: number;
  maxLife: number;
  radius: number;
  color: string;
  source: 'PRO' | 'CON' | 'MERGED';
  curvature: number; // gentle arc perpendicular to path
  status: 'TRAVELING' | 'ORBITING';
  isBright: boolean;
  orbitAngle?: number;
  orbitRadius?: number;
  orbitSpeed?: number;
  orbitLife?: number;
}

/**
 * ThoughtParticleSystem
 * Renders pure digital information dots (NO creatures, NO heads, NO organism shapes)
 * traveling from dual AI neural brains to the central synthesis point, and the progressive
 * downward synthesis stream to the Independent Judge.
 */
export const ThoughtParticleSystem: React.FC<ThoughtParticleSystemProps> = ({
  phase = 'EXCHANGE',
  intensity = 1.0,
  showSynthesisLine = false,
  synthesisLineLength = 0,
  targetJudgeY,
  className = '',
  onConvergenceSnapped,
}) => {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const snappedFiredRef = useRef<boolean>(false);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    let animId: number;
    let width = (canvas.width = canvas.parentElement?.clientWidth || 800);
    let height = (canvas.height = canvas.parentElement?.clientHeight || 500);

    const handleResize = () => {
      if (!canvas || !canvas.parentElement) return;
      width = canvas.width = canvas.parentElement.clientWidth;
      height = canvas.height = canvas.parentElement.clientHeight;
    };
    window.addEventListener('resize', handleResize);

    const dots: DigitalDataDot[] = [];
    const maxActiveDots = width < 640 ? 40 : 70;

    const startTime = performance.now();

    // Exact Palettes from Master Prompt:
    // PRO: Cyan, Blue, White highlights (#22D3EE, #38BDF8, #60A5FA, #FFFFFF)
    const proColors = ['#22D3EE', '#38BDF8', '#60A5FA', '#FFFFFF'];
    // CON: Purple, Violet, Magenta, White highlights (#A78BFA, #8B5CF6, #D946EF, #FFFFFF)
    const conColors = ['#A78BFA', '#8B5CF6', '#D946EF', '#FFFFFF'];
    // Synthesis merged palette: Neutral White, Indigo, Subtle Violet, Subtle Gold
    const mergedColors = ['#FFFFFF', '#818CF8', '#C084FC', '#FEF08A'];

    const render = (currentTime: number) => {
      ctx.clearRect(0, 0, width, height);

      const elapsed = (currentTime - startTime) * 0.001;

      // Central Synthesis Point & Brain Flank Coordinates
      const centerX = width * 0.5;
      const centerY = height * 0.36;

      const proX = width < 640 ? 75 : width < 1024 ? 120 : 160;
      const conX = width < 640 ? width - 75 : width < 1024 ? width - 120 : width - 160;

      // Exact Judge Destination Coordinate (relative Y in container)
      const judgeY = targetJudgeY !== undefined ? targetJudgeY : height * 0.62;

      // Phase Classification
      const isTransferring =
        phase === 'TRANSFER' ||
        phase === 'EXCHANGE' ||
        phase === 'PRO_THINKING' ||
        phase === 'CON_THINKING';

      const isProSolo = phase === 'PRO_THINKING';
      const isConSolo = phase === 'CON_THINKING';

      const isConvergencePhase =
        phase === 'CONVERGENCE' ||
        phase === 'SYNTHESIS_STABILIZE';

      const isSynthesisComplete =
        phase === 'SYNTHESIS_STREAM' ||
        phase === 'SYNTHESIS_LINE' ||
        phase === 'JUDGE_ANALYSIS' ||
        phase === 'EVALUATION' ||
        phase === 'RESULT' ||
        phase === 'SYNTHESIZED';

      // 1. SPAWN DIGITAL DATA DOTS (Simultaneous PRO & CON transfer)
      // Dots only spawn during active transfer phases; ZERO dots spawn during thinking or brains form
      if (isTransferring && dots.length < maxActiveDots && Math.random() < 0.45 * intensity) {
        // PRO Digital Data Dot (Blue/Cyan/White)
        if (!isConSolo) {
          const startY = centerY + (Math.random() - 0.5) * 44;
          const speed = Math.random() * 2.2 + 2.0;
          const totalDist = Math.hypot(centerX - proX, centerY - startY);
          const maxLife = Math.ceil(totalDist / speed);
          const radius = Math.random() < 0.3 ? 1.5 : Math.random() < 0.75 ? 2.2 : 3.0;

          dots.push({
            startX: proX,
            startY,
            targetX: centerX,
            targetY: centerY,
            x: proX,
            y: startY,
            speed,
            life: 0,
            maxLife,
            radius,
            color: proColors[Math.floor(Math.random() * proColors.length)],
            source: 'PRO',
            curvature: (Math.random() - 0.5) * 45, // gentle computational curve
            status: 'TRAVELING',
            isBright: Math.random() < 0.25,
          });
        }

        // CON Digital Data Dot (Purple/Violet/Magenta/White) - Simultaneous
        if (!isProSolo) {
          const startY = centerY + (Math.random() - 0.5) * 44;
          const speed = Math.random() * 2.2 + 2.0;
          const totalDist = Math.hypot(centerX - conX, centerY - startY);
          const maxLife = Math.ceil(totalDist / speed);
          const radius = Math.random() < 0.3 ? 1.5 : Math.random() < 0.75 ? 2.2 : 3.0;

          dots.push({
            startX: conX,
            startY,
            targetX: centerX,
            targetY: centerY,
            x: conX,
            y: startY,
            speed,
            life: 0,
            maxLife,
            radius,
            color: conColors[Math.floor(Math.random() * conColors.length)],
            source: 'CON',
            curvature: (Math.random() - 0.5) * 45,
            status: 'TRAVELING',
            isBright: Math.random() < 0.25,
          });
        }
      }

      // 2. CENTRAL SYNTHESIS NODE (The true convergence point)
      // Stays subtle until particles arrive, then brightens during convergence and stabilization
      const nodePulse = Math.sin(elapsed * 3.5) * 3;
      const isNodeActive = isConvergencePhase || isSynthesisComplete;
      const nodeRadius = isSynthesisComplete ? 10 : isConvergencePhase ? 9 : 6;

      // Soft ambient background aura behind the node
      const nodeGrad = ctx.createRadialGradient(
        centerX,
        centerY,
        1,
        centerX,
        centerY,
        isNodeActive ? 30 + nodePulse : 18
      );
      nodeGrad.addColorStop(0, isNodeActive ? 'rgba(255, 255, 255, 0.95)' : 'rgba(255, 255, 255, 0.4)');
      nodeGrad.addColorStop(0.35, isNodeActive ? 'rgba(129, 140, 248, 0.6)' : 'rgba(99, 102, 241, 0.2)');
      nodeGrad.addColorStop(0.75, isNodeActive ? 'rgba(99, 102, 241, 0.2)' : 'rgba(99, 102, 241, 0.05)');
      nodeGrad.addColorStop(1, 'transparent');

      ctx.fillStyle = nodeGrad;
      ctx.beginPath();
      ctx.arc(centerX, centerY, isNodeActive ? 32 + nodePulse : 20, 0, Math.PI * 2);
      ctx.fill();

      // Subtle gyroscopic orbital ring around synthesis point
      if (isNodeActive) {
        ctx.save();
        ctx.translate(centerX, centerY);
        ctx.rotate(elapsed * 0.7);
        ctx.strokeStyle = isSynthesisComplete ? 'rgba(254, 240, 138, 0.75)' : 'rgba(129, 140, 248, 0.6)';
        ctx.lineWidth = 1.0;
        ctx.beginPath();
        ctx.ellipse(0, 0, 16, 8, Math.PI / 4, 0, Math.PI * 2);
        ctx.stroke();

        ctx.rotate(-elapsed * 1.4);
        ctx.strokeStyle = 'rgba(255, 255, 255, 0.7)';
        ctx.lineWidth = 0.8;
        ctx.setLineDash([2, 2]);
        ctx.beginPath();
        ctx.ellipse(0, 0, 13, 6, -Math.PI / 4, 0, Math.PI * 2);
        ctx.stroke();
        ctx.restore();
      }

      // Central solid core dot of synthesis node
      ctx.fillStyle = '#FFFFFF';
      ctx.beginPath();
      ctx.arc(centerX, centerY, nodeRadius, 0, Math.PI * 2);
      ctx.fill();

      ctx.fillStyle = isSynthesisComplete ? '#FEF08A' : isConvergencePhase ? '#818CF8' : '#38BDF8';
      ctx.beginPath();
      ctx.arc(centerX, centerY, nodeRadius * 0.5, 0, Math.PI * 2);
      ctx.fill();

      // 3. UPDATE & DRAW PURE DIGITAL DATA DOTS (NO TAILS, NO CREATURE SHAPES)
      for (let i = dots.length - 1; i >= 0; i--) {
        const d = dots[i];
        d.life++;

        if (d.status === 'TRAVELING') {
          const progress = Math.min(d.life / d.maxLife, 1.0);

          // Linear trajectory + smooth sine-wave arc offset
          const linearX = d.startX + (d.targetX - d.startX) * progress;
          const linearY = d.startY + (d.targetY - d.startY) * progress;
          const arcOffset = Math.sin(progress * Math.PI) * d.curvature;

          d.x = linearX;
          d.y = linearY + arcOffset;

          // Arrival into central synthesis zone
          if (progress >= 1.0) {
            d.status = 'ORBITING';
            d.orbitAngle = Math.atan2(d.y - centerY, d.x - centerX);
            d.orbitRadius = Math.random() * 14 + 6;
            d.orbitSpeed = (Math.random() * 0.05 + 0.03) * (Math.random() < 0.5 ? 1 : -1);
            d.orbitLife = 0;
            // Colors mix upon arrival into the synthesis palette (white/indigo/gold)
            d.color = mergedColors[Math.floor(Math.random() * mergedColors.length)];
          }
        } else if (d.status === 'ORBITING') {
          // Orbiting within the central synthesis node
          d.orbitLife = (d.orbitLife || 0) + 1;
          d.orbitAngle = (d.orbitAngle || 0) + (d.orbitSpeed || 0.04);
          // Gradually pull into exact core
          d.orbitRadius = Math.max((d.orbitRadius || 10) - 0.2, 2);

          d.x = centerX + Math.cos(d.orbitAngle) * d.orbitRadius;
          d.y = centerY + Math.sin(d.orbitAngle) * d.orbitRadius;

          // Expire when fully absorbed into the core
          if ((d.orbitRadius <= 2.2 || (d.orbitLife || 0) > 50)) {
            dots.splice(i, 1);
            continue;
          }
        }

        // PURE DIGITAL DATA DOT RENDERING:
        // Strictly circular. Zero tails, zero comets, zero organism shapes.
        const alpha = d.status === 'TRAVELING'
          ? Math.min(d.life / 8, 1.0)
          : Math.max(1 - (d.orbitLife || 0) / 50, 0.2);

        // Soft subtle glow halo (1.2px wider than dot)
        ctx.fillStyle = d.color;
        ctx.globalAlpha = Math.max(alpha * 0.35, 0);
        ctx.beginPath();
        ctx.arc(d.x, d.y, d.radius + 1.2, 0, Math.PI * 2);
        ctx.fill();

        // Core crisp digital dot
        ctx.globalAlpha = Math.max(alpha, 0);
        ctx.beginPath();
        ctx.arc(d.x, d.y, d.radius, 0, Math.PI * 2);
        ctx.fill();

        // Center white spark for brightest dots
        if (d.isBright) {
          ctx.fillStyle = '#FFFFFF';
          ctx.globalAlpha = Math.max(alpha * 0.9, 0);
          ctx.beginPath();
          ctx.arc(d.x, d.y, d.radius * 0.45, 0, Math.PI * 2);
          ctx.fill();
        }
      }

      ctx.globalAlpha = 1;

      // 4. DOWNWARD SYNTHESIS DATA STREAM (ONLY SHOWN AFTER SYNTHESIS STABILIZATION)
      // Section 14 & 20: NEVER show during PRO/CON transfer or convergence!
      // Must progressively extend downward from centerY all the way down to judgeY.
      if (showSynthesisLine && synthesisLineLength > 0.02) {
        const clampedProgress = Math.min(Math.max(synthesisLineLength, 0), 1.0);
        const lineEndY = centerY + (judgeY - centerY) * clampedProgress;
        const currentDistance = lineEndY - centerY;

        if (currentDistance > 3) {
          // Volumetric soft outer glow
          ctx.beginPath();
          ctx.moveTo(centerX, centerY);
          ctx.lineTo(centerX, lineEndY);
          ctx.strokeStyle = 'rgba(99, 102, 241, 0.4)';
          ctx.lineWidth = 4.5;
          ctx.stroke();

          // Core bright white data line
          ctx.strokeStyle = '#FFFFFF';
          ctx.lineWidth = 1.8;
          ctx.stroke();

          // Subtle gold accent filament
          ctx.strokeStyle = '#FEF08A';
          ctx.lineWidth = 0.8;
          ctx.stroke();

          // Small discrete digital data dots traveling downward along the stream
          const streamDotsCount = 4;
          for (let k = 0; k < streamDotsCount; k++) {
            const streamPhase = ((elapsed * 0.7 + k / streamDotsCount) % 1.0);
            const dotY = centerY + currentDistance * streamPhase;

            // Small traveling digital dot
            ctx.fillStyle = '#FFFFFF';
            ctx.beginPath();
            ctx.arc(centerX, dotY, 2.2, 0, Math.PI * 2);
            ctx.fill();

            ctx.fillStyle = 'rgba(254, 240, 138, 0.7)';
            ctx.beginPath();
            ctx.arc(centerX, dotY, 3.8, 0, Math.PI * 2);
            ctx.fill();
          }

          // Arrival reception node at Judge core when stream reaches the Judge
          if (clampedProgress >= 0.98) {
            const entryGlow = ctx.createRadialGradient(centerX, judgeY, 1, centerX, judgeY, 15);
            entryGlow.addColorStop(0, '#FFFFFF');
            entryGlow.addColorStop(0.4, 'rgba(254, 240, 138, 0.8)');
            entryGlow.addColorStop(0.8, 'rgba(99, 102, 241, 0.35)');
            entryGlow.addColorStop(1, 'transparent');

            ctx.fillStyle = entryGlow;
            ctx.beginPath();
            ctx.arc(centerX, judgeY, 15, 0, Math.PI * 2);
            ctx.fill();
          }
        }
      }

      // Notify callback if convergence snapped
      if (isConvergencePhase && !snappedFiredRef.current) {
        snappedFiredRef.current = true;
        onConvergenceSnapped?.();
      }

      animId = requestAnimationFrame(render);
    };

    animId = requestAnimationFrame(render);

    return () => {
      cancelAnimationFrame(animId);
      window.removeEventListener('resize', handleResize);
    };
  }, [phase, intensity, showSynthesisLine, synthesisLineLength, targetJudgeY, onConvergenceSnapped]);

  return (
    <div className={`relative w-full h-full pointer-events-none select-none ${className}`}>
      <canvas ref={canvasRef} className="w-full h-full block" />
    </div>
  );
};

export default ThoughtParticleSystem;
