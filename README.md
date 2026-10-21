<div align="center">

# AgentLab

### Observe failures. Diagnose the harness. Patch only what is allowed. Prove the fix.

**AgentLab is a bounded harness evaluation and optimization system for AI agents.**  
When a Target Agent fails, AgentLab turns the failure into an evidence chain, selects an editable harness surface, proposes a constrained patch, and accepts it only after regression validation.

<p>
  <a href="https://agentlab-harness-optimizer.vercel.app/?template=promo"><strong>▶ Try the workflow-repair demo</strong></a>
  ·
  <a href="https://agentlab-harness-optimizer.vercel.app/?template=product&experiment=tool-contract"><strong>▶ Try tool-contract repair</strong></a>
  ·
  <a href="#quickstart"><strong>Quickstart</strong></a>
  ·
  <a href="docs/AGENTLAB_CONTRACT.md"><strong>Architecture contract</strong></a>
</p>

<p>
  <img src="https://img.shields.io/badge/Python-3.12-3776AB?logo=python&logoColor=white" alt="Python 3.12" />
  <img src="https://img.shields.io/badge/API-FastAPI-009688?logo=fastapi&logoColor=white" alt="FastAPI" />
  <img src="https://img.shields.io/badge/UI-Next.js%2014-000000?logo=nextdotjs&logoColor=white" alt="Next.js 14" />
  <img src="https://img.shields.io/badge/Optimization-Bounded-0F766E" alt="Bounded optimization" />
  <a href="https://github.com/ychen393/Agentlab-harness-optimizer/actions/workflows/ci.yml">
    <img src="https://github.com/ychen393/Agentlab-harness-optimizer/actions/workflows/ci.yml/badge.svg" alt="CI" />
  </a>
</p>

<sub>首个 Target Agent testbed：Commerce Agent · 默认 Demo 不需要外部 LLM API Key</sub>

</div>

---

## Why AgentLab?

Most agent tooling stops at **observability** or **evaluation**.

AgentLab connects those signals to a guarded improvement loop:

<table>
  <thead>
    <tr>
      <th width="24%">Capability</th>
      <th width="25%">Typical tracing / eval workflow</th>
      <th>AgentLab</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td><strong>Observe</strong></td>
      <td>Show traces, tool calls, latency, outputs</td>
      <td>Preserve the same execution evidence in <code>ExecutionTrace</code></td>
    </tr>
    <tr>
      <td><strong>Evaluate</strong></td>
      <td>Pass / fail / score</td>
      <td>Independent evaluator with evaluator-only ground truth</td>
    </tr>
    <tr>
      <td><strong>Diagnose</strong></td>
      <td>Usually manual</td>
      <td>Failure pattern → evidence-backed root cause → target harness surface</td>
    </tr>
    <tr>
      <td><strong>Repair</strong></td>
      <td>Usually manual prompt / workflow editing</td>
      <td>Bounded <code>HarnessPatch</code> on approved configuration fields only</td>
    </tr>
    <tr>
      <td><strong>Validate</strong></td>
      <td>Often rerun one example</td>
      <td>Frozen regression + held-out cases + negative controls + explicit decision</td>
    </tr>
  </tbody>
</table>

> **The core idea:** do not ask only *“Did the agent fail?”*  
> Ask **why it failed, what part of the harness is allowed to change, and whether the change survives regression testing.**

---

## One product loop

~~~mermaid
flowchart LR
    A[User Request / Scenario] --> B[Target Agent]
    B --> C[ExecutionTrace]
    C --> D[Independent Evaluation]
    D -->|fail| E[Failure Pattern]
    E --> F[Root Cause]
    F --> G{Patchable?}
    G -->|No| H[patch_unavailable]
    G -->|Yes| I[Bounded HarnessPatch]
    I --> J[Candidate AgentConfig]
    J --> K[Regression Validation]
    K --> L{Decision}
    L -->|Accept| M[Keep candidate]
    L -->|Reject / Review| N[Keep baseline]
~~~

The optimizer can modify only:

<p>
  <code>system_prompt</code>
  &nbsp;·&nbsp;
  <code>tool_description</code>
  &nbsp;·&nbsp;
  <code>context</code>
  &nbsp;·&nbsp;
  <code>workflow_config</code>
</p>

It does **not** rewrite the Target Agent source code, evaluator, benchmark ground truth, tool implementation, or model-provider configuration.

---

## Three demonstrated repair surfaces

<table>
  <thead>
    <tr>
      <th>Failure</th>
      <th>Diagnosis</th>
      <th>Patch surface</th>
      <th>Regression evidence</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td>
        <strong>Workflow stops too early</strong><br />
        CT6 / CT7 cannot reach the required eligibility step
      </td>
      <td>
        <code>workflow_step_limit</code><br />
        required next step is blocked by <code>max_steps = 2</code>
      </td>
      <td>
        <code>workflow_config</code><br />
        <code>max_steps: 2 → 3</code>
      </td>
      <td>
        <strong>5/7 → 7/7</strong><br />
        0 fixed-case regressions · <strong>ACCEPT</strong>
      </td>
    </tr>
    <tr>
      <td>
        <strong>Tool argument violates contract</strong><br />
        <code>search_products</code> receives <code>product_name</code> instead of <code>query</code>
      </td>
      <td>
        <code>tool_argument_schema_failure</code><br />
        registered argument contract is not explicit in the model-facing tool description
      </td>
      <td>
        <code>tool_description</code><br />
        expose the registered <code>{"query":"&lt;string&gt;"}</code> contract
      </td>
      <td>
        <strong>8/12 → 12/12</strong><br />
        TD2–TD4 held out · TD5 control preserved · CT1–CT7 preserved
      </td>
    </tr>
    <tr>
      <td>
        <strong>Product vs. promotion routing ambiguity</strong><br />
        coverage case EX2 selects the wrong tool
      </td>
      <td>
        deterministic path is not patchable through ignored harness fields;<br />
        separate controlled router is harness-sensitive
      </td>
      <td>
        <code>system_prompt</code><br />
        add one explicit negated-intent routing constraint
      </td>
      <td>
        controlled V2 → V3:<br />
        <strong>15/16 → 16/16</strong> · 0 regressions · <strong>ACCEPT</strong>
      </td>
    </tr>
  </tbody>
</table>

<sub>
Evidence boundary: workflow-step repair is deterministic. Tool-contract and routing experiments use provider-independent controlled routers to establish causal sensitivity to the harness. These results are not universal claims about every external model.
</sub>

---

## Demo walkthrough

### 1 · Workflow repair

Open the hosted demo with the promotion template:

**Promotion eligibility → Run → Diagnose → Patch → Regression**

~~~text
search_policy succeeds
        ↓
check_eligibility is required next
        ↓
workflow.max_steps = 2 blocks the step
        ↓
Root Cause → workflow_config
        ↓
HarnessPatch → max_steps 2 → 3
        ↓
same frozen CT1–CT7 rerun
        ↓
5/7 → 7/7 · 0 regressions · ACCEPT
~~~

### 2 · Tool-contract repair

Under **Product Lookup / 商品信息查询**, choose **Failure replay: tool argument contract**.

~~~text
TD1 Seed Failure
search_products({"product_name": ...})
        ↓
registered contract requires {"query": ...}
        ↓
FailurePattern → tool_argument_schema_failure
        ↓
Root Cause → tool_description
        ↓
one bounded patch is generated
        ↓
TD2–TD4 held-out validation
TD5 negative control
CT1–CT7 frozen capability protection
        ↓
8/12 → 12/12 · 0 regressions · ACCEPT
~~~

Why the validation design matters:

<table>
  <thead>
    <tr>
      <th>Group</th>
      <th>Role</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td><strong>TD1</strong></td>
      <td>Seed case. The only case used to derive the failure evidence and patch.</td>
    </tr>
    <tr>
      <td><strong>TD2–TD4</strong></td>
      <td>Held-out cases. They do not participate in patch generation.</td>
    </tr>
    <tr>
      <td><strong>TD5</strong></td>
      <td>Negative control. It already satisfies the contract and must remain correct.</td>
    </tr>
    <tr>
      <td><strong>CT1–CT7</strong></td>
      <td>Frozen existing capability. They protect the accepted Commerce behavior from regression.</td>
    </tr>
  </tbody>
</table>

---

## Architecture

<table>
  <thead>
    <tr>
      <th width="50%">AgentLab Core</th>
      <th>Commerce Target Agent testbed</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td>
        <ul>
          <li>Requirement parsing</li>
          <li>Benchmark generation</li>
          <li>Runner + execution tracing</li>
          <li>Independent evaluation contracts</li>
          <li>Failure classification</li>
          <li>Root-cause analysis</li>
          <li>Patchability + bounded patch strategies</li>
          <li>Regression comparison + decision</li>
        </ul>
      </td>
      <td>
        <ul>
          <li>Commerce Agent</li>
          <li>Deterministic product and promotion tools</li>
          <li>Registered Commerce scenarios</li>
          <li>Immutable evaluator-only ground truth</li>
          <li>Adaptive challenges</li>
          <li>Coverage-driven exploration</li>
          <li>Controlled harness-sensitive experiments</li>
        </ul>
      </td>
    </tr>
  </tbody>
</table>

The Target Agent receives the request and its current <code>AgentConfig</code>.  
The evaluator receives the trace plus ground truth. **Ground truth is never supplied to the Target Agent.**

<details>
<summary><strong>Project structure</strong></summary>

<br />

| Path | Responsibility |
| --- | --- |
| `app/schemas/` | Pydantic contracts across module boundaries |
| `app/requirement/` | Requirement parsing |
| `app/benchmark/` | Benchmark generation |
| `app/runner/` | Target Agent execution and trace ownership |
| `app/debugger/` | Failure mining, contract checks, root-cause analysis |
| `app/optimizer/` | Patch strategies, patchability, patch application |
| `app/regression/` | Baseline vs candidate comparison |
| `app/targets/commerce/` | Commerce Agent, tools, scenarios, evaluator, challenge experiments |
| `api/main.py` | FastAPI adapter for run / diagnose / patch / regression |
| `frontend/` | Next.js product UI |
| `tests/` | Unit and integration tests |
| `docs/AGENTLAB_CONTRACT.md` | MVP engineering contract and source-of-truth boundaries |

</details>

---

<a id="quickstart"></a>

## Quickstart

### Backend

~~~bash
python -m venv .venv

# macOS / Linux
source .venv/bin/activate

# Windows PowerShell
# .\.venv\Scripts\Activate.ps1

python -m pip install -r requirements.txt
python -m pytest -q
python -m uvicorn api.main:app --reload --port 8001
~~~

### Frontend

In a second terminal:

~~~bash
cd frontend
npm ci
npm run dev -- --port 3000
~~~

Open **http://localhost:3000**.

### Production checks

~~~bash
# repository root
python -m pytest -q

# frontend/
npm run lint
npm run typecheck
npm run build
~~~

The GitHub Actions workflow runs the Python suite plus frontend lint, type-check, and production build on pushes to `main` and `feature/**`.

---

## API

<details>
<summary><strong>HTTP surface</strong></summary>

<br />

| Endpoint | Purpose |
| --- | --- |
| `GET /api/health` | Health check |
| `GET /api/benchmarks` | Inspect fixed, adaptive, and coverage-driven benchmark families |
| `POST /api/run` | Execute a request and return trace + available evaluation |
| `POST /api/diagnose` | Derive failure pattern and root-cause evidence |
| `POST /api/patch` | Propose a bounded `HarnessPatch` |
| `POST /api/regression` | Apply candidate patch and compare baseline vs candidate |
| `GET /api/runs` | Current-process run history |
| `GET /api/failures` | Current-process diagnosed failures |
| `GET /api/patches` | Current-process patches |
| `GET /api/regressions` | Current-process regression decisions |

</details>

---

## Evidence, safety, and claim boundaries

<details>
<summary><strong>What is frozen during regression?</strong></summary>

- registered scenarios / benchmark inputs
- evaluator logic
- evaluator-only ground truth
- model / router mechanism for the comparison
- business tool implementations
- unrelated harness surfaces

The candidate may change only the surface justified by the diagnosed bounded patch.

</details>

<details>
<summary><strong>What happens when AgentLab cannot justify a patch?</strong></summary>

It returns <code>patch_unavailable</code>.

A failure is not sufficient evidence by itself. The observed execution path must actually consume an allowed harness surface that can plausibly address the diagnosed cause.

</details>

<details>
<summary><strong>Deterministic vs. controlled vs. external-model evidence</strong></summary>

**Deterministic evidence** covers Commerce fixtures, tools, evaluation, the workflow-step repair, challenge generation, coverage analysis, and patchability checks.

**Controlled-router evidence** keeps one provider-independent router mechanism fixed between baseline and candidate while changing only the allowed harness configuration. It is used to demonstrate causal sensitivity to the patch.

**External-model evidence** is optional. The repository includes an OpenAI-compatible adapter and smoke-test scripts, but no external-model improvement claim is required for the normal demo or test suite.

</details>

<details>
<summary><strong>Current limitations</strong></summary>

- Commerce Agent is the only integrated Target Agent testbed.
- Run / failure / patch / regression history is stored in backend process memory, not a durable database.
- On serverless deployments, in-memory history may disappear after restarts or may not be shared across instances.
- The normal demo does not require a live external LLM.
- Controlled-router evidence does not prove universal improvement across arbitrary providers or domains.
- AgentLab does not autonomously rewrite application source code.
- The MVP does not include production authentication, durable multi-user persistence, model fine-tuning, MCTS, LangGraph orchestration, or an open-ended self-modification loop.

</details>

---

## Optional external-model smoke test

The adapter supports an OpenAI-compatible <code>/chat/completions</code> endpoint.

~~~powershell
$env:AGENTLAB_LLM_API_KEY = "your-api-key"
$env:AGENTLAB_LLM_BASE_URL = "https://your-provider.example/v1"
$env:AGENTLAB_LLM_MODEL = "your-model-name"
$env:AGENTLAB_LLM_TIMEOUT_SECONDS = "30"

python scripts/real_model_smoke.py --repetitions 5
~~~

Never commit real credentials.

---

## Design principles

- **Independent evaluation:** the Target Agent never evaluates itself.
- **Evidence before patching:** every repair must be supported by an observed failure and root cause.
- **Bounded optimization:** only approved harness configuration surfaces are editable.
- **Frozen regression:** the candidate is compared against the same protected cases and evaluator.
- **Preserve the baseline:** each candidate is versioned; an unverified patch does not overwrite the accepted configuration.
- **No fabricated progress:** if a path is not patchable, AgentLab says so.
- **Separate evidence levels:** deterministic, controlled, and external-model claims remain distinct.

---

<div align="center">

### Make every Agent change explainable, bounded, and testable.

**让每一次 Agent 改进都有证据、有边界、可回归验证。**

</div>
