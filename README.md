<div align="center">
  <h1>AgentLab</h1>
  <p><strong>Observe → Diagnose → Patch → Validate</strong></p>
  <p>A reproducible, bounded harness evaluation and optimization workbench for AI agents.</p>
  <p>一个可复现、受约束的 AI Agent Harness 评估与优化实验工作台。</p>
  <p>
    <img src="https://img.shields.io/badge/Python-3.12-3776AB?logo=python&logoColor=white" alt="Python 3.12" />
    <img src="https://img.shields.io/badge/API-FastAPI-009688?logo=fastapi&logoColor=white" alt="FastAPI" />
    <img src="https://img.shields.io/badge/UI-Next.js%2014-000000?logo=nextdotjs&logoColor=white" alt="Next.js 14" />
    <img src="https://img.shields.io/badge/Optimization-Bounded-0F766E" alt="Bounded optimization" />
    <a href="https://github.com/ychen393/Agentlab-harness-optimizer/actions/workflows/ci.yml">
      <img src="https://github.com/ychen393/Agentlab-harness-optimizer/actions/workflows/ci.yml/badge.svg" alt="CI" />
    </a>
  </p>
  <p>
    <a href="https://agentlab-harness-optimizer.vercel.app/">Hosted demo</a>
    ·
    <a href="docs/AGENTLAB_CONTRACT.md">MVP engineering contract</a>
  </p>
</div>

---

> **The idea / 核心想法**
>
> AgentLab does more than label an agent response as pass or fail. It traces the execution, evaluates it against independent ground truth, diagnoses an evidence-backed cause, proposes a limited change to the agent's **harness**, and checks the candidate against regression tests.
>
> AgentLab 不直接改写 Agent 源代码。它根据执行证据定位失败原因，只修改允许调整的 Harness 配置，再用冻结测试集验证改动是否真正有效、有没有破坏原有能力。

## At a glance

<table>
  <thead>
    <tr>
      <th>Question</th>
      <th>AgentLab's answer</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td><strong>What is being improved?</strong></td>
      <td>The configurable harness around a Target Agent — not the agent's application source code.</td>
    </tr>
    <tr>
      <td><strong>What is the first testbed?</strong></td>
      <td>Commerce Agent, with deterministic product and promotion tools, registered scenarios, and independent ground truth.</td>
    </tr>
    <tr>
      <td><strong>What can a patch change?</strong></td>
      <td><code>system_prompt</code>, <code>tool_description</code>, <code>context</code>, or <code>workflow_config</code> only.</td>
    </tr>
    <tr>
      <td><strong>How is a change accepted?</strong></td>
      <td>Run the baseline and candidate on the same frozen cases, compare their evaluation results, and make an explicit <code>ACCEPT</code>, <code>REJECT</code>, or <code>REVIEW</code> decision.</td>
    </tr>
    <tr>
      <td><strong>Does the normal demo need an API key?</strong></td>
      <td>No. The default evidence path uses deterministic fixtures and controlled routers. External-model testing is optional.</td>
    </tr>
  </tbody>
</table>

## The workflow

<p align="center"><strong>Request / Scenario → Execution Trace → Evaluation → Failure Pattern → Root Cause → Harness Patch → Regression Decision</strong></p>

<table>
  <thead>
    <tr>
      <th>Stage</th>
      <th>What happens</th>
      <th>Evidence you can inspect</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td><strong>01 · Run</strong></td>
      <td>Execute a registered scenario or a user request through the Target Agent.</td>
      <td>Tool calls, arguments, outputs, execution errors, and an <code>ExecutionTrace</code>.</td>
    </tr>
    <tr>
      <td><strong>02 · Evaluate</strong></td>
      <td>Compare the observed behavior with evaluator-only ground truth.</td>
      <td>Per-case pass/fail results and the specific checks that failed.</td>
    </tr>
    <tr>
      <td><strong>03 · Diagnose</strong></td>
      <td>Group failures and trace the likely cause back to evidence.</td>
      <td><code>FailurePattern</code>, <code>RootCauseAnalysis</code>, observed versus required tool arguments.</td>
    </tr>
    <tr>
      <td><strong>04 · Patch</strong></td>
      <td>Propose a bounded change only when the evidence supports an editable harness fix.</td>
      <td>Before/after values, rationale, expected effect, and regression risk.</td>
    </tr>
    <tr>
      <td><strong>05 · Validate</strong></td>
      <td>Apply the candidate configuration and rerun the frozen test suite.</td>
      <td>Baseline/candidate results, improved cases, regressions, and a final decision.</td>
    </tr>
  </tbody>
</table>

Adaptive challenges and coverage-driven exploration extend this loop by generating additional tests from observed weaknesses. They remain separate from the fixed regression set, so the evidence from each test family can be reviewed independently.

## Verified experiment results

These results come from the repository's deterministic fixtures and controlled-router experiments. They are **not** claims that every external model will behave the same way.

<table>
  <thead>
    <tr>
      <th>Experiment</th>
      <th>Observed failure</th>
      <th>Bounded change</th>
      <th>Validation result</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td><strong>1. Workflow-step limit</strong><br />Fixed cases CT1–CT7</td>
      <td>V1 passes <strong>5/7</strong>. CT6 and CT7 need a third tool step, but the workflow limit is 2.</td>
      <td><code>workflow_config</code>: <code>max_steps 2 → 3</code>.</td>
      <td>V2 passes <strong>7/7</strong>; no fixed-case regressions; decision <strong>ACCEPT</strong>.</td>
    </tr>
    <tr>
      <td><strong>2. Product-versus-promotion routing</strong><br />Coverage case EX2</td>
      <td>EX2 exposes ambiguity between a product lookup and a promotion lookup. The deterministic fallback path does not consume the relevant harness instructions, so a prompt patch is correctly reported as unavailable on that path.</td>
      <td>In a separate controlled mock-router experiment, add one negated-intent routing instruction to <code>system_prompt</code>.</td>
      <td>Controlled V2 → V3 validation improves from <strong>15/16 to 16/16</strong> across CT + AC + EX cases, with no regressions; decision <strong>ACCEPT</strong>.</td>
    </tr>
    <tr>
      <td><strong>3. Tool-argument contract</strong><br />Seed TD1; validation TD2–TD5</td>
      <td>The router selects <code>search_products</code> but supplies <code>product_name</code>, while the registered tool contract requires <code>query</code>.</td>
      <td>Update only <code>tool_description</code> to make the registered argument format explicit.</td>
      <td>Combined frozen suite improves from <strong>8/12 to 12/12</strong>; TD2–TD4 are held-out cases, TD5 is a negative control, and CT1–CT7 protect existing behavior; decision <strong>ACCEPT</strong>.</td>
    </tr>
  </tbody>
</table>

### Tool-contract repair: one example, the same workflow

The tool-contract experiment is **not a separate optimization engine**. It uses the same Run → Evaluate → Diagnose → Patch → Regression flow and the same core runner, evaluator, failure analysis, bounded patch application, and regression comparator.

<table>
  <thead>
    <tr>
      <th>Step</th>
      <th>What the experiment demonstrates</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td><strong>Seed failure · TD1</strong></td>
      <td><code>Find Running Shoes.</code> triggers <code>search_products</code>, but the observed argument key is <code>product_name</code> rather than the required <code>query</code>.</td>
    </tr>
    <tr>
      <td><strong>Evidence-based diagnosis</strong></td>
      <td>The failure is classified as a tool-argument schema mismatch. The evidence points to the tool description, not the business policy, evaluator, or ground truth.</td>
    </tr>
    <tr>
      <td><strong>Bounded patch</strong></td>
      <td>Only the tool description is changed to expose the registered argument contract. The tool implementation, argument schema, evaluator, and ground truth are not rewritten.</td>
    </tr>
    <tr>
      <td><strong>Held-out validation</strong></td>
      <td>TD2–TD4 test the repair on unseen product requests, including a Chinese request. TD5 is a negative control that already follows the contract.</td>
    </tr>
    <tr>
      <td><strong>Regression protection</strong></td>
      <td>CT1–CT7 are rerun alongside TD1–TD5. The candidate must improve the contract cases without breaking the existing Commerce checks.</td>
    </tr>
  </tbody>
</table>

To try it in the product UI, choose **Product Lookup / 商品信息查询 → Tool Contract Repair / 商品工具契约修复**, run the example, inspect the execution trace, then proceed through diagnosis, patch review, and regression validation.

## Architecture and safety boundaries

<table>
  <thead>
    <tr>
      <th>AgentLab Core</th>
      <th>Initial Target Agent testbed</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td>
        <ul>
          <li>Requirement parsing and benchmark generation</li>
          <li>Runner and execution tracing</li>
          <li>Independent evaluation contracts</li>
          <li>Failure classification and root-cause analysis</li>
          <li>Bounded patch strategies and patchability checks</li>
          <li>Regression comparison and decision</li>
        </ul>
      </td>
      <td>
        <ul>
          <li>Commerce Agent and deterministic tools</li>
          <li>Product and promotion policy fixtures</li>
          <li>Registered Commerce scenarios and ground truth</li>
          <li>Adaptive challenges and coverage exploration</li>
          <li>Commerce-specific patch strategies</li>
        </ul>
      </td>
    </tr>
  </tbody>
</table>

The Target Agent receives the test case and its current harness configuration. **Evaluator-only ground truth is kept outside the Target Agent**, so it cannot use the expected answer to produce its own result.

Key safeguards:

- **Bounded changes:** only <code>system_prompt</code>, <code>tool_description</code>, <code>context</code>, and <code>workflow_config</code> are eligible for optimization.
- **Frozen comparisons:** baseline and candidate use the same registered test cases and evaluator.
- **Versioned candidates:** a candidate is a separate configuration; the baseline is preserved.
- **No invented fixes:** unsupported failure paths return <code>patch_unavailable</code> rather than fabricating a patch.
- **Negative controls and held-out cases:** where the experiment defines them, they are kept distinct from the seed case used to derive a patch.
- **Explicit evidence labels:** deterministic results, controlled-router results, and optional external-model results are reported separately.

## Evidence levels: what the results do and do not prove

<table>
  <thead>
    <tr>
      <th>Evidence type</th>
      <th>What it supports</th>
      <th>What it does not prove</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td><strong>Deterministic fixtures</strong></td>
      <td>Repeatable tool behavior, evaluation rules, workflow-step repair, and regression protection.</td>
      <td>That a probabilistic production model will make the same routing decision.</td>
    </tr>
    <tr>
      <td><strong>Controlled mock router</strong></td>
      <td>That a permitted harness change can causally alter behavior in a controlled, provider-independent experiment.</td>
      <td>That the same patch will improve every external model or every prompt.</td>
    </tr>
    <tr>
      <td><strong>Optional external-model smoke test</strong></td>
      <td>A repeatable way to compare V2 and V3 through an OpenAI-compatible provider.</td>
      <td>No external-model improvement claim is made by default. The smoke test has not been run in the verified project environment because provider credentials were not configured.</td>
    </tr>
  </tbody>
</table>

## Project structure

<table>
  <thead>
    <tr>
      <th>Path</th>
      <th>Responsibility</th>
    </tr>
  </thead>
  <tbody>
    <tr><td><code>app/schemas/</code></td><td>Validated Pydantic contracts between core modules.</td></tr>
    <tr><td><code>app/requirement/</code></td><td>Convert raw requirements into a structured requirement specification.</td></tr>
    <tr><td><code>app/benchmark/</code></td><td>Generate traceable benchmark cases.</td></tr>
    <tr><td><code>app/runner/</code></td><td>Run the Target Agent and record execution traces.</td></tr>
    <tr><td><code>app/debugger/</code></td><td>Classify failures and produce evidence-backed root causes.</td></tr>
    <tr><td><code>app/optimizer/</code></td><td>Propose, validate, and apply bounded harness patches.</td></tr>
    <tr><td><code>app/regression/</code></td><td>Compare baseline and candidate evaluation results.</td></tr>
    <tr><td><code>app/targets/commerce/</code></td><td>Commerce Agent, tools, policies, evaluator, challenge sets, and controlled experiments.</td></tr>
    <tr><td><code>api/main.py</code></td><td>FastAPI endpoints for execution, diagnosis, patching, regression, and session history.</td></tr>
    <tr><td><code>frontend/</code></td><td>Next.js product UI with bilingual labels and workflow views.</td></tr>
    <tr><td><code>tests/</code></td><td>Unit and integration tests; normal tests do not call a live model.</td></tr>
    <tr><td><code>docs/AGENTLAB_CONTRACT.md</code></td><td>MVP scope, module boundaries, and engineering constraints.</td></tr>
    <tr><td><code>scripts/demo.py</code></td><td>Reproduce the deterministic and controlled-router CLI demo.</td></tr>
    <tr><td><code>scripts/real_model_smoke.py</code></td><td>Optional V2/V3 comparison against an external OpenAI-compatible model.</td></tr>
  </tbody>
</table>

## Run locally

### 1. Install the backend dependencies

Windows PowerShell, from the repository root:

<pre><code>python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m pytest -q
python scripts/demo.py</code></pre>

### 2. Start the backend

In a separate terminal, from the repository root:

<pre><code>python -m uvicorn api.main:app --reload --port 8001</code></pre>

### 3. Start the frontend

In another terminal:

<pre><code>cd frontend
npm ci
npm run dev -- --port 3000</code></pre>

Open <a href="http://localhost:3000">http://localhost:3000</a>.

If the browser behavior does not match the source code, check which processes are serving ports 8001 and 3000 before changing application logic.

### Run the frontend checks

From <code>frontend/</code>:

<pre><code>npm run lint
npm run typecheck
npm run build</code></pre>

The GitHub Actions CI workflow runs the Python test suite and the frontend lint, type-check, and production-build checks.

## Optional external-model smoke test

The adapter uses an OpenAI-compatible <code>/chat/completions</code> endpoint. In PowerShell, configure credentials for the current session only:

<pre><code>$env:AGENTLAB_LLM_API_KEY = "your-api-key"
$env:AGENTLAB_LLM_BASE_URL = "https://your-provider.example/v1"
$env:AGENTLAB_LLM_MODEL = "your-model-name"
$env:AGENTLAB_LLM_TIMEOUT_SECONDS = "30"
python scripts/real_model_smoke.py --repetitions 5</code></pre>

Do not commit real credentials. The project intentionally does not auto-load <code>.env</code> files; export the variables in your shell or inject them through the execution environment.

## API surface

<table>
  <thead>
    <tr>
      <th>Endpoint</th>
      <th>Purpose</th>
    </tr>
  </thead>
  <tbody>
    <tr><td><code>GET /api/health</code></td><td>Backend health check.</td></tr>
    <tr><td><code>GET /api/benchmarks</code></td><td>Inspect the fixed regression, adaptive challenge, and coverage-exploration sets.</td></tr>
    <tr><td><code>POST /api/run</code></td><td>Execute a request and return its trace and available evaluation.</td></tr>
    <tr><td><code>POST /api/diagnose</code></td><td>Evaluate a registered run and derive failure/root-cause evidence.</td></tr>
    <tr><td><code>POST /api/patch</code></td><td>Propose a bounded patch from stored run evidence.</td></tr>
    <tr><td><code>POST /api/regression</code></td><td>Apply the proposed patch and compare baseline with candidate.</td></tr>
    <tr><td><code>GET /api/runs</code>, <code>/api/failures</code>, <code>/api/patches</code>, <code>/api/regressions</code></td><td>Read the current backend process's run and optimization history.</td></tr>
  </tbody>
</table>

## Current limitations

<details>
  <summary><strong>Read before interpreting the demo as production-ready</strong></summary>
  <ul>
    <li><strong>One target testbed:</strong> Commerce Agent is the only integrated Target Agent in this MVP.</li>
    <li><strong>Session history is in memory:</strong> run, failure, patch, and regression records are held in the backend process, not a durable database. They can disappear after a restart and may not be shared between serverless instances.</li>
    <li><strong>External-model evidence is optional:</strong> default tests and the normal demo do not make live LLM calls.</li>
    <li><strong>Controlled-router results are scoped:</strong> they show behavior in the controlled experiment, not a universal guarantee for OpenAI-compatible or other providers.</li>
    <li><strong>No autonomous source-code rewriting:</strong> optimization is limited to the four approved harness configuration surfaces.</li>
    <li><strong>Not included in this MVP:</strong> production authentication, durable multi-user storage, an LLM-as-a-Judge, LangGraph orchestration, MCTS, model fine-tuning, or an open-ended self-modification loop.</li>
  </ul>
</details>

---

<div align="center">
  <p><strong>Make every proposed Agent change explainable, bounded, and testable.</strong></p>
  <p>让每一次 Agent 改进都有证据、有边界、可回归验证。</p>
</div>
