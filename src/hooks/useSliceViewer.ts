import { useState, useCallback, useRef, useEffect } from 'react';
import type { ViewerState } from '@/types/eat';

interface UseSliceViewerReturn {
  viewerState: ViewerState;
  setSlice: (slice: number) => void;
  nextSlice: () => void;
  prevSlice: () => void;
  toggleLayer: (layer: 'ct' | 'eat' | 'pericardium') => void;
  setOpacity: (opacity: number) => void;
  setTotalSlices: (total: number) => void;
  canvasRef: React.RefObject<HTMLCanvasElement>;
}

// Demo slice generator - creates procedural medical-like images
function generateDemoSlice(
  ctx: CanvasRenderingContext2D,
  width: number,
  height: number,
  sliceIndex: number,
  totalSlices: number,
  showCT: boolean,
  showEAT: boolean,
  showPericardium: boolean,
  opacity: number
) {
  // Clear canvas
  ctx.fillStyle = '#0a0a0a';
  ctx.fillRect(0, 0, width, height);

  const centerX = width / 2;
  const centerY = height / 2;
  
  // Simulate slice position affecting heart visibility
  const sliceRatio = sliceIndex / totalSlices;
  const heartVisible = sliceRatio > 0.3 && sliceRatio < 0.8;
  const heartSize = heartVisible 
    ? Math.sin((sliceRatio - 0.3) * Math.PI / 0.5) * 0.8 + 0.2 
    : 0;

  // CT background (body cross-section simulation)
  if (showCT) {
    // Body outline
    ctx.beginPath();
    ctx.ellipse(centerX, centerY, width * 0.42, height * 0.38, 0, 0, Math.PI * 2);
    ctx.fillStyle = '#1a1a1a';
    ctx.fill();

    // Lungs (darker regions)
    ctx.beginPath();
    ctx.ellipse(centerX - width * 0.18, centerY - height * 0.02, width * 0.12, height * 0.18, -0.2, 0, Math.PI * 2);
    ctx.fillStyle = '#0d0d0d';
    ctx.fill();

    ctx.beginPath();
    ctx.ellipse(centerX + width * 0.18, centerY - height * 0.02, width * 0.12, height * 0.18, 0.2, 0, Math.PI * 2);
    ctx.fill();

    // Spine
    ctx.beginPath();
    ctx.ellipse(centerX, centerY + height * 0.25, width * 0.04, height * 0.05, 0, 0, Math.PI * 2);
    ctx.fillStyle = '#4a4a4a';
    ctx.fill();
  }

  // Pericardium outline
  if (showPericardium && heartVisible) {
    ctx.beginPath();
    ctx.ellipse(
      centerX - width * 0.02, 
      centerY - height * 0.05, 
      width * 0.14 * heartSize, 
      height * 0.16 * heartSize, 
      -0.15, 
      0, 
      Math.PI * 2
    );
    ctx.strokeStyle = `rgba(34, 197, 94, ${opacity})`;
    ctx.lineWidth = 2;
    ctx.stroke();
  }

  // EAT (fat around heart)
  if (showEAT && heartVisible) {
    ctx.globalAlpha = opacity;
    
    // Simulate irregular fat distribution
    const eatRegions = [
      { x: -0.08, y: -0.12, rx: 0.04, ry: 0.03 },
      { x: 0.06, y: -0.08, rx: 0.035, ry: 0.04 },
      { x: -0.06, y: 0.04, rx: 0.05, ry: 0.03 },
      { x: 0.08, y: 0.02, rx: 0.03, ry: 0.035 },
      { x: -0.02, y: -0.14, rx: 0.045, ry: 0.025 },
    ];

    eatRegions.forEach(region => {
      ctx.beginPath();
      ctx.ellipse(
        centerX + width * region.x * heartSize,
        centerY + height * region.y * heartSize,
        width * region.rx * heartSize,
        height * region.ry * heartSize,
        Math.random() * 0.5,
        0,
        Math.PI * 2
      );
      ctx.fillStyle = 'rgba(239, 68, 68, 0.7)';
      ctx.fill();
    });

    ctx.globalAlpha = 1;
  }
}

export function useSliceViewer(initialTotalSlices = 120): UseSliceViewerReturn {
  const [viewerState, setViewerState] = useState<ViewerState>({
    currentSlice: Math.floor(initialTotalSlices / 2),
    totalSlices: initialTotalSlices,
    showCT: true,
    showEAT: true,
    showPericardium: true,
    overlayOpacity: 0.7,
  });

  const canvasRef = useRef<HTMLCanvasElement>(null);

  // Render the current slice
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    generateDemoSlice(
      ctx,
      canvas.width,
      canvas.height,
      viewerState.currentSlice,
      viewerState.totalSlices,
      viewerState.showCT,
      viewerState.showEAT,
      viewerState.showPericardium,
      viewerState.overlayOpacity
    );
  }, [viewerState]);

  const setSlice = useCallback((slice: number) => {
    setViewerState(prev => ({
      ...prev,
      currentSlice: Math.max(0, Math.min(slice, prev.totalSlices - 1)),
    }));
  }, []);

  const nextSlice = useCallback(() => {
    setViewerState(prev => ({
      ...prev,
      currentSlice: Math.min(prev.currentSlice + 1, prev.totalSlices - 1),
    }));
  }, []);

  const prevSlice = useCallback(() => {
    setViewerState(prev => ({
      ...prev,
      currentSlice: Math.max(prev.currentSlice - 1, 0),
    }));
  }, []);

  const toggleLayer = useCallback((layer: 'ct' | 'eat' | 'pericardium') => {
    setViewerState(prev => ({
      ...prev,
      showCT: layer === 'ct' ? !prev.showCT : prev.showCT,
      showEAT: layer === 'eat' ? !prev.showEAT : prev.showEAT,
      showPericardium: layer === 'pericardium' ? !prev.showPericardium : prev.showPericardium,
    }));
  }, []);

  const setOpacity = useCallback((opacity: number) => {
    setViewerState(prev => ({
      ...prev,
      overlayOpacity: Math.max(0, Math.min(1, opacity)),
    }));
  }, []);

  const setTotalSlices = useCallback((total: number) => {
    setViewerState(prev => ({
      ...prev,
      totalSlices: total,
      currentSlice: Math.min(prev.currentSlice, total - 1),
    }));
  }, []);

  return {
    viewerState,
    setSlice,
    nextSlice,
    prevSlice,
    toggleLayer,
    setOpacity,
    setTotalSlices,
    canvasRef,
  };
}
