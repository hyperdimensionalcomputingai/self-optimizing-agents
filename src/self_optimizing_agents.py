"""
Observability & evaluation tools for RAG workflows on the FHIR graph database
- Graph-based RAG (Kuzu)
- Vector and FTS-based RAG (LanceDB)
- Evaluation and observability using Opik

The observability tool used is Opik, by Comet:
https://www.comet.com/site/products/opik/
"""

import asyncio
import os
from textwrap import dedent
from datetime import datetime

import lancedb
import opik
from opik import opik_context
from dotenv import load_dotenv
from lancedb.embeddings import get_registry
from lancedb.rerankers import RRFReranker
from openai import OpenAI
from opik.integrations.openai import track_openai

import utils
from baml_client.async_client import b
from baml_instrumentation import BAMLInstrumentation, track_baml_call, run_post_call_metrics
from guardrails import (
    EmailGuardrail, 
    GuardrailAction, 
    GuardrailSeverity, 
    validate_input_with_guardrails, 
    validate_output_with_guardrails,
    EnhancedGuardrailManager
)
from prompt_optimization import collect_response_with_metrics, prompt_optimizer
from baml_request_extractor import extract_request_from_collector, get_prompt_from_request, get_model_from_request
from baml_metadata_extractor import create_span_metadata_with_baml_info
from baml_client import types as baml_types
from logging_config import get_logger

# Load environment variables
load_dotenv()
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY")
OPIK_API_KEY = os.environ.get("OPIK_API_KEY")
OPIK_WORKSPACE = os.environ.get("OPIK_WORKSPACE")
OPIK_PROJECT_NAME = os.environ.get("OPIK_PROJECT_NAME", "ODSC-RAG")  # Default to ODSC-RAG if not set

# Initialize logger
logger = get_logger(__name__)

# Set a reasonable sample rate for metrics to avoid overwhelming the system
os.environ["METRICS_SAMPLE_RATE"] = os.environ.get("METRICS_SAMPLE_RATE", "0.05")  # Default to 5% if not set

# Configure BAML logging
os.environ["BAML_LOG"] = "OFF"

# Configure guardrails
GUARDRAILS_ENABLED = os.environ.get("GUARDRAILS_ENABLED", "true").lower() == "true"

# Initialize enhanced guardrail manager for better tracing
if GUARDRAILS_ENABLED:
    enhanced_guardrail_manager = EnhancedGuardrailManager([
        EmailGuardrail(
            action=GuardrailAction.WARN,
            severity=GuardrailSeverity.MEDIUM,
            mask_emails=True,
            block_common_domains=False
        )
    ])

# Global storage for extracted prompts across the workflow
# Note: Prompt extraction is now only done in synthesize_answers function

def store_extracted_prompt(function_name: str, prompt: str, model: str, metadata: dict = None):
    """
    Store extracted prompt data for later use in optimization.
    
    Args:
        function_name: Name of the BAML function
        prompt: The extracted prompt
        model: The model used
        metadata: Additional metadata
    """
    # This function is deprecated - prompt extraction is now only done in synthesize_answers
    pass

async def store_prompt_in_function_dataset(function_name: str, question: str, answer: str, prompt: str, model: str, metadata: dict = None):
    """
    Store extracted prompt data in a function-specific dataset for independent optimization.
    
    Args:
        function_name: Name of the BAML function
        question: The input question
        answer: The generated answer
        prompt: The extracted prompt
        model: The model used
        metadata: Additional metadata
    """
    try:
        # Import PromptOptimizationManager here to avoid scope issues
        from prompt_optimization import PromptOptimizationManager
        
        # Create dataset name based on function
        dataset_name = f"self_optimizing_agents_optimization_{function_name.lower()}"
        
        # Create a function-specific prompt optimizer
        function_optimizer = PromptOptimizationManager(dataset_name=dataset_name)
        
        # Store in the function-specific dataset
        await function_optimizer.collect_response_with_metrics(
            question=question,
            answer=answer,
            metrics={
                "prompt_extraction": 1.0,
                "prompt_length_score": min(len(prompt) / 1000, 1.0)
            },
            additional_metadata={
                "extracted_prompt": prompt,
                "extracted_model": model,
                "function_name": function_name,
                "prompt_length": len(prompt),
                "workflow_step": "function_specific",
                **(metadata or {})
            }
        )
        
        logger.info(f"Stored prompt in function-specific dataset: {dataset_name}")
        
    except Exception as e:
        logger.warning(f"Failed to store prompt in function-specific dataset {function_name}: {e}")



# Set embedding registry in LanceDB to use ollama
embedding_model = get_registry().get("ollama").create(name="nomic-embed-text")
kuzu_db_manager = utils.KuzuDatabaseManager("fhir_db.kuzu")

# Initialize the OpenAI client with OpenRouter base URL
client = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=OPENROUTER_API_KEY)
client = track_openai(client)

# Optional headers for OpenRouter leaderboard
headers = {
    "HTTP-Referer": "graphgeeks.org",  # Optional. Site URL for rankings
    "X-Title": "GraphGeeks",  # Optional. Site title for rankings
}

# Configure Opik
if OPIK_API_KEY and OPIK_WORKSPACE:
    os.environ["OPIK_API_KEY"] = OPIK_API_KEY
    os.environ["OPIK_WORKSPACE"] = OPIK_WORKSPACE
    os.environ["OPIK_PROJECT_NAME"] = OPIK_PROJECT_NAME
    
    # Set OpenRouter API key for Opik metrics (LLM as a Judge)
    if OPENROUTER_API_KEY:
        os.environ["OPENROUTER_API_KEY"] = OPENROUTER_API_KEY
    else:
        logger.warning("OPENROUTER_API_KEY not set. Opik metrics may fail.")
    
    # Configure Opik for cloud usage
    opik.configure(use_local=False)
    logger.info("Opik configured for cloud tracking")
else:
    logger.warning(
        "Please set the OPIK_API_KEY and OPIK_WORKSPACE environment variables to enable opik tracking"
    )
    # Disable Opik tracking if credentials are not provided
    opik.configure(use_local=True)
    logger.info("Opik configured for local tracking (no cloud credentials)")




# Core RAG Functions
@opik.track(flush=True)
async def prune_schema(question: str) -> str:
    schema = kuzu_db_manager.get_schema_dict
    schema_xml = kuzu_db_manager.get_schema_xml(schema)

    pruned_schema, baml_collector = await track_baml_call(
        b.PruneSchema,
        "prune_schema_collector",
        "pruned_schema",
        schema_xml,
        question,
        return_collector=True
    )

    pruned_schema_xml = kuzu_db_manager.get_schema_xml(pruned_schema.model_dump())
    logger.info("Generated pruned schema XML")
    
    return pruned_schema_xml


@opik.track(flush=True)
async def answer_question(question: str, context: str) -> str:
    answer, baml_collector = await track_baml_call(
        b.AnswerQuestion,
        "answer_question_collector",
        "answer_question",
        question,
        context,
        return_collector=True
    )
    
    return answer


@opik.track(flush=True)
async def execute_graph_rag(question: str, schema_xml: str, important_entities: str) -> str:
    response_cypher, baml_collector = await track_baml_call(
        b.Text2Cypher,
        "execute_graph_rag_collector",
        "execute_graph_rag",
        question,
        schema_xml,
        important_entities,
        return_collector=True
    )
    
    if response_cypher.cypher:
        # Run the Cypher query on the graph database
        conn = kuzu_db_manager.get_connection()
        query = response_cypher.cypher
        response = conn.execute(query)
        result = response.get_as_pl().to_dicts()  # type: ignore
        logger.info("Ran Cypher query")
    else:
        logger.warning("No Cypher query was generated from the given question and schema")
        result = ""
        query = ""
    
    context = dedent(
        f"""
        <CYPHER>
        {query}
        </CYPHER>

        <RESULT>
        {result}
        </RESULT>
        """
    )
    
    # Update opik context with additional metadata
    opik_context.update_current_span(
        name="execute_graph_rag",
        metadata={
            "cypher_generated": bool(response_cypher.cypher),
            "cypher": response_cypher.cypher,
            "result_count": len(result) if result else 0,
        }
    )
    
    answer = await answer_question(question, context)
    return answer


@opik.track(flush=True)
async def execute_vector_and_fts_rag(
    question: str, schema_xml: str, important_entities: str, top_k: int = 2
) -> str:
    lancedb_table_name = "notes"
    lancedb_db_manager = await lancedb.connect_async("./fhir_lance_db")
    async_tbl = await lancedb_db_manager.open_table(lancedb_table_name)
    reranker = RRFReranker()
    
    if important_entities:
        response = await async_tbl.search(important_entities, query_type="hybrid")
        response_polars = (
            await response.rerank(reranker=reranker)
            .limit(top_k)
            .select(["record_id", "note"])
            .to_polars()
        )
        response_dicts = response_polars.to_dicts()
        context = " ".join([f"{row['note']}\n" for row in response_dicts])
        logger.info("Generated vector context")
        
        # Update opik context with vector search data
        opik_context.update_current_span(
            name="execute_vector_and_fts_rag",
            metadata={
                "top_k": top_k,
                "entities_found": bool(important_entities),
                "results_count": len(response_dicts),
                "search_type": "hybrid",
            },
        )
    else:
        logger.info("No important entities found, skipping querying vector database...")
        context = ""
        
        # Update opik context for skipped search
        opik_context.update_current_span(
            name="execute_vector_and_fts_rag",
            metadata={
                "top_k": top_k,
                "entities_found": False,
                "results_count": 0,
                "search_type": "skipped",
            },
        )
    
    return context


@opik.track(flush=True)
async def get_vector_context(question, pruned_schema_xml, important_entities, top_k=2):
    return await execute_vector_and_fts_rag(question, pruned_schema_xml, important_entities, top_k)


@opik.track(flush=True)
async def get_graph_answer(question, pruned_schema_xml, important_entities):
    return await execute_graph_rag(question, pruned_schema_xml, important_entities)


@opik.track(flush=True)
async def extract_entity_keywords(question: str, pruned_schema_xml: str):
    entities, baml_collector = await track_baml_call(
        b.ExtractEntityKeywords,
        "extract_entity_keywords_collector",
        "extract_entity_keywords",
        question,
        pruned_schema_xml,
        return_collector=True
    )

    # Convert entities to a string representation for metrics
    entities_str = "\n".join([f"- key: {entity.key}\n  value: {entity.value}" for entity in entities])
    
    # Debug: Log the entities being checked
    logger.info(f"Checking Contains metric for entities: {entities_str}")
    
    # Store entities for later use in Contains metric
    # The Contains metric will be run along with other metrics in synthesize_answers
    logger.info(f"Extracted {len(entities)} entities for Contains metric evaluation")

    return entities


@opik.track(flush=True)
async def run_hybrid_rag(question: str, question_number: int = None) -> tuple[str, str, list]:
    logger.info(f"---\nQuestion {question_number}: {question}")
    
    # Apply input guardrails if enabled
    if GUARDRAILS_ENABLED:
        try:
            # Use enhanced guardrail manager for better tracing
            processed_question = await enhanced_guardrail_manager.validate_with_detailed_tracing(
                question,
                span_name=f"input_guardrail_validation_q{question_number}" if question_number else "input_guardrail_validation",
                trace_tags=["rag_input", "email_validation"],
                custom_metadata={
                    "question_number": question_number,
                    "workflow_step": "input_validation",
                    "rag_type": "hybrid"
                },
                validation_type="input"
            )
            
            if processed_question != question:
                logger.info(f"Input processed by guardrails: {processed_question}")
                question = processed_question
                
        except Exception as e:
            logger.warning(f"Input guardrail validation failed: {e}")
    
    pruned_schema_xml = await prune_schema(question)
    entities = await extract_entity_keywords(question, pruned_schema_xml)
    important_entities = " ".join(
        [f"{entity.key} {entity.value}".replace("_", " ") for entity in entities]
    )
    
    # Start both RAG tasks concurrently
    vector_context_task = asyncio.create_task(
        get_vector_context(question, pruned_schema_xml, important_entities)
    )
    graph_answer_task = asyncio.create_task(
        get_graph_answer(question, pruned_schema_xml, important_entities)
    )
    
    # As soon as vector context is ready, start answer generation
    vector_context = await vector_context_task
    vector_answer_task = asyncio.create_task(answer_question(question, vector_context))

    # Await both vector answer generation and graph answer generation before returning
    vector_answer, graph_answer = await asyncio.gather(vector_answer_task, graph_answer_task)
    
    # Update opik context with workflow summary
    opik_context.update_current_span(
        name="run_hybrid_rag",
        metadata={
            "question": question,
            "entities_extracted": len(entities),
            "vector_context_generated": bool(vector_context),
            "graph_answer_generated": bool(graph_answer),
        },
    )
    
    return vector_answer, graph_answer, entities


@opik.track(flush=True)
async def synthesize_answers(question: str, vector_answer: str, graph_answer: str, entities: list = None, question_number: int = None) -> str:
    # Import opik_context at the beginning to avoid UnboundLocalError
    from opik import opik_context
    
    prompt_data, baml_collector = await track_baml_call(
        b.OptimizedSynthesizeAnswers,
        "synthesize_answers_collector",
        "synthesize_answers",
        question,
        vector_answer,
        graph_answer,
        return_collector=True
    )
    
    # Extract the actual answer from the PromptOptimizationData object
    synthesized_answer = prompt_data.final_answer_prompt
    
    # Extract metadata from the prompt_data object for upcoming work
    # This is done after the main BAML call to avoid interfering with metrics
    if baml_collector:
        try:
            # Extract request data from the BAML collector
            request_data = extract_request_from_collector(baml_collector, "OptimizedSynthesizeAnswers")
            
            if request_data:
                # Extract prompt and model information
                extracted_prompt = get_prompt_from_request(request_data)
                extracted_model = get_model_from_request(request_data)
                
                logger.info(f"Extracted synthesize answers request data: model={extracted_model}, prompt_length={len(extracted_prompt) if extracted_prompt else 0}")
                
                # Get full BAML metadata with field descriptions and structured analysis
                try:
                    # Get the BAML type class for OptimizedSynthesizeAnswers
                    baml_type_class = getattr(baml_types, "PromptOptimizationData", None)
                    
                    if baml_type_class and hasattr(prompt_data, 'model_dump'):
                        # Create structured metadata with BAML field descriptions
                        baml_metadata = create_span_metadata_with_baml_info(
                            prompt_data,
                            baml_type_class,
                            additional_metadata={
                                "extracted_prompt": extracted_prompt,
                                "extracted_model": extracted_model,
                                "request_url": request_data.url,
                                "request_method": request_data.method,
                                "workflow_step": "synthesize_answers",
                                "function_name": "OptimizedSynthesizeAnswers",
                                "has_prompt_content": bool(extracted_prompt),
                                "question": question,
                                "vector_answer_length": len(vector_answer),
                                "graph_answer_length": len(graph_answer)
                            }
                        )
                        
                        # Update Opik context with full BAML metadata
                        opik_context.update_current_span(
                            name="synthesize_answers",
                            metadata=baml_metadata
                        )
                        
                        logger.info(f"Added full BAML metadata with {len(baml_metadata)} fields")
                        
                    else:
                        # Fallback to basic metadata if BAML type class not found
                        opik_context.update_current_span(
                            name="synthesize_answers",
                            metadata={
                                "extracted_prompt": extracted_prompt,
                                "extracted_model": extracted_model,
                                "request_url": request_data.url,
                                "request_method": request_data.method,
                                "workflow_step": "synthesize_answers",
                                "function_name": "OptimizedSynthesizeAnswers",
                                "has_prompt_content": bool(extracted_prompt),
                                "question": question,
                                "vector_answer_length": len(vector_answer),
                                "graph_answer_length": len(graph_answer)
                            }
                        )
                        
                except Exception as baml_metadata_error:
                    logger.warning(f"Failed to extract BAML metadata: {baml_metadata_error}")
                    # Fallback to basic metadata
                    opik_context.update_current_span(
                        name="synthesize_answers",
                        metadata={
                            "extracted_prompt": extracted_prompt,
                            "extracted_model": extracted_model,
                            "request_url": request_data.url,
                            "request_method": request_data.method,
                            "workflow_step": "synthesize_answers",
                            "function_name": "OptimizedSynthesizeAnswers",
                            "has_prompt_content": bool(extracted_prompt),
                            "question": question,
                            "vector_answer_length": len(vector_answer),
                            "graph_answer_length": len(graph_answer)
                        }
                    )
                
                # Store the extracted prompt in function-specific dataset
                if extracted_prompt:
                    await store_prompt_in_function_dataset(
                        "OptimizedSynthesizeAnswers",
                        question,
                        synthesized_answer,  # Use the synthesized answer as the result
                        extracted_prompt,
                        extracted_model,
                        {
                            "request_url": request_data.url,
                            "request_method": request_data.method,
                            "workflow_step": "synthesize_answers",
                            "baml_type_name": "PromptOptimizationData",
                            "has_structured_metadata": True,
                            "vector_answer_length": len(vector_answer),
                            "graph_answer_length": len(graph_answer)
                        }
                    )
                
        except Exception as e:
            logger.warning(f"Failed to extract synthesize answers request data: {e}")
    

    
    # Apply output guardrails if enabled
    if GUARDRAILS_ENABLED:
        try:
            # Use enhanced guardrail manager for better tracing
            processed_answer = await enhanced_guardrail_manager.validate_with_detailed_tracing(
                synthesized_answer,
                span_name=f"output_guardrail_validation_q{question_number}" if question_number else "output_guardrail_validation",
                trace_tags=["rag_output", "email_validation"],
                custom_metadata={
                    "question_number": question_number,
                    "workflow_step": "output_validation",
                    "rag_type": "hybrid",
                    "answer_length": len(synthesized_answer)
                },
                validation_type="output"
            )
            
            if processed_answer != synthesized_answer:
                logger.info("Output processed by guardrails")
                synthesized_answer = processed_answer
                
        except Exception as e:
            logger.warning(f"Output guardrail validation failed: {e}")
    
    # Run metrics after the BAML call completes
    metrics_list = [
        {"type": "Hallucination", "params": {"model": "openrouter/openai/gpt-4o"}},
        {"type": "AnswerRelevance", "params": {"model": "openrouter/openai/gpt-4o"}},
        {"type": "Moderation", "params": {"model": "openrouter/openai/gpt-4o"}},
        {"type": "Usefulness", "params": {"model": "openrouter/openai/gpt-4o"}},
    ]
    
    # Add Contains metric if entities are provided
    if entities:
        entities_str = "\n".join([f"- key: {entity.key}\n  value: {entity.value}" for entity in entities])
        metrics_list.append({
            "type": "Contains", 
            "params": {
                "reference": entities_str
            }
        })
        logger.info(f"Added Contains metric with {len(entities)} entities")
    
    await run_post_call_metrics(
        "synthesize_answers_collector",
        "synthesize_answers",
        input=question,
        output=synthesized_answer,
        context=[graph_answer + vector_answer],
        metrics=metrics_list
    )
    

    
    return synthesized_answer


# Evaluation Functions
@opik.track(flush=True)
async def generate_response(question: str, question_number: int = None) -> str | None:
    """Generate response for individual calls (UI or evaluation) with prompt optimization."""
    vector_answer, graph_answer, entities = await run_hybrid_rag(question, question_number)
    synthesized_answer = await synthesize_answers(question, vector_answer, graph_answer, entities, question_number)
    
    # Update the current span with question-specific information
    span_name = f"Question {question_number}" if question_number else "Question"
    opik_context.update_current_span(
        name=span_name,
        metadata={
            "workflow_type": "rag_evaluation" if question_number else "rag_ui_call",
            "question_number": question_number,
            "question": question,
            "vector_answer_length": len(vector_answer),
            "graph_answer_length": len(graph_answer),
            "synthesized_answer_length": len(synthesized_answer),
            "has_vector_answer": bool(vector_answer),
            "has_graph_answer": bool(graph_answer),
        },
    )
    
    return synthesized_answer


@opik.track(flush=True)
async def generate_ui_response(question: str) -> str | None:
    """Generate response specifically for UI calls with prompt optimization."""
    # Create a trace for UI calls
    opik_context.update_current_trace(
        name="UI Query",
        input={"question": question},
        metadata={
            "source": "ui",
            "timestamp": datetime.now().isoformat(),
        },
        tags=["rag", "ui", "fhir", "healthcare"]
    )
    
    # Use the same logic as generate_response but without question_number
    return await generate_response(question, question_number=None)

@opik.track(flush=True)
async def generate_ui_response_with_details(question: str) -> tuple[str | None, str, str]:
    """Generate response with vector and graph answers for UI calls."""
    # Create a trace for UI calls
    opik_context.update_current_trace(
        name="UI Query with Details",
        input={"question": question},
        metadata={
            "source": "ui",
            "timestamp": datetime.now().isoformat(),
        },
        tags=["rag", "ui", "fhir", "healthcare"]
    )
    
    # Get vector and graph answers
    vector_answer, graph_answer, entities = await run_hybrid_rag(question, question_number=None)
    
    # Synthesize the final answer
    synthesized_answer = await synthesize_answers(question, vector_answer, graph_answer, entities, question_number=None)
    
    return synthesized_answer, vector_answer, graph_answer






@opik.track(flush=True)
async def run_evaluation() -> None:
    """Run the evaluation suite with predefined questions."""
    questions = [
        "What are the full names of the patients treated by the practitioner named Josef Klein?",
        "How many patients with the last name 'Rosenbaum' received multiple immunizations?",
        "Do any patients have the email address 'joseph.klein@example.com'? If so, what is their full name and what is the full name of the practitioner who treated them?"
        "Did the practitioner 'Arla Fritsch' treat more than one patient?",
        "What are the unique categories of substances patients are allergic to?",
        "How many patients were born in between the years 1990 and 2000?",
        "How many patients were immunized after January 1, 2022?",
        "Which practitioner treated the most patients? Return their full name and how many patients they treated.",
        "Is the patient ID 45 allergic to the substance 'shellfish'? If so, what city and state do they live in, and what is the full name of the practitioner who treated them?",
        "How many patients are immunized for influenza?",
        "How many substances cause allergies in the category 'food'?",
    ]
    
    # Create the top-level trace for the entire evaluation suite
    opik_context.update_current_trace(
        name="Prompt Optimization Experiment",
        input={"total_questions": len(questions)},
        metadata={
            "evaluation_type": "full_suite",
            "total_questions": len(questions),
        },
        tags=["rag", "evaluation", "fhir", "healthcare", "suite"]
    )
    
    # Get number of questions to evaluate, default to all questions
    num_questions = int(os.environ.get("NUM_EVAL_QUESTIONS", len(questions)))
    
    # Ensure num_questions doesn't exceed available questions
    num_questions = min(num_questions, len(questions))
    
    for i, question in enumerate(questions[:num_questions], 1):
        result = await generate_response(question, question_number=i)
        logger.info(f"Answer {i}: {result}")
        logger.info("-" * 80)
    
    # Display dataset statistics after evaluation
    logger.info("\n" + "=" * 80)
    logger.info("COMBINED DATASET STATISTICS")
    logger.info("=" * 80)
    stats = await prompt_optimizer.get_dataset_stats()
    
    if isinstance(stats, dict) and "error" not in stats:
        logger.info(f"Total items: {stats.get('total_items', 0)}")
        logger.info("\nMetrics:")
        metrics = stats.get('metrics', {})
        for metric_name, metric_stats in metrics.items():
            logger.info(f"\n  {metric_name.upper()}:")
            if isinstance(metric_stats, dict):
                logger.info(f"    Count: {metric_stats.get('count', 0)}")
                logger.info(f"    Average: {metric_stats.get('average', 0):.3f}")
                logger.info(f"    Highest: {metric_stats.get('highest', 0):.3f}")
                logger.info(f"    Lowest: {metric_stats.get('lowest', 0):.3f}")
                logger.info(f"    Threshold: {metric_stats.get('threshold', 0):.3f}")
                logger.info(f"    Above threshold: {metric_stats.get('items_above_threshold', 0)}")
    else:
        logger.info(f"Dataset stats: {stats}")
    logger.info("=" * 80)


if __name__ == "__main__":
    # Run evaluation by default
    asyncio.run(run_evaluation()) 