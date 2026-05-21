# LedgerMind

A multi-agent personal financial advisory system that orchestrates four specialist agents — a Compliance Advisor, Financial Analyst, Risk Auditor, and Investment Advisor — to answer user questions with explicit consensus, traceable calculations, and audit-ready outputs.

Built as a demonstration of responsible multi-agent AI design for regulated financial use cases: explainability, abstention, calibrated confidence, and disagreement surfacing.

---

## What It Does

A user asks a financial question in natural language. Four specialist agents reason in parallel, each pulling their own slice of the user's financial data and retrieving from a tax and compliance knowledge base. The agents either produce a structured verdict with a confidence score and citations, or they abstain if the question is outside their specialty.

A Disagreement & Consensus Handler then evaluates the four verdicts, an Uncertainty Gate filters low-confidence non-abstentions, and a Mediator agent synthesizes the responses into a single user-facing answer. Disagreements between agents are surfaced explicitly rather than hidden. Every step is written to an audit log.

---

## Architecture

```
USER QUERY + FINANCIAL DATA
         |
         v
  +-------------+
  |   RAG Engine | (mocked keyword retrieval over tax & compliance KB)
  +-------------+
         |
         v
  +---------------------------------------------------+
  |             FOUR SPECIALIST AGENTS                |
  |  (run in parallel via ThreadPoolExecutor)         |
  +---------------------------------------------------+
  | CA Agent  | Analyst  | Risk Agent | Investment   |
  | (tax &    | (spending| (anomalies | (allocation  |
  |  compl.)  |  & cash  |  & fraud)  |  & div.)     |
  |           |  flow)   |            |              |
  +-----------+----------+------------+--------------+
         |          |           |             |
         v          v           v             v
  +---------------------------------------------------+
  |          DISAGREEMENT & CONSENSUS HANDLER         |
  |  (computes agreement metrics, surfaces conflicts) |
  +---------------------------------------------------+
         |
         v
  +---------------------------------------------------+
  |           UNCERTAINTY GATE                         |
  |  (low-confidence non-abstentions become abstains) |
  +---------------------------------------------------+
         |
         v
  +---------------------------------------------------+
  |        CONSENSUS LOGIC & MEDIATOR                  |
  |  (LLM call synthesizing all agent responses)      |
  +---------------------------------------------------+
         |
         v
  AUDIT-READY OUTPUT
  - Consensus summary
  - Key findings
  - Disagreements highlighted
  - Recommended actions
  - Aggregated citations
  - Full audit log file (.jsonl)
```

---

## Key Design Decisions

**Deterministic calculations outside the LLM.** All numerical work (anomaly detection, allocation analysis, performance computation) happens in pure Python before any LLM call. Agents receive precomputed values and reason about them, but never do arithmetic themselves. This eliminates a major class of hallucination.

**Abstention is a first-class output.** Every agent has a strict scope and is instructed to abstain when a question is outside its specialty. The evaluation framework specifically measures whether agents correctly abstain on out-of-scope questions, not just whether they answer well on in-scope ones.

**Confidence calibration with an uncertainty gate.** Agents produce a confidence score on every response. A two-stage gate then catches low-confidence responses: agents self-abstain when confident below 0.4, and the orchestrator re-flags any responses that slip through.

**Disagreements are surfaced.** The Mediator agent is explicitly instructed to highlight substantive disagreements between specialists rather than averaging them away. This is critical for the auditability story.

**Append-only audit log.** Every retrieval, tool call, agent response, consensus event, and final output is written as a JSON Lines event to a session log file. Any final answer can be reconstructed from the log alone.

---

## Tech Stack

- **Orchestration:** LangGraph (state machine with parallel node execution)
- **LLM:** Anthropic Claude Sonnet 4.5
- **Knowledge retrieval:** Mocked keyword-based RAG (production swap-in would be Chroma or Pinecone)
- **UI:** Streamlit with custom editorial styling
- **Data:** Pandas, NumPy
- **Logging:** JSON Lines audit format

---

## Getting Started

### Prerequisites

- Python 3.11 or higher
- An Anthropic API key (get one at https://console.anthropic.com)

### Installation

```bash
git clone <repo-url>
cd ledgermind

# Set up virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env and add your ANTHROPIC_API_KEY
```

### Generate Sample Data

```bash
python -m utils.data_generator
```

This generates six months of synthetic transactions, a sample portfolio, and supporting financial records in `./sample_data/`.

### Run the Streamlit App

```bash
streamlit run app.py
```

Open http://localhost:8501 in your browser.

### Run the Evaluation Suite

```bash
python run_evaluation.py
```

This runs the golden test cases through the orchestrator and prints metrics covering scoping correctness, citation coverage, and calculation grounding.

---

## Evaluation Metrics

The evaluation framework measures three properties:

1. **Scoping correctness.** When a question is outside an agent's specialty, does the agent correctly abstain? When the question is in scope, does it respond?

2. **Citation coverage.** Do responding agents cite knowledge base sources, or do they answer without grounding?

3. **Calculation grounding.** Do responding agents reference precomputed numerical results in their reasoning, or do they invent figures?

The overall score is a weighted combination (50% scoping, 25% citation, 25% grounding). A test passes if the overall score is at or above 0.7.

---

## Project Structure

```
ledgermind/
├── app.py                          # Streamlit entrypoint
├── run_evaluation.py               # Eval runner
├── requirements.txt
├── .env.example
├── README.md
├── agents/
│   ├── base_agent.py               # SpecialistAgent base class
│   ├── specialists.py              # CA, Analyst, Risk, Investment
│   ├── prompts.py                  # Centralized system prompts
│   └── orchestrator.py             # LangGraph state machine
├── tools/
│   ├── llm_client.py               # Claude API wrapper
│   ├── rag_engine.py               # Mock RAG retrieval
│   └── calculations.py             # Deterministic financial math
├── utils/
│   ├── audit_log.py                # Session audit logger
│   └── data_generator.py           # Synthetic data generation
├── evaluation/
│   └── eval_framework.py           # Test cases and scoring
├── ui/
│   ├── components.py               # Streamlit components
│   └── styles.py                   # CSS theming
├── knowledge_base/
│   └── tax_and_compliance_kb.json  # Mocked KB content
└── sample_data/                    # Generated synthetic data
```

---

## Disclaimer

LedgerMind is an educational demonstration of multi-agent financial reasoning. All outputs are informational only and do not constitute tax, investment, or legal advice. Sample data is entirely synthetic; no real financial information is processed.
