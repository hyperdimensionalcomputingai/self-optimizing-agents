import React from 'react';

interface DebugSidebarProps {
  ontologyContext?: any;
  graphContext?: any;
  isOpen: boolean;
  onToggle: () => void;
}

const DebugSidebar: React.FC<DebugSidebarProps> = ({
  ontologyContext,
  graphContext,
  isOpen,
  onToggle
}) => {

  return (
    <>
      <div className={`debug-sidebar ${isOpen ? 'open' : 'closed'}`}>
        <div className="sidebar-header">
          <h3>Debug Viewer</h3>
          <button
            className="close-button"
            onClick={onToggle}
            aria-label="Close sidebar"
          >
            ×
          </button>
        </div>

        <div className="sidebar-content">
          <div className="debug-section">
            <h4>Ontology Context</h4>
            <div className="debug-data">
              <pre>{typeof ontologyContext === 'string' ? ontologyContext : JSON.stringify(ontologyContext, null, 2) || 'No data'}</pre>
            </div>
          </div>

          <div className="debug-section">
            <h4>Graph Context</h4>
            <div className="debug-data">
              <pre>{typeof graphContext === 'string' ? graphContext : JSON.stringify(graphContext, null, 2) || 'No data'}</pre>
            </div>
          </div>
        </div>
      </div>

      {!isOpen && (
        <button
          className="sidebar-toggle"
          onClick={onToggle}
          aria-label="Open debug sidebar"
        >
          ❓
        </button>
      )}

      {isOpen && <div className="sidebar-overlay" onClick={onToggle} />}
    </>
  );
};

export default DebugSidebar;
