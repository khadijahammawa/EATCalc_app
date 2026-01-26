// EAT Calculator Types

export interface AnalysisParams {
  inputFile: File | null;
  outputPath: string;
  huLow: number;
  huHigh: number;
  device: 'cpu' | 'gpu';
  saveEATMask: boolean;
}

export interface AnalysisResults {
  eatVolume: number; // in mL
  meanHU: number;
  stdHU: number;
  voxelZoom: [number, number, number];
  totalSlices: number;
  outputPath: string;
  analysisId?: string;
  statsCsv?: string;
}

export interface SliceData {
  ct: ImageData | null;
  eatMask: ImageData | null;
  pericardium: ImageData | null;
}

export interface ViewerState {
  currentSlice: number;
  totalSlices: number;
  showCT: boolean;
  showEAT: boolean;
  showPericardium: boolean;
  overlayOpacity: number;
  rotation: number;
}

export type AnalysisStatus = 
  | 'idle'
  | 'uploading'
  | 'segmenting'
  | 'calculating'
  | 'complete'
  | 'error';

export interface AnalysisProgress {
  status: AnalysisStatus;
  message: string;
  progress: number; // 0-100
}

// API Response types
export interface AnalysisResponse {
  success: boolean;
  results?: AnalysisResults;
  error?: string;
}

export interface SliceResponse {
  success: boolean;
  sliceData?: SliceData;
  error?: string;
}
