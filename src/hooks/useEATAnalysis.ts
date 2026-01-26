import { useState, useCallback } from 'react';
import type {
  AnalysisParams,
  AnalysisResults,
  AnalysisProgress,
  AnalysisResponse,
  AnalysisStatus,
} from '@/types/eat';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

interface UseEATAnalysisReturn {
  results: AnalysisResults | null;
  progress: AnalysisProgress;
  isProcessing: boolean;
  startAnalysis: (params: AnalysisParams) => Promise<void>;
  resetAnalysis: () => void;
}

export function useEATAnalysis(): UseEATAnalysisReturn {
  const [results, setResults] = useState<AnalysisResults | null>(null);
  const [progress, setProgress] = useState<AnalysisProgress>({
    status: 'idle',
    message: 'Ready to analyze',
    progress: 0,
  });

  const isProcessing = ['uploading', 'segmenting', 'calculating'].includes(progress.status);

  const updateProgress = (status: AnalysisStatus, message: string, progressValue: number) => {
    setProgress({ status, message, progress: progressValue });
  };

  const startAnalysis = useCallback(async (params: AnalysisParams) => {
    if (!params.inputFile) {
      updateProgress('error', 'No input file selected', 0);
      return;
    }

    try {
      updateProgress('uploading', 'Uploading CT scan...', 10);
      const formData = new FormData();
      formData.append('file', params.inputFile);
      if (params.outputPath) {
        formData.append('output_path', params.outputPath);
      }
      formData.append('hu_low', params.huLow.toString());
      formData.append('hu_high', params.huHigh.toString());
      formData.append('device', params.device);
      formData.append('save_eat_mask', params.saveEATMask ? 'true' : 'false');

      updateProgress('segmenting', 'Running analysis...', 35);
      const response = await fetch(`${API_BASE_URL}/api/analyze`, {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        let detail = 'Analysis failed';
        try {
          const payload = (await response.json()) as { detail?: string };
          if (payload.detail) {
            detail = payload.detail;
          }
        } catch {
          // ignore JSON parsing errors
        }
        throw new Error(detail);
      }

      updateProgress('calculating', 'Finalizing results...', 85);
      const data = (await response.json()) as AnalysisResponse;
      if (!data.success || !data.results) {
        throw new Error(data.error || 'Analysis failed');
      }

      setResults(data.results as AnalysisResults);
      updateProgress('complete', 'Analysis complete', 100);
    } catch (error) {
      updateProgress('error', error instanceof Error ? error.message : 'Analysis failed', 0);
    }
  }, []);

  const resetAnalysis = useCallback(() => {
    setResults(null);
    updateProgress('idle', 'Ready to analyze', 0);
  }, []);

  return {
    results,
    progress,
    isProcessing,
    startAnalysis,
    resetAnalysis,
  };
}
