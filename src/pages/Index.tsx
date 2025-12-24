import { Header } from '@/components/eat/Header';
import { InputPanel } from '@/components/eat/InputPanel';
import { ResultsPanel } from '@/components/eat/ResultsPanel';
import { AxialViewer } from '@/components/eat/AxialViewer';
import { StatusBar } from '@/components/eat/StatusBar';
import { useEATAnalysis } from '@/hooks/useEATAnalysis';
import { useSliceViewer } from '@/hooks/useSliceViewer';
import { useEffect } from 'react';
import { Separator } from '@/components/ui/separator';

const Index = () => {
  const { results, progress, isProcessing, startAnalysis, resetAnalysis } = useEATAnalysis();
  const { viewerState, setSlice, nextSlice, prevSlice, toggleLayer, setOpacity, rotateLeft, rotateRight, setTotalSlices, setAnalysisId, canvasRef } = useSliceViewer();

  useEffect(() => {
    if (results) {
      setTotalSlices(results.totalSlices);
      setAnalysisId(results.analysisId ?? null);
    } else {
      setAnalysisId(null);
    }
  }, [results, setAnalysisId, setTotalSlices]);

  const hasData = results !== null;

  return (
    <div className="min-h-screen flex flex-col bg-background">
      <Header />
      <div className="flex-1 flex overflow-hidden">
        <aside className="w-80 flex-shrink-0 border-r border-border bg-card overflow-y-auto">
          <div className="p-5">
            <InputPanel onStartAnalysis={startAnalysis} onReset={resetAnalysis} isProcessing={isProcessing} hasResults={hasData} />
          </div>
          <Separator />
          <div className="p-5">
            <h3 className="text-sm font-semibold text-foreground uppercase tracking-wide mb-4">Results</h3>
            <ResultsPanel results={results} />
          </div>
        </aside>
        <main className="flex-1 flex flex-col overflow-hidden bg-muted/20">
          <AxialViewer viewerState={viewerState} canvasRef={canvasRef} onSliceChange={setSlice} onNextSlice={nextSlice} onPrevSlice={prevSlice} onToggleLayer={toggleLayer} onOpacityChange={setOpacity} onRotateLeft={rotateLeft} onRotateRight={rotateRight} hasData={hasData} />
        </main>
      </div>
      <StatusBar progress={progress} />
    </div>
  );
};

export default Index;
