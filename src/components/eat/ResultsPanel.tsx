import { Heart, Activity, BarChart3, Copy, Download } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Separator } from '@/components/ui/separator';
import type { AnalysisResults } from '@/types/eat';
import { toast } from 'sonner';

interface ResultsPanelProps {
  results: AnalysisResults | null;
}

export function ResultsPanel({ results }: ResultsPanelProps) {
  if (!results) {
    return (
      <div className="flex flex-col items-center justify-center py-8 text-center">
        <div className="w-12 h-12 rounded-full bg-muted flex items-center justify-center mb-3">
          <Heart className="h-6 w-6 text-muted-foreground" />
        </div>
        <p className="text-sm text-muted-foreground">
          Run an analysis to see results
        </p>
      </div>
    );
  }

  const handleCopyResults = () => {
    const text = `EAT Analysis Results
Volume: ${results.eatVolume.toFixed(1)} mL
Mean HU: ${results.meanHU.toFixed(1)}
Std HU: ${results.stdHU.toFixed(1)}
Voxel Size: ${results.voxelZoom.map(v => v.toFixed(2)).join(' × ')} mm`;
    
    navigator.clipboard.writeText(text);
    toast.success('Results copied to clipboard');
  };

  const handleExportCSV = () => {
    const csv = `Metric,Value,Unit
EAT Volume,${results.eatVolume.toFixed(2)},mL
Mean HU,${results.meanHU.toFixed(2)},HU
Std HU,${results.stdHU.toFixed(2)},HU
Voxel X,${results.voxelZoom[0].toFixed(3)},mm
Voxel Y,${results.voxelZoom[1].toFixed(3)},mm
Voxel Z,${results.voxelZoom[2].toFixed(3)},mm
Total Slices,${results.totalSlices},`;

    const blob = new Blob([csv], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'eat_results.csv';
    a.click();
    URL.revokeObjectURL(url);
    toast.success('Results exported as CSV');
  };

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Primary Metric - EAT Volume */}
      <div className="text-center py-4 px-3 rounded-xl bg-primary/5 border border-primary/10">
        <div className="flex items-center justify-center gap-2 mb-1">
          <Heart className="h-5 w-5 text-primary" />
          <span className="text-sm font-medium text-primary uppercase tracking-wide">
            EAT Volume
          </span>
        </div>
        <p className="metric-value text-4xl text-primary">
          {results.eatVolume.toFixed(1)}
          <span className="text-lg font-normal text-primary/70 ml-1">mL</span>
        </p>
      </div>

      {/* Secondary Metrics */}
      <div className="grid grid-cols-2 gap-4">
        <MetricCard
          icon={<Activity className="h-4 w-4" />}
          label="Mean HU"
          value={results.meanHU.toFixed(1)}
          unit="HU"
        />
        <MetricCard
          icon={<BarChart3 className="h-4 w-4" />}
          label="Std HU"
          value={results.stdHU.toFixed(1)}
          unit="HU"
        />
      </div>

      <Separator />

      {/* Voxel Information */}
      <div className="space-y-2">
        <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
          Voxel Resolution
        </p>
        <p className="text-sm font-mono text-foreground">
          {results.voxelZoom.map(v => v.toFixed(2)).join(' × ')} mm
        </p>
        <p className="text-xs text-muted-foreground">
          {results.totalSlices} slices
        </p>
      </div>

      <Separator />

      {/* Export Options */}
      <div className="flex gap-2">
        <Button
          variant="outline"
          size="sm"
          className="flex-1"
          onClick={handleCopyResults}
        >
          <Copy className="h-3.5 w-3.5 mr-1.5" />
          Copy
        </Button>
        <Button
          variant="outline"
          size="sm"
          className="flex-1"
          onClick={handleExportCSV}
        >
          <Download className="h-3.5 w-3.5 mr-1.5" />
          CSV
        </Button>
      </div>
    </div>
  );
}

interface MetricCardProps {
  icon: React.ReactNode;
  label: string;
  value: string;
  unit: string;
}

function MetricCard({ icon, label, value, unit }: MetricCardProps) {
  return (
    <div className="p-3 rounded-lg bg-muted/50 border border-border">
      <div className="flex items-center gap-1.5 text-muted-foreground mb-1">
        {icon}
        <span className="text-xs font-medium uppercase tracking-wide">{label}</span>
      </div>
      <p className="text-xl font-semibold text-foreground">
        {value}
        <span className="text-sm font-normal text-muted-foreground ml-1">{unit}</span>
      </p>
    </div>
  );
}
