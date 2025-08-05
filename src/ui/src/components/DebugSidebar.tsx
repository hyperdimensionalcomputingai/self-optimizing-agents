import React from 'react';

interface DebugSidebarProps {
  vectorAnswer?: string;
  graphAnswer?: string;
  isOpen: boolean;
  onToggle: () => void;
}

const DebugSidebar: React.FC<DebugSidebarProps> = ({
  vectorAnswer,
  graphAnswer,
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
            <h4>Vector Answer</h4>
            <div className="debug-data">
              <pre>{vectorAnswer || 'No data'}</pre>
            </div>
          </div>

          <div className="debug-section">
            <h4>Graph Answer</h4>
            <div className="debug-data">
              <pre>{graphAnswer || 'No data'}</pre>
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
