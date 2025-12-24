import { useState, useCallback, useRef, useEffect } from 'react';
import type { ViewerState } from '@/types/eat';

interface UseSliceViewerReturn {
  viewerState: ViewerState;
  setSlice: (slice: number) => void;
  nextSlice: () => void;
  prevSlice: () => void;
  toggleLayer: (layer: 'ct' | 'eat' | 'pericardium') => void;
  setOpacity: (opacity: number) => void;
  rotateLeft: () => void;
  rotateRight: () => void;
  setTotalSlices: (total: number) => void;
  setAnalysisId: (analysisId: string | null) => void;
  canvasRef: React.RefObject<HTMLCanvasElement>;
}

interface SliceImagesResponse {
  ctPng: string;
  eatPng: string;
  pericardiumPng: string;
  slice: number;
  totalSlices: number;
}

type SliceImageSet = {
  ct: HTMLImageElement;
  eat: HTMLImageElement;
  pericardium: HTMLImageElement;
};

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';
const SLICE_CACHE_LIMIT = 40;

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

function loadImage(src: string): Promise<HTMLImageElement> {
  return new Promise((resolve, reject) => {
    const img = new Image();
    img.onload = () => resolve(img);
    img.onerror = () => reject(new Error('Failed to load slice image'));
    img.src = src;
  });
}

function drawRotatedImage(
  ctx: CanvasRenderingContext2D,
  img: HTMLImageElement,
  rotation: number,
  width: number,
  height: number
) {
  if (rotation % 360 === 0) {
    ctx.drawImage(img, 0, 0, width, height);
    return;
  }

  const angle = (rotation * Math.PI) / 180;
  const drawWidth = rotation % 180 === 0 ? width : height;
  const drawHeight = rotation % 180 === 0 ? height : width;

  ctx.save();
  ctx.translate(width / 2, height / 2);
  ctx.rotate(angle);
  ctx.drawImage(img, -drawWidth / 2, -drawHeight / 2, drawWidth, drawHeight);
  ctx.restore();
}

export function useSliceViewer(initialTotalSlices = 120): UseSliceViewerReturn {
  const [viewerState, setViewerState] = useState<ViewerState>({
    currentSlice: Math.floor(initialTotalSlices / 2),
    totalSlices: initialTotalSlices,
    showCT: true,
    showEAT: true,
    showPericardium: true,
    overlayOpacity: 0.7,
    rotation: 0,
  });
  const [analysisId, setAnalysisId] = useState<string | null>(null);
  const [sliceImages, setSliceImages] = useState<{
    sliceIndex: number;
  } & SliceImageSet | null>(null);

  const canvasRef = useRef<HTMLCanvasElement>(null);
  const fetchControllerRef = useRef<AbortController | null>(null);
  const sliceCacheRef = useRef<Map<number, SliceImageSet>>(new Map());

  const loadSliceImages = useCallback(async (sliceIndex: number) => {
    if (!analysisId) {
      setSliceImages(null);
      return;
    }

    const cache = sliceCacheRef.current;
    const cached = cache.get(sliceIndex);
    if (cached) {
      cache.delete(sliceIndex);
      cache.set(sliceIndex, cached);
      setSliceImages({ sliceIndex, ...cached });
      return;
    }

    if (fetchControllerRef.current) {
      fetchControllerRef.current.abort();
    }
    const controller = new AbortController();
    fetchControllerRef.current = controller;

    try {
      const response = await fetch(
        `${API_BASE_URL}/api/slice?analysis_id=${encodeURIComponent(analysisId)}&slice=${sliceIndex}`,
        { signal: controller.signal }
      );
      if (!response.ok) {
        throw new Error('Failed to fetch slice data');
      }

      const data = (await response.json()) as SliceImagesResponse;
      const [ct, eat, pericardium] = await Promise.all([
        loadImage(data.ctPng),
        loadImage(data.eatPng),
        loadImage(data.pericardiumPng),
      ]);

      if (!controller.signal.aborted) {
        const sliceSet = { ct, eat, pericardium };
        cache.delete(sliceIndex);
        cache.set(sliceIndex, sliceSet);
        while (cache.size > SLICE_CACHE_LIMIT) {
          const oldestKey = cache.keys().next().value;
          cache.delete(oldestKey);
        }
        setSliceImages({ sliceIndex, ...sliceSet });
      }
    } catch (error) {
      if (!(error instanceof DOMException && error.name === 'AbortError')) {
        setSliceImages(null);
      }
    }
  }, [analysisId]);

  useEffect(() => {
    void loadSliceImages(viewerState.currentSlice);
  }, [loadSliceImages, viewerState.currentSlice]);

  const drawSliceImages = useCallback(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    ctx.clearRect(0, 0, canvas.width, canvas.height);
    const rotation = ((viewerState.rotation % 360) + 360) % 360;

    if (analysisId) {
      if (!sliceImages || sliceImages.sliceIndex !== viewerState.currentSlice) {
        ctx.fillStyle = '#0a0a0a';
        ctx.fillRect(0, 0, canvas.width, canvas.height);
        return;
      }
    } else {
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
      return;
    }

    if (viewerState.showCT) {
      drawRotatedImage(ctx, sliceImages.ct, rotation, canvas.width, canvas.height);
    }
    if (viewerState.showPericardium) {
      ctx.globalAlpha = viewerState.overlayOpacity;
      drawRotatedImage(ctx, sliceImages.pericardium, rotation, canvas.width, canvas.height);
      ctx.globalAlpha = 1;
    }
    if (viewerState.showEAT) {
      ctx.globalAlpha = viewerState.overlayOpacity;
      drawRotatedImage(ctx, sliceImages.eat, rotation, canvas.width, canvas.height);
      ctx.globalAlpha = 1;
    }
  }, [analysisId, sliceImages, viewerState]);

  // Render the current slice
  useEffect(() => {
    drawSliceImages();
  }, [drawSliceImages]);

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

  const rotateLeft = useCallback(() => {
    setViewerState(prev => ({
      ...prev,
      rotation: (prev.rotation + 270) % 360,
    }));
  }, []);

  const rotateRight = useCallback(() => {
    setViewerState(prev => ({
      ...prev,
      rotation: (prev.rotation + 90) % 360,
    }));
  }, []);

  const setTotalSlices = useCallback((total: number) => {
    setViewerState(prev => ({
      ...prev,
      totalSlices: total,
      currentSlice: Math.min(prev.currentSlice, total - 1),
    }));
  }, []);

  const setAnalysisIdSafe = useCallback((nextAnalysisId: string | null) => {
    setAnalysisId(nextAnalysisId);
    setSliceImages(null);
    sliceCacheRef.current.clear();
    if (fetchControllerRef.current) {
      fetchControllerRef.current.abort();
      fetchControllerRef.current = null;
    }
  }, []);

  return {
    viewerState,
    setSlice,
    nextSlice,
    prevSlice,
    toggleLayer,
    setOpacity,
    rotateLeft,
    rotateRight,
    setTotalSlices,
    setAnalysisId: setAnalysisIdSafe,
    canvasRef,
  };
}
