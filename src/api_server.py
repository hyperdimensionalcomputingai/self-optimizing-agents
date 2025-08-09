import asyncio
import os
from typing import Optional
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
import uvicorn
from dotenv import load_dotenv
import opik
from opik import opik_context

from baml_client.async_client import b
from self_optimizing_agents import (
    answer_question,
    execute_vector_and_fts_rag,
    prune_schema,
    generate_ui_response,
    generate_ui_response_with_details,
)
from utils import KuzuDatabaseManager

# Load environment variables
load_dotenv()

# Set environment variables for BAML and API keys
os.environ["BAML_LOG"] = "WARN"
os.environ["OPENROUTER_API_KEY"] = os.environ.get("OPENROUTER_API_KEY")
os.environ["METRICS_SAMPLE_RATE"] = os.environ.get("METRICS_SAMPLE_RATE", "0.05")  # Default to 5% if not set

# Initialize FastAPI app
app = FastAPI(title="Self-Optimizing Agents API", version="1.0.0")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8172", "http://127.0.0.1:8172", "http://localhost:8001", "http://127.0.0.1:8001"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pydantic models for API requests/responses
class QueryRequest(BaseModel):
    query: str

class QueryResponse(BaseModel):
    response: str
    vector_answer: Optional[str] = None
    graph_answer: Optional[str] = None
    trace_id: Optional[str] = None
    span_id: Optional[str] = None
    # graph_data removed - no longer providing graph visualization

class FeedbackRequest(BaseModel):
    trace_id: Optional[str] = None
    span_id: Optional[str] = None
    feedback_type: str  # 'thumbs_up' or 'thumbs_down'
    reason: Optional[str] = None

# Initialize database manager
kuzu_db_manager = KuzuDatabaseManager("fhir_db.kuzu")

def get_current_trace_and_span_ids():
    """Helper function to extract trace and span IDs from current Opik context."""
    try:
        # Get current trace data
        trace_data = opik_context.get_current_trace_data()
        if trace_data and hasattr(trace_data, 'id'):
            trace_id = trace_data.id
        else:
            trace_id = None
        
        # Get current span data  
        span_data = opik_context.get_current_span_data()
        if span_data and hasattr(span_data, 'id'):
            span_id = span_data.id
        else:
            span_id = None
            
        return trace_id, span_id
    except Exception as e:
        print(f"Error getting trace/span IDs: {e}")
        return None, None

# Mount static files for React app
if os.path.exists("ui/build"):
    app.mount("/static", StaticFiles(directory="ui/build/static"), name="static")

@app.get("/")
async def read_root():
    """Serve the React app"""
    print(f"DEBUG: Serving React app from {os.path.abspath('ui/build/index.html')}")
    if not os.path.exists("ui/build/index.html"):
        raise HTTPException(status_code=500, detail="React app not built")
    return FileResponse("ui/build/index.html")

@app.post("/query", response_model=QueryResponse)
async def query_endpoint(request: QueryRequest):
    """Main query endpoint that runs the self-optimizing agents pipeline with prompt optimization"""
    try:
        question = request.query
        print(f"DEBUG: Processing query: {question}")
        
        # Use the UI-specific response generator that includes prompt optimization and returns details
        result = await generate_ui_response_with_details(question)
        print(f"DEBUG: Result type: {type(result)}, Result: {result}")
        
        if result is None:
            raise Exception("generate_ui_response_with_details returned None")
        
        if len(result) != 3:
            raise Exception(f"Expected 3 values, got {len(result)}: {result}")
        
        synthesized_answer, vector_answer, graph_answer = result
        
        print(f"DEBUG: synthesized_answer: {type(synthesized_answer)} = {synthesized_answer}")
        print(f"DEBUG: vector_answer: {type(vector_answer)} = {vector_answer}")
        print(f"DEBUG: graph_answer: {type(graph_answer)} = {graph_answer}")
        
        # Get current trace and span IDs for feedback functionality
        trace_id, span_id = get_current_trace_and_span_ids()
        print(f"DEBUG: trace_id: {trace_id}, span_id: {span_id}")
        
        # For UI calls, we return the synthesized answer along with vector and graph answers
        response = QueryResponse(
            response=synthesized_answer or "No answer generated",
            vector_answer=vector_answer,
            graph_answer=graph_answer,
            trace_id=trace_id,
            span_id=span_id
        )
        
        print(f"DEBUG: Returning response: {response}")
        return response
        
    except Exception as e:
        import traceback
        print(f"ERROR: Exception in query_endpoint: {e}")
        print(f"ERROR: Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "Self-Optimizing Agents API"}

def is_valid_uuid(uuid_string):
    """Check if a string is a valid UUID format."""
    import re
    uuid_pattern = re.compile(r'^[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}$', re.IGNORECASE)
    return bool(uuid_pattern.match(uuid_string))

@app.post("/feedback")
async def feedback_endpoint(request: FeedbackRequest):
    """Endpoint to record user feedback for traces and spans in Opik"""
    try:
        print(f"DEBUG: Received feedback: {request}")
        
        # Validate feedback type
        if request.feedback_type not in ['thumbs_up', 'thumbs_down']:
            raise HTTPException(status_code=400, detail="Invalid feedback_type. Must be 'thumbs_up' or 'thumbs_down'")
        
        # Skip Opik logging for mock/development IDs that don't match UUID format
        skip_opik_logging = False
        if request.trace_id and not is_valid_uuid(request.trace_id):
            print(f"DEBUG: Skipping Opik logging for non-UUID trace ID: {request.trace_id}")
            skip_opik_logging = True
        if request.span_id and not is_valid_uuid(request.span_id):
            print(f"DEBUG: Skipping Opik logging for non-UUID span ID: {request.span_id}")
            skip_opik_logging = True
        
        if not skip_opik_logging:
            # Create Opik client for logging feedback
            opik_client = opik.Opik()
            
            # Convert feedback to binary score (0 for thumbs_up/good, 1 for thumbs_down/bad)
            # Note: Following user requirement where 0 = good, 1 = bad
            score_value = 0.0 if request.feedback_type == 'thumbs_up' else 1.0
            
            # Prepare feedback score
            feedback_score = {
                "name": "overall_quality",
                "value": score_value,
                "reason": request.reason
            }
            
            # Log feedback to trace if trace_id is provided
            if request.trace_id:
                try:
                    opik_client.log_traces_feedback_scores(
                        scores=[{
                            "id": request.trace_id,
                            **feedback_score
                        }]
                    )
                    print(f"DEBUG: Logged feedback to trace {request.trace_id}")
                except Exception as trace_error:
                    print(f"WARNING: Failed to log feedback to trace {request.trace_id}: {trace_error}")
            
            # Log feedback to span if span_id is provided
            if request.span_id:
                try:
                    opik_client.log_spans_feedback_scores(
                        scores=[{
                            "id": request.span_id,
                            **feedback_score
                        }]
                    )
                    print(f"DEBUG: Logged feedback to span {request.span_id}")
                except Exception as span_error:
                    print(f"WARNING: Failed to log feedback to span {request.span_id}: {span_error}")
        else:
            print(f"DEBUG: Development mode - feedback recorded locally but not sent to Opik")
        
        if not request.trace_id and not request.span_id:
            raise HTTPException(status_code=400, detail="Either trace_id or span_id must be provided")
        
        return {"status": "success", "message": "Feedback recorded successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"ERROR: Exception in feedback_endpoint: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/query-detailed", response_model=QueryResponse)
async def query_detailed_endpoint(request: QueryRequest):
    """Detailed query endpoint that provides full RAG pipeline information with prompt optimization"""
    try:
        question = request.query
        
        # Step 1: Prune schema using self-optimizing agents
        pruned_schema_xml = await prune_schema(question)
        
        # Step 2: Extract entities using self-optimizing agents
        entities = await b.ExtractEntityKeywords(question, pruned_schema_xml)
        important_entities = " ".join(
            [f"{entity.key} {entity.value}".replace("_", " ") for entity in entities]
        )
        
        # Step 3: Generate vector/FTS context using self-optimizing agents
        vector_context = await execute_vector_and_fts_rag(
            question, pruned_schema_xml, important_entities
        )
        
        # Step 4: Generate Cypher and graph answer using self-optimizing agents
        cypher_response = await b.Text2Cypher(question, pruned_schema_xml, important_entities)
        
        graph_context = ""
        graph_data = None
        
        if cypher_response.cypher:
            # Run the Cypher query on the graph database
            conn = kuzu_db_manager.get_connection()
            query = cypher_response.cypher
            response = conn.execute(query)
            result = response.get_as_pl().to_dicts()
            graph_context = f"<CYPHER>\n{query}\n</CYPHER>\n<RESULT>\n{result}\n</RESULT>"
            
            # No longer preparing graph data for visualization
            graph_data = None
        
        # Generate answers using self-optimizing agents
        graph_answer = await answer_question(question, graph_context)
        vector_answer = await answer_question(question, vector_context)
        
        # Step 5: Synthesize final answer using self-optimizing agents
        synthesized_answer = await b.SynthesizeAnswers(question, vector_answer, graph_answer)
        
        return QueryResponse(
            response=synthesized_answer,
            vector_answer=vector_answer,
            graph_answer=graph_answer
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/{full_path:path}")
async def serve_react_app(full_path: str):
    """Serve React app for all other routes (for client-side routing)"""
    # Don't serve API routes
    if full_path.startswith("api/") or full_path.startswith("query") or full_path.startswith("health"):
        raise HTTPException(status_code=404, detail="Not Found")
    
    # Serve the React app for all other routes
    return FileResponse("ui/build/index.html")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8001) 