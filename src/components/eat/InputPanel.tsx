import { useState } from 'react';
import { Upload, Folder, Play, RotateCcw, Cpu, Zap } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Checkbox } from '@/components/ui/checkbox';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import type { AnalysisParams, BatchAnalysisParams } from '@/types/eat';

interface InputPanelProps {
  onStartAnalysis: (params: AnalysisParams) => void;
  onStartBatchAnalysis: (params: BatchAnalysisParams) => void;
  onReset: () => void;
  isProcessing: boolean;
  hasResults: boolean;
}

export function InputPanel({
  onStartAnalysis,
  onStartBatchAnalysis,
  onReset,
  isProcessing,
  hasResults,
}: InputPanelProps) {
  const [inputFile, setInputFile] = useState<File | null>(null);
  const [inputFiles, setInputFiles] = useState<File[]>([]);
  const [outputPath, setOutputPath] = useState('./output');
  const [huLow, setHuLow] = useState(-190);
  const [huHigh, setHuHigh] = useState(-30);
  const [device, setDevice] = useState<'cpu' | 'gpu'>('cpu');
  const [saveEATMask, setSaveEATMask] = useState(false);
  const [isBatch, setIsBatch] = useState(false);
  const [fileInputKey, setFileInputKey] = useState(0);

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(e.target.files ?? []);
    if (isBatch) {
      setInputFiles(files);
      setInputFile(null);
      return;
    }
    const file = files[0];
    if (file) {
      setInputFile(file);
      setInputFiles([]);
    }
  };

  const handleSubmit = () => {
    if (isBatch) {
      onStartBatchAnalysis({
        inputFiles,
        outputPath,
        huLow,
        huHigh,
        device,
        saveEATMask,
      });
    } else {
      onStartAnalysis({
        inputFile,
        outputPath,
        huLow,
        huHigh,
        device,
        saveEATMask,
      });
    }
  };

  const isValid = isBatch ? inputFiles.length > 0 : inputFile !== null;
  const fileLabel = isBatch
    ? inputFiles.length > 0
      ? `${inputFiles.length} files selected`
      : 'Select CT scans...'
    : inputFile
      ? inputFile.name
      : 'Select CT scan...';

  const handleBatchToggle = (checked: boolean) => {
    setIsBatch(checked);
    setInputFile(null);
    setInputFiles([]);
    setFileInputKey(prev => prev + 1);
  };

  return (
    <div className="space-y-6">
      {/* File Input Section */}
      <div className="space-y-4">
        <h3 className="text-sm font-semibold text-foreground uppercase tracking-wide">
          Input
        </h3>

        <div className="flex items-center gap-2">
          <Checkbox
            id="batch-mode"
            checked={isBatch}
            onCheckedChange={(checked) => handleBatchToggle(checked === true)}
            disabled={isProcessing}
          />
          <Label htmlFor="batch-mode" className="text-sm text-muted-foreground">
            Batch mode (multiple NIfTI files)
          </Label>
        </div>
        
        <div className="space-y-2">
          <Label htmlFor="ct-file" className="text-sm text-muted-foreground">
            {isBatch ? 'CT Scans (NIfTI)' : 'CT Scan (NIfTI)'}
          </Label>
          <div className="relative">
            <Input
              key={fileInputKey}
              id="ct-file"
              type="file"
              accept=".nii,.nii.gz"
              multiple={isBatch}
              onChange={handleFileSelect}
              className="hidden"
            />
            <Button
              variant="outline"
              className="w-full justify-start text-left font-normal h-10"
              onClick={() => document.getElementById('ct-file')?.click()}
              disabled={isProcessing}
            >
              <Upload className="mr-2 h-4 w-4 text-muted-foreground" />
              <span className="truncate">
                {fileLabel}
              </span>
            </Button>
          </div>
        </div>

        <div className="space-y-2">
          <Label htmlFor="output-path" className="text-sm text-muted-foreground">
            Output Folder
          </Label>
          <div className="relative">
            <Folder className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
            <Input
              id="output-path"
              value={outputPath}
              onChange={(e) => setOutputPath(e.target.value)}
              className="pl-9"
              placeholder="./output"
              disabled={isProcessing}
            />
          </div>
        </div>

        <div className="space-y-2">
          <div className="flex items-center space-x-2">
            <Checkbox
              id="save-eat-mask"
              checked={saveEATMask}
              onCheckedChange={(checked) => setSaveEATMask(checked === true)}
              disabled={isProcessing}
            />
            <Label htmlFor="save-eat-mask" className="text-sm text-muted-foreground">
              Save EAT mask (NIfTI)
            </Label>
          </div>
          <p className="text-xs text-muted-foreground">
            Outputs EAT_mask_{'{'}hu_low{'}'}_{'{'}hu_high{'}'}.nii.gz to the output folder.
          </p>
        </div>
      </div>

      {/* Threshold Section */}
      <div className="space-y-4">
        <h3 className="text-sm font-semibold text-foreground uppercase tracking-wide">
          HU Thresholds
        </h3>
        
        <div className="grid grid-cols-2 gap-3">
          <div className="space-y-2">
            <Label htmlFor="hu-low" className="text-sm text-muted-foreground">
              Low (HU)
            </Label>
            <Input
              id="hu-low"
              type="number"
              value={huLow}
              onChange={(e) => setHuLow(Number(e.target.value))}
              className="font-mono"
              disabled={isProcessing}
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="hu-high" className="text-sm text-muted-foreground">
              High (HU)
            </Label>
            <Input
              id="hu-high"
              type="number"
              value={huHigh}
              onChange={(e) => setHuHigh(Number(e.target.value))}
              className="font-mono"
              disabled={isProcessing}
            />
          </div>
        </div>
        
        <p className="text-xs text-muted-foreground">
          Standard adipose tissue range: -190 to -30 HU
        </p>
      </div>

      {/* Device Selection */}
      <div className="space-y-4">
        <h3 className="text-sm font-semibold text-foreground uppercase tracking-wide">
          Processing
        </h3>
        
        <div className="space-y-2">
          <Label htmlFor="device" className="text-sm text-muted-foreground">
            Device
          </Label>
          <Select 
            value={device} 
            onValueChange={(v) => setDevice(v as 'cpu' | 'gpu')}
            disabled={isProcessing}
          >
            <SelectTrigger>
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="cpu">
                <div className="flex items-center gap-2">
                  <Cpu className="h-4 w-4" />
                  <span>CPU</span>
                </div>
              </SelectItem>
              <SelectItem value="gpu">
                <div className="flex items-center gap-2">
                  <Zap className="h-4 w-4" />
                  <span>GPU (CUDA)</span>
                </div>
              </SelectItem>
            </SelectContent>
          </Select>
        </div>
      </div>

      {/* Action Buttons */}
      <div className="space-y-3 pt-2">
        <Button
          onClick={handleSubmit}
          disabled={!isValid || isProcessing}
          className="w-full h-11 text-base font-medium"
        >
          {isProcessing ? (
            <>
              <div className="mr-2 h-4 w-4 animate-spin rounded-full border-2 border-current border-t-transparent" />
              Processing...
            </>
          ) : (
            <>
              <Play className="mr-2 h-4 w-4" />
              {isBatch ? 'Run Batch' : 'Run Analysis'}
            </>
          )}
        </Button>

        {hasResults && (
          <Button
            variant="ghost"
            onClick={onReset}
            disabled={isProcessing}
            className="w-full"
          >
            <RotateCcw className="mr-2 h-4 w-4" />
            New Analysis
          </Button>
        )}
      </div>
    </div>
  );
}
