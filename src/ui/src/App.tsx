import React, { useState } from 'react';
import ChatContainer from './components/ChatContainer';
import DebugSidebar from './components/DebugSidebar';
import FeedbackTest from './components/FeedbackTest';
import './App.css';

type SidebarType = 'debug' | null;

function App() {
  const [vectorAnswer, setVectorAnswer] = useState<string>('');
  const [graphAnswer, setGraphAnswer] = useState<string>('');
  const [activeSidebar, setActiveSidebar] = useState<SidebarType>(null);

  const handleDebugDataUpdate = (vectorAnswer: string, graphAnswer: string, graphData?: any) => {
    setVectorAnswer(vectorAnswer);
    setGraphAnswer(graphAnswer);
    // graphData is no longer used since visualization is removed
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
