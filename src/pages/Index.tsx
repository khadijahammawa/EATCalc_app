import { Header } from '@/components/eat/Header';
import { InputPanel } from '@/components/eat/InputPanel';
import { ResultsPanel } from '@/components/eat/ResultsPanel';
import { AxialViewer } from '@/components/eat/AxialViewer';
import { StatusBar } from '@/components/eat/StatusBar';
import { useEATAnalysis } from '@/hooks/useEATAnalysis';
import { useSliceViewer } from '@/hooks/useSliceViewer';
import { useEffect } from 'react';
import { Separator } from '@/components/ui/separator';
import { ResizableHandle, ResizablePanel, ResizablePanelGroup } from '@/components/ui/resizable';

const Index = () => {
  const { results, batchResults, progress, isProcessing, startAnalysis, startBatchAnalysis, resetAnalysis } = useEATAnalysis();
  const { viewerState, setSlice, nextSlice, prevSlice, onWheelDelta, toggleLayer, setOpacity, rotateLeft, rotateRight, setTotalSlices, setAnalysisId, canvasRef } = useSliceViewer();

  useEffect(() => {
    if (results) {
      setTotalSlices(results.totalSlices);
      setAnalysisId(results.analysisId ?? null);
    } else {
      setAnalysisId(null);
    }
  }, [results, batchResults, setAnalysisId, setTotalSlices]);

  const hasData = results !== null;
  const hasResults = results !== null || batchResults !== null;

  return (
    <div className="min-h-screen flex flex-col bg-background">
      <Header />
      <ResizablePanelGroup className="flex-1" direction="horizontal" autoSaveId="eat-layout">
        <ResizablePanel defaultSize={28} minSize={20} maxSize={45} className="min-w-[16rem]">
          <aside className="h-full border-r border-border bg-card overflow-y-auto">
            <div className="p-5">
              <InputPanel
                onStartAnalysis={startAnalysis}
                onStartBatchAnalysis={startBatchAnalysis}
                onReset={resetAnalysis}
                isProcessing={isProcessing}
                hasResults={hasResults}
              />
            </div>
            <Separator />
            <div className="p-5">
              <h3 className="text-sm font-semibold text-foreground uppercase tracking-wide mb-4">Results</h3>
              <ResultsPanel results={results} batchResults={batchResults} />
            </div>
          </aside>
        </ResizablePanel>
        <ResizableHandle withHandle />
        <ResizablePanel minSize={40} className="min-w-0">
          <main className="h-full flex flex-col overflow-hidden bg-muted/20">
            <AxialViewer viewerState={viewerState} canvasRef={canvasRef} onSliceChange={setSlice} onNextSlice={nextSlice} onPrevSlice={prevSlice} onWheelDelta={onWheelDelta} onToggleLayer={toggleLayer} onOpacityChange={setOpacity} onRotateLeft={rotateLeft} onRotateRight={rotateRight} hasData={hasData} />
          </main>
        </ResizablePanel>
      </ResizablePanelGroup>
      <StatusBar progress={progress} />
    </div>
  );
};

export default Index;
