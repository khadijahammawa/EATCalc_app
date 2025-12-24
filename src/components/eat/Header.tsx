import { Heart, Info } from 'lucide-react';
import { Button } from '@/components/ui/button';
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from '@/components/ui/tooltip';

export function Header() {
  return (
    <header className="flex items-center justify-between px-6 py-4 border-b border-border bg-card">
      <div className="flex items-center gap-3">
        <div className="flex items-center justify-center w-10 h-10 rounded-xl bg-primary/10">
          <Heart className="h-5 w-5 text-primary" />
        </div>
        <div>
          <h1 className="text-lg font-semibold text-foreground tracking-tight">
            EAT Calculator
          </h1>
          <p className="text-xs text-muted-foreground">
            Epicardial Adipose Tissue Quantification
          </p>
        </div>
      </div>

      <Tooltip>
        <TooltipTrigger asChild>
          <Button variant="ghost" size="icon" className="h-9 w-9">
            <Info className="h-4 w-4" />
          </Button>
        </TooltipTrigger>
        <TooltipContent side="bottom" align="end" className="max-w-xs">
          <p className="text-sm">
            This tool uses TotalSegmentator for pericardium segmentation and calculates
            epicardial adipose tissue volume using Hounsfield Unit thresholding.
          </p>
        </TooltipContent>
      </Tooltip>
    </header>
  );
}
