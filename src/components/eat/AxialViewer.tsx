import { useEffect, useRef } from 'react';
import { Eye, EyeOff, ChevronLeft, ChevronRight } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Slider } from '@/components/ui/slider';
import { Checkbox } from '@/components/ui/checkbox';
import { Label } from '@/components/ui/label';
import type { ViewerState } from '@/types/eat';

interface AxialViewerProps {
  viewerState: ViewerState;
  canvasRef: React.RefObject<HTMLCanvasElement>;
  onSliceChange: (slice: number) => void;
  onNextSlice: () => void;
  onPrevSlice: () => void;
  onToggleLayer: (layer: 'ct' | 'eat' | 'pericardium') => void;
  onOpacityChange: (opacity: number) => void;
  hasData: boolean;
}

export function AxialViewer({
  viewerState,
  canvasRef,
  onSliceChange,
  onNextSlice,
  onPrevSlice,
  onToggleLayer,
  onOpacityChange,
  hasData,
}: AxialViewerProps) {
  const containerRef = useRef<HTMLDivElement>(null);

  // Handle mouse wheel for slice navigation
  useEffect(() => {
    const container = containerRef.current;
    if (!container || !hasData) return;

    const handleWheel = (e: WheelEvent) => {
      e.preventDefault();
      if (e.deltaY < 0) {
        onPrevSlice();
      } else {
        onNextSlice();
      }
    };

    container.addEventListener('wheel', handleWheel, { passive: false });
    return () => container.removeEventListener('wheel', handleWheel);
  }, [hasData, onNextSlice, onPrevSlice]);

  // Handle keyboard navigation
  useEffect(() => {
    if (!hasData) return;

    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'ArrowUp' || e.key === 'ArrowLeft') {
        e.preventDefault();
        onPrevSlice();
      } else if (e.key === 'ArrowDown' || e.key === 'ArrowRight') {
        e.preventDefault();
        onNextSlice();
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [hasData, onNextSlice, onPrevSlice]);

  return (
    <div className="flex flex-col h-full">
      {/* Toolbar */}
      <div className="flex items-center justify-between p-3 border-b border-border bg-card">
        <div className="flex items-center gap-4">
          {/* Layer toggles */}
          <LayerToggle
            checked={viewerState.showCT}
            onChange={() => onToggleLayer('ct')}
            label="CT"
            color="bg-muted-foreground"
          />
          <LayerToggle
            checked={viewerState.showEAT}
            onChange={() => onToggleLayer('eat')}
            label="EAT"
            color="bg-destructive"
          />
          <LayerToggle
            checked={viewerState.showPericardium}
            onChange={() => onToggleLayer('pericardium')}
            label="Pericardium"
            color="bg-success"
          />
        </div>

        {/* Opacity control */}
        <div className="flex items-center gap-3">
          <Label className="text-xs text-muted-foreground">Overlay</Label>
          <Slider
            value={[viewerState.overlayOpacity * 100]}
            onValueChange={([v]) => onOpacityChange(v / 100)}
            max={100}
            step={5}
            className="w-24"
          />
          <span className="text-xs font-mono text-muted-foreground w-8">
            {Math.round(viewerState.overlayOpacity * 100)}%
          </span>
        </div>
      </div>

      {/* Canvas Area */}
      <div 
        ref={containerRef}
        className="flex-1 flex items-center justify-center p-4 bg-muted/30 overflow-hidden"
      >
        {hasData ? (
          <div className="relative">
            <canvas
              ref={canvasRef}
              width={512}
              height={512}
              className="rounded-lg shadow-lg border border-border max-w-full max-h-full object-contain"
              style={{ imageRendering: 'pixelated' }}
            />
            
            {/* Slice indicator overlay */}
            <div className="absolute top-3 left-3 px-2 py-1 rounded bg-foreground/80 text-background text-xs font-mono">
              Slice {viewerState.currentSlice + 1} / {viewerState.totalSlices}
            </div>

            {/* Legend */}
            <div className="absolute bottom-3 right-3 flex flex-col gap-1 px-2 py-1.5 rounded bg-foreground/80 text-xs">
              {viewerState.showEAT && (
                <div className="flex items-center gap-2">
                  <div className="w-3 h-3 rounded-sm bg-destructive" />
                  <span className="text-background">EAT</span>
                </div>
              )}
              {viewerState.showPericardium && (
                <div className="flex items-center gap-2">
                  <div className="w-3 h-3 rounded-sm bg-success" />
                  <span className="text-background">Pericardium</span>
                </div>
              )}
            </div>
          </div>
        ) : (
          <div className="text-center text-muted-foreground">
            <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-muted flex items-center justify-center">
              <Eye className="h-8 w-8" />
            </div>
            <p className="text-sm font-medium">No image loaded</p>
            <p className="text-xs mt-1">Run an analysis to view slices</p>
          </div>
        )}
      </div>

      {/* Slice Navigation */}
      <div className="p-3 border-t border-border bg-card">
        <div className="flex items-center gap-3">
          <Button
            variant="outline"
            size="icon"
            className="h-8 w-8"
            onClick={onPrevSlice}
            disabled={!hasData || viewerState.currentSlice === 0}
          >
            <ChevronLeft className="h-4 w-4" />
          </Button>
          
          <Slider
            value={[viewerState.currentSlice]}
            onValueChange={([v]) => onSliceChange(v)}
            max={viewerState.totalSlices - 1}
            step={1}
            disabled={!hasData}
            className="flex-1"
          />
          
          <Button
            variant="outline"
            size="icon"
            className="h-8 w-8"
            onClick={onNextSlice}
            disabled={!hasData || viewerState.currentSlice === viewerState.totalSlices - 1}
          >
            <ChevronRight className="h-4 w-4" />
          </Button>
        </div>
        
        <p className="text-center text-xs text-muted-foreground mt-2">
          Use scroll wheel or arrow keys to navigate
        </p>
      </div>
    </div>
  );
}

interface LayerToggleProps {
  checked: boolean;
  onChange: () => void;
  label: string;
  color: string;
}

function LayerToggle({ checked, onChange, label, color }: LayerToggleProps) {
  return (
    <div className="flex items-center gap-2">
      <Checkbox
        id={`layer-${label}`}
        checked={checked}
        onCheckedChange={onChange}
        className="data-[state=checked]:bg-primary"
      />
      <div className={`w-2.5 h-2.5 rounded-sm ${color}`} />
      <Label
        htmlFor={`layer-${label}`}
        className="text-sm font-medium cursor-pointer"
      >
        {label}
      </Label>
    </div>
  );
}
