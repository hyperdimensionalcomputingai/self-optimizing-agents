import React, { useState } from 'react';
import ChatContainer from './components/ChatContainer';
import DebugSidebar from './components/DebugSidebar';
import GraphVisualizationSidebar from './components/GraphVisualizationSidebar';
import './App.css';

type SidebarType = 'debug' | 'graph' | null;

function App() {
  const [vectorAnswer, setVectorAnswer] = useState<string>('');
  const [graphAnswer, setGraphAnswer] = useState<string>('');
  const [graphData, setGraphData] = useState<any>(null);
  const [activeSidebar, setActiveSidebar] = useState<SidebarType>(null);

  const handleDebugDataUpdate = (vectorAnswer: string, graphAnswer: string, graphData?: any) => {
    setVectorAnswer(vectorAnswer);
    setGraphAnswer(graphAnswer);

    // Only use dedicated graph_data parameter for visualization
    if (graphData) {
      if (Array.isArray(graphData)) {
        setGraphData(graphData);
      } else if (graphData.nodes && graphData.edges) {
        setGraphData(graphData);
      } else {
        setGraphData(null);
      }
    } else {
      setGraphData(null);
    }
  };

  const handleSidebarToggle = (sidebarType: SidebarType) => {
    setActiveSidebar(activeSidebar === sidebarType ? null : sidebarType);
  };

  return (
    <div className="App">
      <DebugSidebar
        vectorAnswer={vectorAnswer}
        graphAnswer={graphAnswer}
        isOpen={activeSidebar === 'debug'}
        onToggle={() => handleSidebarToggle('debug')}
      />
      <GraphVisualizationSidebar
        graphData={graphData}
        isOpen={activeSidebar === 'graph'}
        onToggle={() => handleSidebarToggle('graph')}
      />
      <header className="app-header">
        <h1>Self-Optimizing Agents</h1>
      </header>
      <main>
        <ChatContainer onDebugDataUpdate={handleDebugDataUpdate} />
      </main>
    </div>
  );
}

export default App;
