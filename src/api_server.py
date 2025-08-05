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
os.environ["OPENROUTER_API_KEY"] = os.getenv("OPENROUTER_API_KEY")
os.environ["METRICS_SAMPLE_RATE"] = "0.05"

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
    graph_data: Optional[dict] = None

# Initialize database manager
kuzu_db_manager = KuzuDatabaseManager("fhir_db.kuzu")

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
        
        # Use the UI-specific response generator that includes prompt optimization and returns details
        synthesized_answer, vector_answer, graph_answer = await generate_ui_response_with_details(question)
        
        # For UI calls, we return the synthesized answer along with vector and graph answers
        return QueryResponse(
            response=synthesized_answer or "No answer generated",
            vector_answer=vector_answer,
            graph_answer=graph_answer,
            graph_data={}
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "Self-Optimizing Agents API"}


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
            
            # Prepare graph data for visualization
            graph_data = {
                "cypher_query": query,
                "result": result
            }
        
        # Generate answers using self-optimizing agents
        graph_answer = await answer_question(question, graph_context)
        vector_answer = await answer_question(question, vector_context)
        
        # Step 5: Synthesize final answer using self-optimizing agents
        synthesized_answer = await b.SynthesizeAnswers(question, vector_answer, graph_answer)
        
        return QueryResponse(
            response=synthesized_answer,
            ontology_context={"pruned_schema": pruned_schema_xml},
            graph_context_str=graph_context,
            graph_data=graph_data
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