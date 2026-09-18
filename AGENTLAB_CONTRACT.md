# AgentLab — MVP Engineering Contract

## 0. Purpose of This Document

This document is the source of truth for the AgentLab MVP.

Before implementing or modifying any feature, read this document first.

Do not redesign the architecture, add unnecessary frameworks, or expand the product scope unless explicitly requested.

The development principle is:

**Design top-down. Implement bottom-up.**

The architecture is defined first, but implementation must proceed through small, independently testable modules.

Do not generate the entire application in one pass.

---

# 1. Product Goal

AgentLab is a generic Harness Evaluation and Optimization System.

AgentLab Core evaluates and improves the configurable harness around a separate
Target Agent. The first Target Agent / testbed is a Commerce Agent. AgentLab is
not itself the Commerce Agent, and the Commerce Agent is not part of AgentLab
Core.

Its purpose is not only to determine whether an AI Agent succeeds or fails.

It should:

1. understand the Target Agent's requirements;
2. generate benchmark test cases;
3. execute the Target Agent against those test cases through a stable interface;
4. evaluate outputs;
5. identify recurring failure patterns;
6. diagnose likely root causes;
7. propose bounded harness improvements;
8. create a new harness configuration for the Target Agent;
9. rerun the same benchmark;
10. compare Target Agent V1 and V2 harness configurations;
11. decide whether the proposed change should be accepted or rejected.

The core product loop is:

```text
Requirement
    ↓
Benchmark Generation
    ↓
Target Agent Execution
    ↓
Evaluation
    ↓
Failure Mining
    ↓
Root Cause Analysis
    ↓
    Harness Patch
    ↓
    Target Agent V2
    ↓
Regression Test
    ↓
    Target Agent V1 vs V2
    ↓
Accept / Reject
```

The primary value proposition is:

> We do not only tell users that their Target Agent failed.
> We identify why it failed, which editable part of its harness should change,
> and whether that bounded change actually improves performance.

---

# 2. MVP Scope

AgentLab Core must remain domain-independent at its module boundaries. It owns:

```text
benchmark
runner
evaluator
debugger
optimizer
regression
```

The initial Target Agent is the Commerce Agent. It is the first testbed used to
validate that the generic harness optimizer can discover failures, propose
bounded harness changes, and verify them through regression testing. Do not
attempt to support multiple Target Agent implementations in the first MVP.

Initial Commerce Agent scenarios may involve product discovery, product
comparison, policy-aware recommendations, catalog or inventory tool use,
missing product context, and structured commerce responses. Detailed Commerce
Agent behavior belongs under the future target package, not inside AgentLab
Core.

The already implemented Requirement Parser and Benchmark Generator remain
generic. Existing research-oriented examples in their contracts are examples
of valid inputs, not a restriction of AgentLab to a Research Agent.

## 2.1 AgentLab Core

AgentLab Core contains the reusable evaluation and optimization loop:

1. `benchmark` creates traceable test cases from requirements;
2. `runner` invokes a Target Agent through the Target Agent Interface;
3. `evaluator` independently scores outputs;
4. `debugger` groups failures and diagnoses evidence-backed root causes;
5. `optimizer` proposes bounded changes to the editable harness surface;
6. `regression` compares versions on the same and/or held-out benchmark data.

Requirement parsing and shared schemas support this loop but are not part of
the Target Agent implementation.

## 2.2 Target Agent

A Target Agent is a separate system being evaluated and optimized by AgentLab.
It owns its domain behavior, domain models, tools, policies, and execution
implementation. AgentLab Core must interact with it only through stable data
contracts and the Target Agent Interface.

The initial Target Agent is the Commerce Agent. Future Target Agents may use
the same interface, but multi-target support is not an MVP deliverable.

## 2.3 Target Agent Interface

Conceptually, every Target Agent must support:

```python
class TargetAgent:
    def run(
        self,
        test_case: TestCase,
        agent_config: AgentConfig,
    ) -> ExecutionTrace:
        ...
```

The interface separates AgentLab Core orchestration from domain-specific agent
implementation. A concrete protocol or abstract base class should be introduced
only when the Runner is implemented.

---

# 3. Allowed Harness Optimization Scope

AgentLab must NOT allow unrestricted self-modification or Target Agent code
rewriting.

The optimizer may modify only:

```text
1. `system_prompt`
2. `tool_description`
3. `context`
4. `workflow_config`
```

Example editable harness configuration:

```json
{
  "system_prompt": "...",
  "tools": {
    "web_search": {
      "description": "..."
    }
  },
  "context": {
    "instructions": []
  },
  "workflow": {
    "max_steps": 6,
    "require_citation": true
  }
}
```

The MVP must not automatically modify:

```text
- application source code;
- database implementation;
- evaluator implementation;
- scoring logic;
- benchmark ground truth;
- held-out regression data;
- security rules;
- model provider configuration;
- test cases after regression testing begins.
```

This is a bounded harness optimization system.

---

# 4. Non-Goals

Do NOT implement the following unless explicitly requested later:

```text
- autonomous code rewriting;
- reinforcement learning;
- model fine-tuning;
- evolutionary search;
- MCTS workflow search;
- multi-agent swarm architecture;
- complex RAG infrastructure;
- vector databases;
- authentication;
- enterprise permission systems;
- distributed workers;
- Kubernetes;
- microservices;
- multiple frontend frameworks;
- multiple Target Agent implementations in the MVP.
```

Do not optimize for production scale yet.

Optimize for:

```text
correctness
clarity
traceability
demoability
modularity
```

---

# 5. Technology Stack

Use:

```text
Python
Pydantic
Qwen or OpenAI-compatible API
SQLite
Streamlit
Plotly
```

Optional later:

```text
LangGraph
```

Do not introduce LangGraph in the first implementation unless the normal Python pipeline becomes difficult to maintain.

The initial workflow should be implemented using ordinary Python functions.

Example:

```python
requirement = parse_requirement(...)
tests = generate_tests(requirement)
runs = run_benchmark(...)
evaluations = evaluate_runs(...)
failures = analyze_failures(...)
patch = propose_harness_patch(...)
v2 = apply_harness_patch(...)
v2_runs = run_benchmark(...)
comparison = compare_versions(...)
```

---

# 6. Engineering Principle

The implementation order must be:

```text
small component
↓
unit test
↓
verify output contract
↓
connect next component
↓
integration test
↓
expand system
```

Do not build UI first.

Do not build database abstractions before the core loop works.

Do not generate all project files at once.

Each module must have a clear input and output contract.

---

# 7. System Modules

The final system separates AgentLab Core from Target Agents.

AgentLab Core contains the following logical modules:

```text
1. Requirement Parser
2. Benchmark Generator
3. Target Agent Runner
4. Evaluation Engine
5. Failure Analyzer
6. Root Cause Analyzer
7. Optimizer
8. Regression Comparator
9. Persistence Layer
10. Streamlit UI
```

Target implementations are separate:

```text
targets/
└── commerce/
```

Not every module needs to be an AI Agent.

Prefer deterministic Python code where possible.

Use an LLM only where semantic reasoning is genuinely required.

The `benchmark`, `runner`, `evaluator`, `debugger`, `optimizer`, and
`regression` modules are AgentLab Core. Code under `targets/commerce/` belongs
to the initial Target Agent and must not be imported into generic Core logic
except through the Target Agent Interface.

---

# 8. Suggested Project Structure

```text
app/
│
├── schemas/
│   ├── requirement.py
│   ├── benchmark.py
│   ├── execution.py
│   ├── evaluation.py
│   ├── debugging.py
│   └── optimization.py
│
├── requirement/
│   └── parser.py
│
├── benchmark/
│   └── generator.py
│
├── runner/
│   └── agent_runner.py
│
├── evaluator/
│   ├── rules.py
│   ├── llm_judge.py
│   └── scoring.py
│
├── debugger/
│   ├── failure_classifier.py
│   └── root_cause.py
│
├── optimizer/
│   ├── harness_patch.py
│   └── patcher.py
│
├── regression/
│   └── compare.py
│
├── targets/
│   └── commerce/
│       ├── agent.py
│       ├── tools.py
│       ├── domain_models.py
│       ├── policies.py
│       ├── scenarios.py
│       └── evaluator.py
│
├── database/
│   ├── connection.py
│   └── repository.py
│
├── llm/
│   └── client.py
│
└── streamlit_app.py
│
tests/
│
├── test_requirement.py
├── test_benchmark.py
├── test_runner.py
├── test_evaluator.py
└── test_regression.py
│
demo.py
README.md
AGENTLAB_CONTRACT.md
```

Do not create unnecessary abstraction layers beyond this structure.

The `targets/commerce/` files above are planned conceptual components. Do not
create them until the Commerce Agent is explicitly requested.

---

# 9. Core Data Contracts

All module boundaries should use Pydantic models.

Avoid passing unstructured dictionaries between major modules when a stable schema can be defined.

---

## 9.1 Requirement

```python
from pydantic import BaseModel
from typing import Literal


class Requirement(BaseModel):
    id: str
    description: str
    type: Literal[
        "freshness",
        "citation",
        "factuality",
        "coverage",
        "format",
        "tool_usage",
        "other"
    ]
    weight: float
```

---

## 9.2 RequirementSpec

```python
class RequirementSpec(BaseModel):
    task_type: str
    task_description: str
    requirements: list[Requirement]
```

Example:

```json
{
  "task_type": "research",
  "task_description": "Research recent Agent evaluation approaches",
  "requirements": [
    {
      "id": "R1",
      "description": "Use recent sources",
      "type": "freshness",
      "weight": 0.2
    },
    {
      "id": "R2",
      "description": "Include at least five citations",
      "type": "citation",
      "weight": 0.2
    }
  ]
}
```

Weights should sum approximately to 1.

---

# 10. Requirement Parser Contract

## Input

```text
Raw user requirement / PRD / user story
```

## Output

```python
RequirementSpec
```

The parser should convert natural-language requirements into structured evaluation criteria.

It must not generate benchmark cases.

It must not run the Target Agent.

It must not modify requirements beyond what can reasonably be inferred from the provided text.

When information is ambiguous, preserve the ambiguity instead of inventing detailed acceptance rules.

---

# 11. TestCase Contract

```python
class TestCase(BaseModel):
    id: str
    input: str

    category: Literal[
        "normal",
        "boundary",
        "adversarial",
        "missing_context",
        "fresh_information",
        "citation_heavy",
        "tool_required",
        "formatting"
    ]

    difficulty: Literal[
        "easy",
        "medium",
        "hard"
    ]

    requirement_ids: list[str]
```

Optional later:

```python
expected_behavior: str | None
```

---

# 12. Benchmark Generator Contract

## Input

```python
RequirementSpec
```

## Output

```python
list[TestCase]
```

For MVP, generate approximately:

```text
5 cases during development
10–20 cases for final demo
```

The benchmark must intentionally cover multiple categories.

Do not generate 20 near-duplicate questions.

Benchmark quality matters more than benchmark size.

Every test case must map back to one or more Requirement IDs.

Example:

```json
{
  "id": "T07",
  "input": "Compare Self-Harness and AFlow using recent sources.",
  "category": "fresh_information",
  "difficulty": "medium",
  "requirement_ids": [
    "R1",
    "R2",
    "R3"
  ]
}
```

## 12.1 Domain-Specific Benchmark Ground Truth

Generic `TestCase` remains unchanged. It describes the input presented to a
Target Agent and traces that input to generic requirements. Domain-specific
facts and expected outcomes must not be added to `TestCase`.

Each Target Agent may define separate, immutable benchmark ground truth. For
the Commerce testbed, the future target package will conceptually provide:

```text
CommerceScenario
├── stable scenario identity
├── link to a generic TestCase.id
└── CommerceGroundTruth
    ├── domain facts relevant to the scenario
    ├── expected outcomes
    ├── prohibited or invalid outcomes where applicable
    ├── applicable commerce policies
    └── expected tool behavior where applicable
```

`CommerceScenario` supplies the domain context needed for deterministic
evaluation. `CommerceGroundTruth` is evaluator-owned benchmark data, not Target
Agent context. The Target Agent and optimizer must not modify it, and held-out
ground truth must not be exposed during patch generation.

The exact Pydantic contracts for `CommerceScenario` and
`CommerceGroundTruth` must be defined with the Commerce target. Do not add
Commerce-specific fields to generic `TestCase`.

---

# 13. AgentConfig Contract

`AgentConfig` represents the editable harness configuration supplied to a
Target Agent. It does not represent the entire Target Agent, its source code,
domain models, business policies, evaluator, or benchmark.

```python
class ToolConfig(BaseModel):
    name: str
    description: str


class WorkflowConfig(BaseModel):
    max_steps: int = 6
    require_citation: bool = False


class AgentConfig(BaseModel):
    version: str
    system_prompt: str
    tools: list[ToolConfig]
    context: list[str] = []
    workflow: WorkflowConfig
```

Harness configuration versions must be immutable.

Do not overwrite V1 when creating V2.

---

# 14. Target Agent Runner Contract

## Input

```python
TestCase
AgentConfig
TargetAgent
```

## Output

```python
ExecutionTrace
```

Schema:

```python
class ExecutionTrace(BaseModel):
    test_id: str
    agent_version: str

    output: str

    tool_calls: list[str] = []

    latency_seconds: float | None = None

    input_tokens: int | None = None
    output_tokens: int | None = None

    error: str | None = None
```

Conceptual invocation:

```python
trace = target_agent.run(test_case, agent_config)
```

The Runner's responsibility is orchestration and observability. It invokes the
separate Target Agent through the Target Agent Interface.

It must not evaluate the answer.

It must preserve execution traces.

---

# 15. Evaluation Architecture

Evaluation must contain two layers.

The evaluator must be independent from the Target Agent and from the optimizer.
Neither the Target Agent nor the optimizer may modify, replace, or influence:

```text
benchmark ground truth
evaluator logic
scoring logic
held-out regression data
```

Evaluation inputs may include Target Agent outputs and execution traces, but
the evaluator must not reuse the Target Agent as its judge.

## 15.1 Domain Evaluator Adapter

AgentLab Core owns generic evaluation orchestration and shared result schemas.
A Target Agent may supply a domain evaluator adapter for deterministic checks
that require domain ground truth:

```text
Generic AgentLab Core Evaluator
+
Target-specific deterministic evaluator adapter
```

For the initial testbed, the Commerce evaluator adapter compares Commerce Agent
behavior and `ExecutionTrace` records against immutable `CommerceScenario` /
`CommerceGroundTruth` data. Examples may include product-fact correctness,
policy compliance, required catalog-tool use, inventory constraints, and
expected commerce outcomes.

The adapter returns shared evaluation contracts such as `RuleCheckResult`; it
does not redefine `EvaluationResult`. AgentLab Core remains responsible for
combining deterministic and semantic scores. The Commerce evaluator must be
independent from the Commerce Agent and Harness Optimizer and must not expose
held-out ground truth to either system.

```text
Layer 1:
Deterministic / Rule-Based Checks

Layer 2:
LLM Semantic Judge
```

Do not use LLM-as-Judge for conditions that can be reliably checked with Python.

---

# 16. Deterministic Checks

Examples:

```text
citation_count >= required_count

required_sections_present

valid_json

word_count <= maximum

required_tool_called

output_not_empty
```

Return structured results.

Example:

```python
class RuleCheckResult(BaseModel):
    metric: str
    passed: bool
    score: float
    explanation: str | None = None
```

---

# 17. LLM Judge Contract

Use the LLM Judge only for semantic dimensions such as:

```text
factuality
requirement coverage
relevance
completeness
evidence support
reasoning quality
```

The LLM Judge must return structured JSON validated by Pydantic.

Example:

```python
class SemanticScore(BaseModel):
    factuality: float
    coverage: float
    relevance: float
    evidence_support: float
    reasoning: str
```

All numeric scores should be normalized to:

```text
0.0–1.0
```

---

# 18. Final Evaluation Contract

```python
class EvaluationResult(BaseModel):
    test_id: str
    agent_version: str

    passed: bool
    final_score: float

    rule_scores: dict[str, float]
    semantic_scores: dict[str, float]

    failed_requirement_ids: list[str]

    explanation: str
```

The score calculation should initially be simple and explicit.

Example default:

```text
30% factuality
25% requirement coverage
20% evidence support
15% deterministic formatting / constraints
10% tool usage
```

Do not hide score calculation inside the LLM.

The scoring formula must be implemented in Python.

---

# 19. Failure Classification Contract

The failure analyzer receives:

```python
list[EvaluationResult]
list[ExecutionTrace]
```

It outputs recurring failure patterns.

Schema:

```python
class FailurePattern(BaseModel):
    id: str
    category: str
    count: int
    affected_test_ids: list[str]

    severity: Literal[
        "low",
        "medium",
        "high"
    ]

    summary: str
```

Example categories:

```text
citation_missing
tool_selection_error
unsupported_claim
incomplete_answer
format_error
freshness_failure
requirement_coverage_failure
execution_error
```

Do not create a new category for every individual failure.

Prefer recurring patterns.

`FailurePattern.id` is a stable, non-empty identifier such as `F1`. A
`HarnessPatch` must use these identifiers when citing the failure patterns that
support a proposed change.

---

# 20. Root Cause Analysis Contract

## Input

```text
FailurePattern
+
Relevant ExecutionTrace records
+
Current AgentConfig
```

## Output

```python
class RootCauseAnalysis(BaseModel):
    failure_category: str

    evidence: list[str]

    root_cause: str

    target_component: Literal[
        "system_prompt",
        "tool_description",
        "context",
        "workflow_config"
    ]

    confidence: float
```

Root cause analysis must always reference evidence from actual failures.

Do not produce unsupported generic advice.

Bad:

```text
Improve the prompt.
```

Good:

```text
T03 and T12 answered questions requiring current information
without invoking web search.

The current web_search tool description does not define
freshness-sensitive triggering conditions.

Target component:
tool_description.
```

---

# 21. Harness Optimizer and HarnessPatch Contract

The Harness Optimizer receives:

```text
list[EvaluationResult]
list[ExecutionTrace]
list[FailurePattern]
list[RootCauseAnalysis]
current AgentConfig
```

It outputs a bounded `HarnessPatch`. `HarnessPatch` is the planned canonical
name for a proposed editable harness change. Its exact Pydantic schema must be
defined before the optimizer is implemented.

Conceptually:

```python
class HarnessPatch(BaseModel):
    target_component: Literal[
        "system_prompt",
        "tool_description",
        "context",
        "workflow_config"
    ]

    old_value: str

    proposed_value: str

    reason: str

    supporting_failure_pattern_ids: list[str]

    expected_effect: str

    regression_risk: str
```

Every proposed modification must be:

```text
bounded
specific
traceable
reversible
```

Do not rewrite the entire harness configuration if a narrow edit is sufficient.

The optimizer may change only the editable harness surface. It must not modify
Target Agent application code, benchmark ground truth, evaluator logic, scoring
logic, or held-out regression data.

---

# 22. Harness Configuration Versioning

Applying an accepted HarnessPatch creates:

```text
Target Agent V2 harness configuration
```

It must never overwrite:

```text
Target Agent V1 harness configuration
```

Example:

```text
Target Agent Harness
│
├── V1
│
└── V2
```

Later:

```text
V1 → V2 → V3 → V4
```

Each version should preserve:

```text
parent version
change description
HarnessPatch
creation timestamp
```

---

# 23. Regression Testing Contract

The regression loop is:

```text
Target Agent V1
→ benchmark
→ evaluation
→ diagnosis
→ HarnessPatch
→ Target Agent V2
→ same and/or held-out benchmark
→ Accept / Reject
```

The same benchmark must be run against:

```text
Target Agent V1 harness configuration
and
Target Agent V2 harness configuration
```

Do not generate a fresh benchmark for the comparison.

Otherwise the comparison is not meaningful.

Held-out regression data may additionally be used to detect overfitting. It
must remain immutable and inaccessible to the Target Agent and optimizer during
patch generation.

---

# 24. Version Comparison Contract

```python
class MetricComparison(BaseModel):
    metric: str
    v1: float
    v2: float
    delta: float


class RegressionDecision(BaseModel):
    comparisons: list[MetricComparison]

    primary_metric_improved: bool

    critical_regression_detected: bool

    decision: Literal[
        "accept",
        "reject",
        "review"
    ]

    explanation: str
```

Initial comparison metrics:

```text
Pass Rate
Requirement Coverage
Citation Accuracy
Tool Usage Accuracy
Factuality
Latency
```

Do not automatically accept V2 simply because the average score increases.

Critical regressions should be considered.

---

# 25. Example Regression Logic

Example:

```text
V1 Pass Rate:
65%

V2 Pass Rate:
85%

Citation Accuracy:
70% → 93%

Tool Accuracy:
62% → 89%

Latency:
3.5s → 4.1s
```

Possible result:

```text
Primary quality metrics improved significantly.

Latency increased by 0.6 seconds.

No critical regression detected.

Decision:
ACCEPT V2
```

---

# 26. Persistence Layer

Use SQLite.

Initial persistent entities:

```text
agents
harness_config_versions
requirements
test_cases
runs
evaluations
harness_patches
```

Do not design a complex enterprise database schema.

The persistence layer should primarily support:

```text
traceability
version comparison
benchmark history
debugging
demo data
```

---

# 27. UI Scope

Do not build the UI until the core Python pipeline works.

Final Streamlit UI should have approximately four areas.

## Page 1 — Target Setup

Display:

```text
Requirement
Harness Configuration
Generated Benchmark
```

## Page 2 — Evaluation

Display:

```text
Pass Rate
Average Score
Latency
Failure Distribution
Test Case Results
```

## Page 3 — Diagnosis

Display:

```text
Failure Pattern
Evidence
Root Cause
Target Component
Recommended Change
```

## Page 4 — Improvement

Display:

```text
Target Agent V1 vs V2

Metric deltas

Regression results

Accept / Reject
```

---

# 28. Visualization

Use Plotly only where visualization improves understanding.

Useful charts:

```text
V1 vs V2 metric comparison

Failure category distribution

Pass / Fail distribution

Requirement coverage

Harness configuration version score history
```

Do not add charts only for decoration.

---

# 29. Development Phases

## Phase 0 — Contracts

Before coding:

```text
Define Pydantic schemas.
```

Verify all module input/output contracts.

---

## Phase 1 — Minimum Testable Loop

Implement only:

```text
Requirement
↓
5 Test Cases
↓
Target Agent
↓
Evaluation
↓
Pass / Fail
```

No Streamlit.

No SQLite requirement if unnecessary.

No optimizer.

No debugger.

Deliverable:

```text
demo.py
```

Acceptance criterion:

The full loop must run successfully from a single command.

---

## Phase 2 — Failure Analysis

Add:

```text
Failure Classification
↓
Failure Pattern Mining
```

Acceptance criterion:

Failed cases are grouped into meaningful recurring categories.

---

## Phase 3 — Diagnosis

Add:

```text
Failure Pattern
↓
Root Cause
↓
Target Harness Component
```

Acceptance criterion:

Every root-cause conclusion must cite execution evidence.

---

## Phase 4 — Optimization

Add:

```text
Root Cause
↓
HarnessPatch
↓
Target Agent V2 harness configuration
```

Acceptance criterion:

The optimizer changes only one of:

```text
system_prompt
tool_description
context
workflow_config
```

---

## Phase 5 — Regression

Add:

```text
Target Agent V1 harness configuration
vs
Target Agent V2 harness configuration
```

Acceptance criterion:

Both versions run on the same benchmark and produce a structured comparison.

---

## Phase 6 — Persistence

Add SQLite.

Persist:

```text
Harness configuration versions
Test cases
Runs
Evaluations
Harness patches
```

---

## Phase 7 — UI

Build the Streamlit interface only after the backend pipeline works.

---

# 30. Testing Requirements

Every major module requires tests.

At minimum:

```text
Requirement Parser:
valid output schema

Benchmark Generator:
valid TestCase schema
requirement mapping present

Runner:
trace generated
errors captured

Rule Evaluator:
known cases produce expected result

Scoring:
deterministic score calculation

Failure Analyzer:
known failures grouped correctly

Regression Comparator:
known metric differences produce expected decision
```

Mock LLM calls where possible.

Do not make every unit test depend on live API calls.

---

# 31. Error Handling

All LLM outputs must be validated.

If output fails Pydantic validation:

```text
retry once with format correction
```

If it still fails:

```text
return explicit structured error
```

Do not silently continue with malformed model output.

API errors should not crash the entire benchmark.

One failed test case should be recorded as an execution error while other cases continue.

---

# 32. Observability

Every benchmark run should make it possible to answer:

```text
Which Target Agent and harness configuration version ran?

Which test case ran?

What input was sent?

What output came back?

Which tools were called?

How long did it take?

What evaluation result was produced?

Why did the evaluator fail it?

Which HarnessPatch resulted from the failure?
```

If the system cannot answer those questions, observability is insufficient.

---

# 33. Rules for Using LLMs

Use deterministic code when deterministic code is sufficient.

Examples:

```text
count citations → Python

check JSON → Python

calculate score → Python

compare versions → Python
```

Use LLMs for:

```text
requirement understanding

test generation

semantic evaluation

failure reasoning

root-cause analysis

HarnessPatch generation
```

Do not ask the LLM to perform arithmetic or deterministic checks unnecessarily.

---

# 34. Coding Rules for Codex

When implementing a requested module:

1. Read this contract first.
2. Inspect existing code before changing anything.
3. Implement only the requested scope.
4. Do not rewrite unrelated files.
5. Preserve existing public interfaces unless explicitly requested.
6. Use existing schemas instead of inventing new duplicates.
7. Avoid premature abstraction.
8. Avoid unnecessary dependencies.
9. Add or update tests.
10. Run relevant tests after modifications.
11. Report exactly what changed.
12. Report known limitations.
13. Do not claim something works unless it has been executed or tested.

---

# 35. Rules Against Overengineering

Do NOT introduce:

```text
RepositoryFactory
AbstractAgentFactory
BaseManager
ServiceProvider
Complex dependency injection
Generic workflow engines
Event buses
Distributed queues
```

unless an actual requirement makes them necessary.

Prefer:

```python
parse_requirement()

generate_tests()

run_agent()

evaluate()

analyze_failures()

propose_harness_patch()

compare_versions()
```

Simple code is preferred for the MVP.

---

# 36. Codex Task Format

Every implementation request should follow this pattern:

```text
Read AGENTLAB_CONTRACT.md first.

Current task:
Implement Benchmark Generator only.

Input:
RequirementSpec

Output:
list[TestCase]

Requirements:
- Generate five test cases initially.
- Cover multiple benchmark categories.
- Every TestCase must reference requirement_ids.
- Validate output using Pydantic.
- Add unit tests.

Do NOT:
- build the UI;
- add SQLite;
- implement Target Agent Runner;
- add LangGraph;
- modify unrelated modules.

Acceptance criteria:
1. Tests pass.
2. Example RequirementSpec generates valid TestCase objects.
3. Invalid LLM output is handled explicitly.

After implementation:
Explain changed files, test results, and remaining limitations.
```

Use this pattern for future Codex tasks.

---

# 37. Initial Build Sequence for Codex

Codex should implement modules in this exact order unless explicitly instructed otherwise:

```text
1. schemas
2. Requirement Parser
3. Benchmark Generator
4. Target Agent Interface
5. Minimal Commerce Agent V1
6. CommerceScenario / CommerceGroundTruth
7. Target Agent Runner
8. Deterministic Commerce Evaluator Adapter
9. LLM Judge
10. Scoring
11. Failure Classification
12. Root Cause Analysis
13. HarnessPatch
14. Harness Configuration Versioning
15. Regression Comparison
16. SQLite
17. Streamlit
18. Plotly dashboard
```

In short, the next implementation path after Benchmark Generator is:

```text
Target Agent Interface
→ Minimal Commerce Agent V1
→ Commerce Scenario / Ground Truth
→ Runner
→ Deterministic Commerce Evaluator
→ remaining optimization loop
```

LangGraph is not part of the required MVP.

---

# 38. MVP Success Definition

The MVP is successful when the following demo works:

```text
User enters a Commerce Agent requirement.

↓

AgentLab structures the requirement.

↓

AgentLab generates benchmark cases.

↓

Commerce Agent V1 executes the benchmark through the Target Agent Interface.

↓

AgentLab evaluates the results.

↓

AgentLab finds recurring failures.

↓

AgentLab identifies a likely root cause.

↓

AgentLab proposes a bounded HarnessPatch.

↓

Commerce Agent V2 harness configuration is created.

↓

The exact same benchmark is rerun.

↓

AgentLab compares Commerce Agent V1 and V2 harness configurations.

↓

AgentLab shows whether the change improved the Target Agent
without introducing unacceptable regressions.
```

Everything else is secondary.

---

# 39. Product Architecture Mental Model

AgentLab consists of two loops.

## Inner Quality Loop

```text
Requirement
↓
Benchmark
↓
Target Agent through Target Agent Interface
↓
Evaluation
```

## Outer Improvement Loop

```text
Evaluation
↓
Failure Mining
↓
Root Cause
↓
HarnessPatch
↓
Regression Test
↓
New Harness Configuration Version
```

The MVP must prove both loops.

A dashboard without the outer loop is not sufficient.

---

# 40. Final Engineering Principle

The architecture may be designed broadly.

The implementation must remain incremental.

Never implement:

```text
the whole platform
```

in one Codex request.

Instead implement:

```text
one contract
↓
one module
↓
one test
↓
one integration
↓
next module
```

The human owns:

```text
Product goal
Architecture
Module boundaries
Input/output contracts
Evaluation criteria
Scope decisions
```

Codex assists with:

```text
Implementation
API integration
Schemas
Testing
Debugging
Refactoring
UI implementation
```

Codex should not silently change product architecture.

When an architecture change seems necessary, explain the issue first rather than implementing the change automatically.
