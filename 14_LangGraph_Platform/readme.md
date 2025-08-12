<p align = "center" draggable=”false” ><img src="https://github.com/AI-Maker-Space/LLM-Dev-101/assets/37101144/d1343317-fa2f-41e1-8af1-1dbb18399719" 
     width="200px"
     height="auto"/>
</p>

## <h1 align="center" id="heading">Session 14: Build & Serve Agentic Graphs with LangGraph</h1>

| 🤓 Pre-work | 📰 Session Sheet | ⏺️ Recording     | 🖼️ Slides        | 👨‍💻 Repo         | 📝 Homework      | 📁 Feedback       |
|:-----------------|:-----------------|:-----------------|:-----------------|:-----------------|:-----------------|:-----------------|
| – | – | – | – | You are here! | – | – |

# Build 🏗️

Run the repository and complete the following:

- 🤝 Breakout Room Part #1 — Building and serving your LangGraph Agent Graph
  - Task 1: Getting Dependencies & Environment
    - Configure `.env` (OpenAI, Tavily, optional LangSmith)
  - Task 2: Serve the Graph Locally
    - `uv run langgraph dev` (API on http://localhost:2024)
  - Task 3: Call the API
    - `uv run test_served_graph.py` (sync SDK example)
  - Task 4: Explore assistants (from `langgraph.json`)
    - `agent` → `simple_agent` (tool-using agent)
    - `agent_helpful` → `agent_with_helpfulness` (separate helpfulness node)

- 🤝 Breakout Room Part #2 — Using LangGraph Studio to visualize the graph
  - Task 1: Open Studio while the server is running
    - https://smith.langchain.com/studio?baseUrl=http://localhost:2024
  - Task 2: Visualize & Stream
    - Start a run and observe node-by-node updates
  - Task 3: Compare Flows
    - Contrast `agent` vs `agent_helpful` (tool calls vs helpfulness decision)

<details>
<summary>🚧 Advanced Build 🚧 (OPTIONAL - <i>open this section for the requirements</i>)</summary>

- Create and deploy a locally hosted MCP server with FastMCP.
- Extend your tools in `tools.py` to allow your LangGraph to consume the MCP Server.
</details>

# Ship 🚢

- Running local server (`langgraph dev`)
- Short demo showing both assistants responding

# Share 🚀
- Walk through your graph in Studio
- Share 3 lessons learned and 3 lessons not learned


#### ❓ Question:

What is the purpose of the `chunk_overlap` parameter when using `RecursiveCharacterTextSplitter` to prepare documents for RAG, and what trade-offs arise as you increase or decrease its value?

##### ✅ Answer:
### Purpose of `chunk_overlap` in `RecursiveCharacterTextSplitter`

**Purpose:**  
Ensures adjacent chunks share some text so facts that cross boundaries appear together, improving retrieval recall in RAG.

**Trade-offs:**

| Overlap ↑ | Pros | Cons |
|-----------|------|------|
| Higher    | Better recall; fewer missed facts at boundaries | More tokens → higher cost & latency; duplicate content bias |
| Lower     | Lower cost/latency; more diverse retrieved chunks | Risk of splitting key facts; lower boundary recall |

**Rule of Thumb:**  
Use 10–20% of `chunk_size` as overlap (e.g., `chunk_size=600`, `chunk_overlap=60–120`) and tune based on evaluation metrics (e.g., ContextRecall vs. cost).

#### ❓ Question:

Your retriever is configured with `search_kwargs={"k": 5}`. How would adjusting `k` likely affect RAGAS metrics such as Context Precision and Context Recall in practice, and why?

##### ✅ Answer:

### Effect of `k` on RAGAS Metrics

**`k` = number of chunks retrieved per query.**

| k Change | Likely Effect on RAGAS Metrics | Reason |
|----------|--------------------------------|--------|
| Increase | **Context Recall ↑** (more relevant chunks retrieved), **Context Precision ↓** (more irrelevant chunks included) | Larger pool raises chance of including all needed evidence, but also more noise |
| Decrease | **Context Precision ↑** (fewer irrelevant chunks), **Context Recall ↓** (higher risk of missing evidence) | Smaller pool keeps only the most relevant chunks, but may drop key boundary facts |

**Trade-off:**  
- High `k` → better completeness, worse precision.  
- Low `k` → better precision, worse completeness.  

**Tip:**  
Tune `k` alongside chunk size/overlap and use evaluation to find the sweet spot for your task.

#### ❓ Question:

Compare the `agent` and `agent_helpful` assistants defined in `langgraph.json`. Where does the helpfulness evaluator fit in the graph, and under what condition should execution route back to the agent vs. terminate?

##### ✅ Answer:

### `agent` vs `agent_helpful` (from `langgraph.json`)
- **agent →** uses `simple_agent` graph (tool calls or end).
- **agent_helpful →** uses `agent_with_helpfulness` graph (adds a post-response helpfulness check).

### Where the helpfulness evaluator sits
- After the **agent** model runs, if there are **no tool calls**, route to **`helpfulness`** node; otherwise go to **`action`** (ToolNode).
- Edges: `agent → action|helpfulness`; then `helpfulness → (continue|end)`.

### When to loop back vs. terminate
- The helpfulness node emits `HELPFULNESS:Y` or `HELPFULNESS:N` (and guards with a loop-limit `HELPFULNESS:END`).
- **If `Y` → terminate**; **if `N` → route back to `agent`**; **if `END` → terminate**.

### Contrast with the simple agent
- Simple agent: if the last message has **tool calls → `action`**; else **END** (no helpfulness check).
