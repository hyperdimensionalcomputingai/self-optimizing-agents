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

def log_opik_configuration():
    """Log Opik configuration status for debugging feedback integration"""
    print("\n" + "=" * 80)
    print("🔧 OPIK CONFIGURATION STATUS")
    print("=" * 80)
    
    opik_api_key = os.environ.get("OPIK_API_KEY")
    opik_workspace = os.environ.get("OPIK_WORKSPACE") 
    opik_project = os.environ.get("OPIK_PROJECT_NAME", "ODSC-RAG")
    
    print(f"📊 OPIK_API_KEY: {'✅ Set' if opik_api_key else '❌ Missing'}")
    print(f"🏢 OPIK_WORKSPACE: {'✅ ' + opik_workspace if opik_workspace else '❌ Missing'}")
    print(f"📁 OPIK_PROJECT_NAME: {opik_project}")
    
    if opik_api_key and opik_workspace:
        print("✅ Opik configuration complete - feedback integration should work")
        try:
            test_client = opik.Opik()
            print("✅ Opik client creation successful")
        except Exception as e:
            print(f"❌ Opik client creation failed: {e}")
    else:
        print("⚠️  Opik configuration incomplete - feedback integration will be limited")
        print("   Please set OPIK_API_KEY and OPIK_WORKSPACE environment variables")
    
    print("=" * 80)

# Log Opik configuration on startup
log_opik_configuration()

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
        
        print("\n" + "=" * 80)
        print("🚀 NEW QUERY RECEIVED")
        print("=" * 80)
        print(f"❓ Question: {question}")
        print("🔄 Starting RAG pipeline with Opik trace creation...")
        
        # Use the UI-specific response generator that includes prompt optimization and returns details
        result = await generate_ui_response_with_details(question)
        print(f"✅ RAG pipeline completed successfully")
        
        if result is None:
            raise Exception("generate_ui_response_with_details returned None")
        
        if len(result) != 5:
            raise Exception(f"Expected 5 values (answer, vector, graph, trace_id, span_id), got {len(result)}: {result}")
        
        synthesized_answer, vector_answer, graph_answer, trace_id, span_id = result
        
        print(f"DEBUG: synthesized_answer: {type(synthesized_answer)} = {synthesized_answer}")
        print(f"DEBUG: vector_answer: {type(vector_answer)} = {vector_answer}")
        print(f"DEBUG: graph_answer: {type(graph_answer)} = {graph_answer}")
        
        print(f"\n🔗 TRACE/SPAN ID EXTRACTION FOR FEEDBACK:")
        print(f"   - Trace ID: {trace_id or 'None'}")
        print(f"   - Span ID: {span_id or 'None'}")
        if trace_id and span_id:
            print(f"   - ✅ Valid IDs available for feedback tracking")
            print(f"   - 🎯 Feedback buttons will be enabled in UI")
        else:
            print(f"   - ⚠️  Missing IDs - feedback functionality will be limited")
            print(f"   - 🚫 Feedback buttons may not work properly")
        
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

@app.get("/test-trace")
async def test_trace_endpoint():
    """Test endpoint to generate a real trace ID for feedback testing"""
    try:
        # Create a simple trace using Opik
        import opik
        from opik import opik_context
        
        @opik.track(flush=True)
        async def create_test_trace():
            # Update trace with test data
            opik_context.update_current_trace(
                name="Test Trace for Feedback",
                input={"test": "This is a test trace to verify feedback submission"},
                metadata={"purpose": "feedback_testing"},
                tags=["test", "feedback"]
            )
            
            # Create a test span
            opik_context.update_current_span(
                name="test_span",
                metadata={"test_data": "Sample response for feedback testing"}
            )
            
            # Get the trace and span IDs
            trace_id, span_id = get_current_trace_and_span_ids()
            return trace_id, span_id
        
        trace_id, span_id = await create_test_trace()
        
        print("\n" + "=" * 80)
        print("🧪 TEST TRACE CREATED FOR FEEDBACK TESTING")
        print("=" * 80)
        print(f"🔗 Trace ID: {trace_id}")
        print(f"📊 Span ID: {span_id}")
        print("💡 Use these IDs to test feedback submission:")
        print(f"   POST /feedback with body:")
        print(f"   {{")
        print(f"     \"trace_id\": \"{trace_id}\",")
        print(f"     \"span_id\": \"{span_id}\",")
        print(f"     \"feedback_type\": \"thumbs_up\",")
        print(f"     \"reason\": \"Test feedback reason\"")
        print(f"   }}")
        print("=" * 80)
        
        return {
            "status": "success",
            "message": "Test trace created for feedback testing",
            "trace_id": trace_id,
            "span_id": span_id,
            "test_feedback_data": {
                "trace_id": trace_id,
                "span_id": span_id,
                "feedback_type": "thumbs_up",  # or "thumbs_down"
                "reason": "This is a test reason"
            }
        }
        
    except Exception as e:
        print(f"ERROR: Failed to create test trace: {e}")
        return {"status": "error", "error": str(e)}

def is_valid_uuid(uuid_string):
    """Check if a string is a valid UUID format."""
    import re
    uuid_pattern = re.compile(r'^[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}$', re.IGNORECASE)
    return bool(uuid_pattern.match(uuid_string))

@app.post("/feedback")
async def feedback_endpoint(request: FeedbackRequest):
    """Endpoint to record user feedback for traces and spans in Opik"""
    from datetime import datetime
    
    try:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Enhanced logging for user feedback reception
        print("=" * 80)
        print(f"🎯 USER FEEDBACK RECEIVED at {timestamp}")
        print("=" * 80)
        print(f"📝 Feedback Type: {request.feedback_type.upper()}")
        print(f"🔗 Trace ID: {request.trace_id}")
        print(f"📊 Span ID: {request.span_id}")
        
        if request.reason:
            print(f"💭 User Reason: '{request.reason}'")
        else:
            print("💭 User Reason: (none provided)")
        
        # Validate feedback type
        if request.feedback_type not in ['thumbs_up', 'thumbs_down']:
            print(f"❌ VALIDATION ERROR: Invalid feedback_type: {request.feedback_type}")
            raise HTTPException(status_code=400, detail="Invalid feedback_type. Must be 'thumbs_up' or 'thumbs_down'")
        
        print("✅ Feedback validation passed")
        
        # Skip Opik logging for mock/development IDs that don't match UUID format
        skip_opik_logging = False
        if request.trace_id and not is_valid_uuid(request.trace_id):
            print(f"🚧 DEVELOPMENT MODE: Skipping Opik logging for non-UUID trace ID: {request.trace_id}")
            skip_opik_logging = True
        if request.span_id and not is_valid_uuid(request.span_id):
            print(f"🚧 DEVELOPMENT MODE: Skipping Opik logging for non-UUID span ID: {request.span_id}")
            skip_opik_logging = True
        
        if not skip_opik_logging:
            print("\n🚀 INITIATING OPIK FEEDBACK LOGGING")
            print(f"   - Target Trace: {request.trace_id}")
            print(f"   - Target Span: {request.span_id}")
            
            # Create Opik client for logging feedback
            try:
                opik_client = opik.Opik()
                print("✅ Opik client created successfully")
            except Exception as client_error:
                print(f"❌ Failed to create Opik client: {client_error}")
                raise
            
            # Convert feedback to binary score (0 for thumbs_up/good, 1 for thumbs_down/bad)
            # Note: Following user requirement where 0 = good, 1 = bad
            score_value = 0.0 if request.feedback_type == 'thumbs_up' else 1.0
            
            # Prepare feedback score
            feedback_score = {
                "name": "overall_quality",
                "value": score_value,
                "reason": request.reason
            }
            
            print(f"\n📊 FEEDBACK SCORE PREPARED:")
            print(f"   - Metric Name: {feedback_score['name']}")
            print(f"   - Score Value: {feedback_score['value']} ({'POSITIVE' if score_value == 0.0 else 'NEGATIVE'})")
            print(f"   - User Reason: {feedback_score['reason'] or 'None'}")
            
            feedback_logged = False
            
            # Log feedback to trace if trace_id is provided
            if request.trace_id:
                try:
                    print(f"\n🎯 LOGGING TO TRACE: {request.trace_id}")
                    opik_client.log_traces_feedback_scores(
                        scores=[{
                            "id": request.trace_id,
                            **feedback_score
                        }]
                    )
                    print(f"✅ SUCCESS: Feedback logged to trace {request.trace_id}")
                    print(f"   - Score: {score_value} ({request.feedback_type})")
                    if request.reason:
                        print(f"   - Reason: '{request.reason}'")
                    feedback_logged = True
                except Exception as trace_error:
                    print(f"❌ ERROR: Failed to log feedback to trace {request.trace_id}")
                    print(f"   - Error: {trace_error}")
                    print(f"   - Error Type: {type(trace_error).__name__}")
                    print(f"   - Full Error: {str(trace_error)}")
            
            # Log feedback to span if span_id is provided
            if request.span_id:
                try:
                    print(f"\n📊 LOGGING TO SPAN: {request.span_id}")
                    opik_client.log_spans_feedback_scores(
                        scores=[{
                            "id": request.span_id,
                            **feedback_score
                        }]
                    )
                    print(f"✅ SUCCESS: Feedback logged to span {request.span_id}")
                    print(f"   - Score: {score_value} ({request.feedback_type})")
                    if request.reason:
                        print(f"   - Reason: '{request.reason}'")
                    feedback_logged = True
                except Exception as span_error:
                    print(f"❌ ERROR: Failed to log feedback to span {request.span_id}")
                    print(f"   - Error: {span_error}")
                    print(f"   - Error Type: {type(span_error).__name__}")
                    print(f"   - Full Error: {str(span_error)}")
            
            if feedback_logged:
                print(f"\n🎉 OPIK FEEDBACK LOGGING COMPLETED SUCCESSFULLY!")
                print(f"   - Check your Opik dashboard for the '{feedback_score['name']}' metric")
                print(f"   - Feedback should appear on trace/span with timestamp: {timestamp}")
            else:
                print(f"\n⚠️  WARNING: No feedback was successfully logged to Opik")
                
        else:
            print(f"\n🚧 DEVELOPMENT MODE ACTIVE")
            print(f"   - Feedback recorded locally but NOT sent to Opik")
            print(f"   - Trace ID: {request.trace_id}")
            print(f"   - Span ID: {request.span_id}")
            print(f"   - Feedback: {request.feedback_type}")
            if request.reason:
                print(f"   - Reason: '{request.reason}'")
        
        if not request.trace_id and not request.span_id:
            print("❌ ERROR: Neither trace_id nor span_id provided")
            raise HTTPException(status_code=400, detail="Either trace_id or span_id must be provided")
        
        print("=" * 80)
        print(f"✅ FEEDBACK PROCESSING COMPLETED at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 80)
        
        return {"status": "success", "message": "Feedback recorded successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"\n❌ CRITICAL ERROR in feedback_endpoint:")
        print(f"   - Error: {e}")
        print(f"   - Error Type: {type(e).__name__}")
        print(f"   - Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 80)
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