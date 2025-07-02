Agentic Workflows for Graph RAG
================

### ODSC Agentic AI Summit 2025 Workshop

By GraphGeeks

----

:spiral_calendar:  July 16 - 31, 2025

:world_map:        Virtual

:writing_hand:     [AI Summit Track](https://www.summit.ai/#Tracks)

----

## All you really need to know

- Python
- How to use the terminal

## Instructors

* Amy Hodler
* David Hughes
* Prashanth Rao
* Dennis Irorere

## Dataset

This workshop uses a dataset of 2,726 FHIR records of patients and their notes. The dataset is obtained
from this [Hugging Face dataset](https://huggingface.co/datasets/kishanbodybrain/test-fhir/tree/main/data)
and preprocessed using the script `create_dataset.py`. This creates the following two newline-delimited
JSON files:

- Raw data: 2,726 notes in unstructured text format, output to `data/note.jsonl`
- Evaluation data: 2,726 FHIR JSON records, output to `data/fhir.jsonl`

## Components

### Graph construction

Our first goal is to build a Graph RAG system that uses a knowledge graph constructed from
the raw data (patient notes) in the `data/note.jsonl` file. The information extraction pipeline
is powered by [BAML](https://www.boundaryml.com/), a programming language for obtaining high-quality
structured outputs from LLMs. The evaluation data in `data/fhir.jsonl` is used to evaluate the
quality of results from the information extraction pipeline in BAML.

Once the graph is created, we will build a Graph RAG pipeline (also powered by BAML) that uses the
graph to answer questions about the patient data.

### Agents & workflow orchestration

Our next goal is to add agentic components to the Graph RAG system to improve the quality of the
answers and to make the system more robust. We will use a variety of tools to build, monitor, and
evaluate the agents.

### End-to-end evaluation

TBD.

