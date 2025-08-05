import React, { useEffect, useRef, useState } from 'react';

interface SimpleGraph {
  nodes: { [key: string]: any };
  edges: Array<{ source: string; target: string; weight?: number; [key: string]: any }>;
}

interface GraphVisualizationSidebarProps {
  graphData?: SimpleGraph | SimpleGraph[];
  isOpen: boolean;
  onToggle: () => void;
}

interface NodePosition {
  id: string;
  x: number;
  y: number;
  data: any;
}

const GraphVisualizationSidebar: React.FC<GraphVisualizationSidebarProps> = ({
  graphData,
  isOpen,
  onToggle
}) => {
  const [nodePositions, setNodePositions] = useState<NodePosition[]>([]);
  const [mergedGraph, setMergedGraph] = useState<SimpleGraph | null>(null);
  const svgRef = useRef<SVGSVGElement>(null);

  useEffect(() => {
    if (!graphData) {
      setMergedGraph(null);
      return;
    }

    // Handle both single graph and array of graphs
    let combinedGraph: SimpleGraph;

    if (Array.isArray(graphData)) {
      // Merge all subgraphs into one
      combinedGraph = {
        nodes: {},
        edges: []
      };

      graphData.forEach((subgraph) => {
        // Parse JSON string if needed
        let parsedSubgraph;
        if (typeof subgraph === 'string') {
          try {
            parsedSubgraph = JSON.parse(subgraph);
          } catch (e) {
            return; // Skip this subgraph
          }
        } else {
          parsedSubgraph = subgraph;
        }

        if (parsedSubgraph.nodes) {
          Object.assign(combinedGraph.nodes, parsedSubgraph.nodes);
        }
        if (parsedSubgraph.edges) {
          combinedGraph.edges.push(...parsedSubgraph.edges);
        }
      });
    } else {
      combinedGraph = graphData;
    }

    if (!combinedGraph.nodes || Object.keys(combinedGraph.nodes).length === 0) {
      setMergedGraph(null);
      return;
    }

    setMergedGraph(combinedGraph);

    const nodeIds = Object.keys(combinedGraph.nodes);
    const centerX = 300;
    const centerY = 200;
    const radius = Math.min(centerX, centerY) * 0.7;

    const positions: NodePosition[] = nodeIds.map((nodeId, index) => {
      const angle = (2 * Math.PI * index) / nodeIds.length;
      return {
        id: nodeId,
        x: centerX + radius * Math.cos(angle),
        y: centerY + radius * Math.sin(angle),
        data: combinedGraph.nodes[nodeId]
      };
    });

    setNodePositions(positions);
  }, [graphData]);

  const getNodePosition = (nodeId: string) => {
    return nodePositions.find(pos => pos.id === nodeId);
  };

  const getNodeDisplayLabel = (node: NodePosition) => {
    // Try to get prefLabel from node data
    const prefLabel = node.data?.properties?.prefLabel;
    if (prefLabel) {
      return prefLabel.length > 15 ? `${prefLabel.substring(0, 15)}...` : prefLabel;
    }

    // Fallback to node ID (truncated)
    return node.id.length > 10 ? `${node.id.substring(0, 10)}...` : node.id;
  };

  const renderEdges = () => {
    if (!mergedGraph?.edges) return null;

    return mergedGraph.edges.map((edge, index) => {
      const sourcePos = getNodePosition(edge.source);
      const targetPos = getNodePosition(edge.target);

      if (!sourcePos || !targetPos) return null;

      return (
        <line
          key={`edge-${index}`}
          x1={sourcePos.x}
          y1={sourcePos.y}
          x2={targetPos.x}
          y2={targetPos.y}
          stroke="#ffff00"
          strokeWidth={edge.weight ? Math.max(1, edge.weight * 3) : 1}
          opacity={0.8}
        />
      );
    });
  };

  const renderNodes = () => {
    return nodePositions.map((node) => (
      <g key={`node-${node.id}`}>
        <circle
          cx={node.x}
          cy={node.y}
          r={15}
          fill="#ffffff"
          stroke="#ffff00"
          strokeWidth={2}
        />
        <text
          x={node.x}
          y={node.y + 25}
          textAnchor="middle"
          fontSize="12"
          fill="#ffffff"
          fontFamily="Arial, sans-serif"
        >
          {getNodeDisplayLabel(node)}
        </text>
      </g>
    ));
  };

  return (
    <>
      <div className={`graph-sidebar ${isOpen ? 'open' : 'closed'}`}>
        <div className="sidebar-header">
          <h3>Graph Visualization</h3>
          <button
            className="close-button"
            onClick={onToggle}
            aria-label="Close graph sidebar"
          >
            ×
          </button>
        </div>

        <div className="sidebar-content">
          <div className="graph-container">
            {mergedGraph && Object.keys(mergedGraph.nodes).length > 0 ? (
              <svg
                ref={svgRef}
                width="600"
                height="400"
                viewBox="0 0 600 400"
                style={{ border: '1px solid #ffffff', borderRadius: '4px' }}
              >
                {renderEdges()}
                {renderNodes()}
              </svg>
            ) : (
              <div className="no-graph-data">
                <p>No graph data available</p>
              </div>
            )}
          </div>

          {mergedGraph && (
            <div className="graph-stats">
              <p><strong>Nodes:</strong> {Object.keys(mergedGraph.nodes || {}).length}</p>
              <p><strong>Edges:</strong> {mergedGraph.edges?.length || 0}</p>
              {Array.isArray(graphData) && (
                <p><strong>Subgraphs:</strong> {graphData.length}</p>
              )}
            </div>
          )}
        </div>
      </div>

      {!isOpen && (
        <button
          className="graph-sidebar-toggle"
          onClick={onToggle}
          aria-label="Open graph visualization sidebar"
        >
          🔗
        </button>
      )}

      {isOpen && <div className="sidebar-overlay" onClick={onToggle} />}
    </>
  );
};

export default GraphVisualizationSidebar;
