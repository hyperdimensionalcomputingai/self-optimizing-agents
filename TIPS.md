# Tips to get started

If all these tools are new to you, it can seem a little daunting to get started.
Below, we suggest an entry point into what looks like a relatively complex code base
at first glance -- the best way to get started is to begin experimenting!

## BAML for structured data extraction
- Start with an empty repo, install uv and run  `uv init` to initialize the virtual environment with
BAML, Kuzu and LanceDB (run `uv sync`)
- Begin with a simple BAML schema and prompt and *immediately* test it on a few input samples. The intial BAML schema
can/will be basic, so you can get a feel for the LLM's behaviour
- Iteratively improve on the BAML schema and prompt until you are satisfied with the results. Add
assertions to the BAML tests to ensure that multiple  LLMs are tested and the promps translate reasonably
well across them.
- Once you are satisfied, import the BAML client code into Python and apply it on around 10 records.
- Export the BAML output into a JSON file (do this for 10 records or so)

## Kuzu for graph data storage and path traversals
- Create an empty Kuzu database and begin creating your graph schema
- Try to copy the data from the JSON file into the Kuzu database via Polars
DataFrame operations (Polars is recommended because it's very fast and highly scalable to larger datasets).
- Run a few Cypher queries in Kuzu to test that the data is structured
correctly and that the results make sense.
- Iterate in BAML + Kuzu as needed
- *Only* once all this works well end-to-end, scale this up to the entire dataset

## LanceDB for vector data storage and hybrid (FTS + vector) search
- Next, ingest the data into a LanceDB table
- For small data (<100K vectors), a vector index is not necessary
- Create an FTS index to be able to do keyword search
- Implement a hybrid search (FTS + vector search) retriever to test
out a few keyword queries - test that relevant results are returned
- Once you are satisfied, you can scale this up to the entire dataset

## Onward and upward!
Now that the individual pieces (structured data extraction, graph data storage and vector data storage)
are making sense, you can experiment with different ways of bringing together vector + graph retrieval!
- Hybrid RAG: Independendly retrieve from vector and graph, and combine the
results into a synthesized response.
- Graph-enhanced vector search: Use vector + FTS retrieval as an entry point to the graph nodes, and
traverse the graph up to a depth of 2-3 from there.
- Agentic RAG: Use a query router to decide whether a vector + FTS retrieval is sufficient, or if a
graph traversal is needed, and route the query to the appropriate tool as needed. Include fallbacks to handle
errors or failed retrievals so that the user doesn't get a blank response
after just a single try.
- MCP servers & additional tools: You can look at including additional MCP tools and/or REST APIs to the workflow,
such as calculator APIs, wikipedia search, etc. This can help provide adequate capabilities to the
agent to answer a wider range of queries.

## Don't forget evals!
- At each of the above stages, ensure you spend time curating an evaluation
suite of at least 20-50 queries that must pass to a sufficient degree to be considered
enough for getting the app to production.
- Some evals can be done via deterministic code (e.g., pytest test suites),
but others are subjective, and can required either a human-in-the-loop
(HITL) or an LLM-as-a-judge approach.
- Plugging in the workflow into observability tools that support OpenTelemetry can help a lot with this, so make sure to think about
these aspects early on, before scaling up the process to the entire
dataset.
- Augment the evals with real user queries from production, and
always keep an eye out for continuous improvements based on
real-world evals to improve the workflow over time. Just like Rome 🌆, a good agentic workflow is not built in one day!







