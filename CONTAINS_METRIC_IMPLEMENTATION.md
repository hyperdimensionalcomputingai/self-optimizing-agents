# Contains Metric Implementation - DO NOT REMOVE

⚠️ **CRITICAL**: This Contains metric implementation is essential and should NOT be removed during development.

## Overview

The Contains metric evaluates whether the AI-generated response contains the key entities that were extracted from the user's question. This provides a measure of whether the response actually addresses the entities mentioned in the user's query.

## Implementation Flow

### 1. Entity Extraction (`extract_entity_keywords`)
```python
# In src/self_optimizing_agents.py (lines 320-340)
async def extract_entity_keywords(question: str, pruned_schema_xml: str):
    entities = await track_baml_call(
        b.ExtractEntityKeywords,
        "extract_entity_keywords_collector", 
        "extract_entity_keywords",
        question,
        pruned_schema_xml,
        return_collector=True
    )
    
    # Convert entities to string for Contains metric
    entities_str = "\n".join([f"- key: {entity.key}\n  value: {entity.value}" for entity in entities])
    logger.info(f"Checking Contains metric for entities: {entities_str}")
    logger.info(f"Extracted {len(entities)} entities for Contains metric evaluation")
    
    return entities
```

### 2. Entity Flow Through Pipeline
```python
# Entities are passed through the entire RAG pipeline:
# run_hybrid_rag() → extract_entity_keywords() → returns entities
# generate_response() → calls run_hybrid_rag() → passes entities to synthesize_answers()
# generate_ui_response_with_details() → same flow
```

### 3. Contains Metric Addition (`synthesize_answers`)
```python
# In src/self_optimizing_agents.py (lines 555-580)
metrics_list = [
    {"type": "Hallucination", "params": {"model": "openrouter/openai/gpt-4o"}},
    {"type": "AnswerRelevance", "params": {"model": "openrouter/openai/gpt-4o"}},
    {"type": "Moderation", "params": {"model": "openrouter/openai/gpt-4o"}},
    {"type": "Usefulness", "params": {"model": "openrouter/openai/gpt-4o"}},
]

# ⚠️ CRITICAL: Contains metric addition - DO NOT REMOVE
if entities:
    entities_str = "\n".join([f"- key: {entity.key}\n  value: {entity.value}" for entity in entities])
    metrics_list.append({
        "type": "Contains", 
        "params": {
            "reference": entities_str
        }
    })
    logger.info(f"Added Contains metric with {len(entities)} entities")
```

### 4. Contains Metric Execution (`baml_instrumentation.py`)
```python
# In src/baml_instrumentation.py (lines 138-143)
elif metric_type == "Contains":
    # Filter out 'output' and 'reference' from params as they're not constructor parameters
    constructor_params = {k: v for k, v in params.items() if k not in ["output", "reference"]}
    metric = Contains(track = True, **constructor_params)
    reference = params.get("reference", "")
    score_result = await metric.ascore(output=output, reference=reference)
```

## Key Files and Line Numbers

### 🔍 **CRITICAL SECTIONS - DO NOT MODIFY WITHOUT REVIEW**

1. **`src/self_optimizing_agents.py`**:
   - Lines 320-340: `extract_entity_keywords()` function
   - Lines 563-571: Contains metric addition in `synthesize_answers()`
   - Lines 591, 645, 648: Entity passing through pipeline

2. **`src/baml_instrumentation.py`**:
   - Lines 138-143: Contains metric execution logic

## Verification Commands

To verify the Contains metric is still implemented:

```bash
# Check for Contains metric references
grep -n "Contains.*metric" src/self_optimizing_agents.py src/baml_instrumentation.py

# Check entity extraction
grep -n "extract_entity_keywords" src/self_optimizing_agents.py

# Check entities parameter passing
grep -n "entities.*question_number" src/self_optimizing_agents.py
```

## Expected Output in Logs

When working correctly, you should see:
```
INFO - Checking Contains metric for entities: - key: practitioner\n  value: Josef Klein
INFO - Extracted 2 entities for Contains metric evaluation  
INFO - Added Contains metric with 2 entities
[DEBUG] Running metrics for span: synthesize_answers (sample_rate: 1.0)
[DEBUG] Executing Contains metric with reference: - key: practitioner...
[DEBUG] Contains metric result: ScoreResult(value=1.0, reason="Found entities")
```

## Critical Fix: Sample Rate

⚠️ **IMPORTANT**: The Contains metric was not being reported because `METRICS_SAMPLE_RATE` was set to 0.05 (5%). This has been fixed to 1.0 (100%) for development/testing to ensure all metrics are reported.

## Testing the Contains Metric

The Contains metric will evaluate whether the synthesized answer contains the entities that were extracted from the question. For example:

- **Question**: "What patients did Josef Klein treat?"
- **Extracted entities**: `[{key: "practitioner", value: "Josef Klein"}]`
- **Contains metric**: Checks if "Josef Klein" appears in the final answer
- **Score**: 1.0 if found, 0.0 if not found

## Integration with Opik

The Contains metric results are automatically:
1. Logged to Opik with other metrics
2. Included in feedback scores
3. Available for analysis in the Opik dashboard

## Why This is Critical

The Contains metric is essential because it:
1. **Validates entity preservation**: Ensures important entities from the question make it to the answer
2. **Measures relevance**: Provides objective measure of whether the answer addresses the question
3. **Enables optimization**: Allows tracking how well the RAG system preserves key information
4. **Complements other metrics**: Works alongside Hallucination, AnswerRelevance, etc.

## Maintenance Notes

- Always preserve the entity extraction and passing logic
- Keep the Contains metric addition in the metrics_list
- Maintain the BAML instrumentation handler
- Test after any changes to the RAG pipeline

**⚠️ DO NOT REMOVE OR MODIFY WITHOUT EXPLICIT APPROVAL**