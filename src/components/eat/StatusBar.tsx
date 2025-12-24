import { CheckCircle2, AlertCircle, Loader2, Clock } from 'lucide-react';
import { Progress } from '@/components/ui/progress';
import type { AnalysisProgress, AnalysisStatus } from '@/types/eat';
import { cn } from '@/lib/utils';

interface StatusBarProps {
  progress: AnalysisProgress;
}

const statusConfig: Record<AnalysisStatus, { 
  icon: typeof CheckCircle2; 
  color: string;
  bgColor: string;
}> = {
  idle: { icon: Clock, color: 'text-muted-foreground', bgColor: 'bg-muted' },
  uploading: { icon: Loader2, color: 'text-primary', bgColor: 'bg-primary/10' },
  segmenting: { icon: Loader2, color: 'text-primary', bgColor: 'bg-primary/10' },
  calculating: { icon: Loader2, color: 'text-primary', bgColor: 'bg-primary/10' },
  complete: { icon: CheckCircle2, color: 'text-success', bgColor: 'bg-success/10' },
  error: { icon: AlertCircle, color: 'text-destructive', bgColor: 'bg-destructive/10' },
};

export function StatusBar({ progress }: StatusBarProps) {
  const config = statusConfig[progress.status];
  const Icon = config.icon;
  const isProcessing = ['uploading', 'segmenting', 'calculating'].includes(progress.status);

  return (
    <div className={cn(
      "flex items-center gap-4 px-4 py-3 border-t border-border transition-colors",
      config.bgColor
    )}>
      <div className="flex items-center gap-2 min-w-0">
        <Icon 
          className={cn(
            "h-4 w-4 flex-shrink-0",
            config.color,
            isProcessing && "animate-spin"
          )} 
        />
        <span className={cn(
          "text-sm font-medium truncate",
          config.color
        )}>
          {progress.message}
        </span>
      </div>

      {isProcessing && (
        <div className="flex-1 flex items-center gap-3 max-w-md">
          <Progress 
            value={progress.progress} 
            className="h-2 flex-1"
          />
          <span className="text-xs font-mono text-muted-foreground w-8 text-right">
            {progress.progress}%
          </span>
        </div>
      )}

      {progress.status === 'complete' && (
        <span className="text-xs text-success font-medium ml-auto">
          ✓ Complete
        </span>
      )}
    </div>
  );
}
