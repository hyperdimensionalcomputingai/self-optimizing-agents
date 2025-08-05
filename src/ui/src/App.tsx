import React, { useState } from 'react';
import ChatContainer from './components/ChatContainer';
import DebugSidebar from './components/DebugSidebar';
import GraphVisualizationSidebar from './components/GraphVisualizationSidebar';
import './App.css';

type SidebarType = 'debug' | 'graph' | null;

function App() {
  const [ontologyContext, setOntologyContext] = useState<any>(null);
  const [graphContext, setGraphContext] = useState<any>(null);
  const [graphData, setGraphData] = useState<any>(null);
  const [activeSidebar, setActiveSidebar] = useState<SidebarType>(null);

  const handleDebugDataUpdate = (ontology: any, graph: any, graphData?: any) => {
    setOntologyContext(ontology);
    setGraphContext(graph);

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
        ontologyContext={ontologyContext}
        graphContext={graphContext}
        isOpen={activeSidebar === 'debug'}
        onToggle={() => handleSidebarToggle('debug')}
      />
      <GraphVisualizationSidebar
        graphData={graphData}
        isOpen={activeSidebar === 'graph'}
        onToggle={() => handleSidebarToggle('graph')}
      />
      <header className="app-header">
        <h1>Self-Optimizing Agents - FHIR Graph RAG</h1>
      </header>
      <main>
        <ChatContainer onDebugDataUpdate={handleDebugDataUpdate} />
      </main>
    </div>
  );
}

export default App;
