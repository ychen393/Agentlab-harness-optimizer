"""Bilingual, judge-facing AgentLab product narrative."""
from __future__ import annotations
import json
import re
from typing import Any
from app.demo_evidence import DemoEvidence, build_demo_evidence, evolution_rows, validation_rows
from app.targets.commerce.policies import get_policy
from app.targets.commerce import COMMERCE_SCENARIOS
from app.ui.i18n import t, validate_ui_translations

def _styles(st: Any) -> None:
    st.markdown("""<style>.block-container{max-width:1280px;padding-top:1.8rem}.hero{padding:2.4rem 2.6rem;border:1px solid #e5e7eb;border-radius:18px;background:linear-gradient(135deg,#fffdf8,#f4f8ff)}.hero h1{font-size:clamp(2.7rem,5vw,4.8rem);letter-spacing:-.06em;margin:0 0 .5rem}.hero p{font-size:1.16rem;color:#4b5563;max-width:780px}.stage{text-align:center;padding:1rem .4rem;border:1px solid #e5e7eb;border-radius:14px;background:#fff;font-weight:650}.fail{color:#b42318;font-weight:700}.pass{color:#067647;font-weight:700}</style>""", unsafe_allow_html=True)

def _demo(st: Any, lang: str, evidence: DemoEvidence) -> None:
    st.session_state.setdefault("demo_step",0)
    if st.button(t("run_baseline",lang),type="primary",icon=":material/play_arrow:"): st.session_state.demo_step=1
    if st.session_state.demo_step==0: st.caption(t("same_agent",lang)); return
    st.subheader(f"1 · {t('observe',lang)}",divider=False); a,b=st.columns(2)
    with a.container(border=True):
        st.write(f"**{t('selection',lang)}** · `search_policy` · {t('pass',lang)}"); st.write("Applicable policy selected · PASS"); st.write("`check_eligibility` · NOT REACHED")
    with b.container(border=True): st.markdown(f"<span class='fail'>WORKFLOW STOPPED · {t('fail',lang)}</span>",unsafe_allow_html=True); st.write("workflow.max_steps = 2"); st.write("The Agent stopped before completing the eligibility check.")
    with st.expander(t("view_trace",lang)): st.code(json.dumps({"test_id":"CT6","tool_calls":evidence.first_cycle.baseline_traces[-2].tool_calls,"error":evidence.first_cycle.baseline_traces[-2].error},indent=2),language="json")
    if st.session_state.demo_step>=2:
        st.subheader(f"2 · {t('evidence_path',lang)}",divider=False)
        for body in ("diagnosis_line1","diagnosis_line2","diagnosis_line3"):
            with st.container(border=True): st.markdown(f"**{t('observation',lang)}**  \n{t(body,lang)}")
        st.info(f"{t('product_question',lang)}\n\n{t('product_answer',lang)}"); st.markdown(f"**{t('root_cause',lang)}:** workflow budget is insufficient for this valid multi-step task.")
        pattern = evidence.first_cycle.failure_patterns[0]
        analysis = evidence.first_cycle.root_cause_analyses[0]
        patch = evidence.first_cycle.proposed_patch
        st.subheader("Evidence chain", divider=False)
        chain = [
            (t("evidence_trace", lang), "`search_policy` ✓ · `check_eligibility` 未执行" if lang == "zh" else "`search_policy` ✓ · `check_eligibility` not executed", "`workflow.max_steps = 2`"),
            (t("evaluation_result", lang), t("task_incomplete", lang), "PASS = False"),
            (t("failure_pattern", lang), pattern.category, f"{t('affected', lang)}: {', '.join(pattern.affected_test_ids)}"),
            (t("root_cause_analysis", lang), analysis.root_cause, f"{t('target', lang)}: {analysis.target_component}"),
            (t("patchability", lang), t("yes", lang), f"{patch.target_component}: max_steps 2 → 3" if patch else ""),
        ]
        for title, value, detail in chain:
            with st.container(border=True):
                st.markdown(f"**{title}**  \n{value}  \n<span class='muted'>{detail}</span>", unsafe_allow_html=True)
        st.subheader(t("not_ct6_specific", lang), divider=False)
        baseline_rows = [
            e.test_id for e in evidence.first_cycle.baseline_evaluations if e.passed
        ]
        failed_rows = [
            e.test_id for e in evidence.first_cycle.baseline_evaluations if not e.passed
        ]
        st.markdown(f"**{t('baseline_scope', lang)}**")
        a, b = st.columns(2)
        a.container(border=True).write(f"**PASS**\n\n{', '.join(baseline_rows)}")
        b.container(border=True).write(f"**FAIL**\n\n{', '.join(failed_rows)}")
        st.markdown(f"**{t('shared_pattern', lang)}:** `{pattern.category}`  ·  **{t('supporting_failures', lang)}:** `{', '.join(pattern.affected_test_ids)}`")
        st.caption("CT6 and CT7 complete the earlier business action but stop before the next required step because the configured workflow budget is exhausted." if lang == "en" else "CT6 和 CT7 都能完成前面的业务步骤，但在后续必要步骤之前触发 workflow step limit。")
        st.subheader(t("required_path", lang), divider=False)
        st.code("search_policy → check_eligibility\nV1 available budget: max_steps = 2\nNext required action: check_eligibility → BLOCKED", language="text")
        proposal_note = "The observed blocked step is used as the candidate value; this is not a claim of global optimality." if lang == "en" else "候选值来自观测到的阻塞步骤；这不代表对所有任务的全局最优保证。"
        st.info(f"{t('proposal_type', lang)}: {t('deterministic_rule', lang)} — {proposal_note}")
        st.caption(t("candidate_not_guarantee", lang))
        with st.expander(t("controlled_comparison", lang)):
            st.write(f"{t('changed', lang)}: `workflow_config.max_steps` 2 → 3")
            st.write(f"{t('frozen_items', lang)}: Commerce Agent business logic · Model / routing · CT1–CT7 · Ground truth · Evaluator · Policy fixtures")
        with st.expander(t("toy_fix", lang)):
            st.write(t("toy_fix_body", lang))
    if st.session_state.demo_step>=3:
        st.subheader(f"3 · {t('propose_patch',lang)}",divider=False); st.caption(f"{t('patch_reason',lang)}"); a,b=st.columns(2)
        a.code("workflow_config\nmax_steps = 2")
        b.code("workflow_config\nmax_steps = 3",language="diff")
        st.caption(f"{t('unchanged',lang)}: Commerce Agent business code · Scenario · Ground truth · Evaluator · Model · Benchmark")
    if st.session_state.demo_step>=4:
        st.subheader(f"4 · {t('rerun_title',lang)}",divider=False); st.caption(f"{t('same',lang)}: Commerce Agent · CT6 · Evaluator"); st.caption(f"{t('only_change',lang)}: `workflow_config.max_steps` 2 → 3"); a,b=st.columns(2)
        a.container(border=True).markdown(f"**BEFORE · V1**\n\n`search_policy` PASS\n\n`check_eligibility` NOT REACHED\n\n<span class='fail'>{t('fail',lang)}</span>",unsafe_allow_html=True); b.container(border=True).markdown(f"**AFTER · V2**\n\n`search_policy` PASS\n\n`check_eligibility` PASS\n\n<span class='pass'>{t('pass',lang)}</span>",unsafe_allow_html=True)
    if st.session_state.demo_step>=5:
        decision = evidence.first_cycle.regression_decision
        st.subheader(f"5 · {t('validate',lang)}",divider=False)
        st.write(t("regression_intro", lang))
        st.info(f"**{t('experiment',lang)}**  ·  {t('baseline',lang)}: `{decision.baseline_version}`  ·  {t('candidate',lang)}: `{decision.candidate_version}`  ·  {t('patch_label',lang)}: `workflow_config` 2 → 3  ·  {t('scenario_family',lang)}: {t('fixed_regression',lang)}")
        comparisons = []
        for baseline, candidate in zip(evidence.first_cycle.baseline_evaluations, evidence.first_cycle.candidate_evaluations):
            change = "Improved" if candidate.passed and not baseline.passed else ("Unchanged" if baseline.passed and candidate.passed else "Regressed")
            if lang == "zh":
                change = {"Improved": "改善", "Unchanged": "不变", "Regressed": "回退"}[change]
            comparisons.append({"Test": baseline.test_id, "V1": "PASS" if baseline.passed else "FAIL", "V2": "PASS" if candidate.passed else "FAIL", "Change": change})
        st.table(comparisons)
        a,b,c,d=st.columns(4); a.metric(t("improved",lang),len(decision.improved_test_ids)); b.metric(t("regressed",lang),len(decision.regressed_test_ids)); c.metric(t("pass_rate",lang),f"{decision.baseline_pass_count} / {decision.baseline_total} → {decision.candidate_pass_count} / {decision.candidate_total}"); d.metric(t("decision",lang),decision.decision.upper())
        st.success(t("accept_reason", lang), icon=":material/check_circle:")
        st.caption(f"{t('source',lang)}: `RegressionDecision` · {t('baseline',lang)}: `{decision.baseline_version}` · {t('candidate',lang)}: `{decision.candidate_version}`")
    if st.session_state.demo_step < 5:
        next_label = {1: t("diagnose_failure", lang), 2: t("propose_patch", lang), 3: t("apply_rerun", lang), 4: t("run_regression", lang)}[st.session_state.demo_step]
        if st.button(next_label, icon=":material/arrow_forward:"):
            st.session_state.demo_step += 1
            st.rerun()

def _commerce_agent(st: Any, lang: str) -> None:
    st.header("Commerce Agent", icon=":material/shopping_cart:")
    st.write("Commerce Agent is the Target Agent. It handles commerce requests with business tools and policy context." if lang == "en" else "Commerce Agent 是正在被测试的 Target Agent，使用业务工具和政策上下文处理电商请求。")
    st.code("User Request → Commerce Agent → Router / LLM → Tools → Business Result", language="text")
    a, b = st.columns(2)
    a.container(border=True).write("**Tools**\n\n`search_products`\n`search_policy`\n`check_eligibility`")
    b.container(border=True).write("**Normal business flow**\n\nPolicy lookup → eligibility check → eligibility / gift result")

def _ct6_business_context(st: Any, lang: str) -> None:
    scenario = next(item for item in COMMERCE_SCENARIOS if item.test_case.id == "CT6")
    request = scenario.test_case.input
    ground_truth = scenario.ground_truth
    policy = get_policy(ground_truth.expected_policy_id)
    paid_at = re.search(r"paid on (\d{4}-\d{2}-\d{2})", request).group(1)
    amount = re.search(r"for (\d+) RMB", request).group(1)
    st.subheader(t("business_role", lang), divider=False)
    st.write(t("business_role_body", lang))
    st.caption(t("time_policy", lang))
    a, b = st.columns(2)
    a.container(border=True).markdown(f"**{t('order_amount', lang)}**  \n`{amount} RMB`\n\n**{t('paid_at', lang)}**  \n`{paid_at}`")
    b.container(border=True).markdown(f"**{t('policy', lang)}**  \n`{policy.id}`\n\n**{t('period', lang)}**  \n`{policy.starts_at} → {policy.ends_at}`\n\n**{t('minimum', lang)}**  \n`{policy.min_amount} RMB`\n\n**{t('gift', lang)}**  \n`{policy.gift}`")
    st.markdown(f"**User Request → Commerce Agent → `search_policy` → `{policy.id}` → `check_eligibility` → {t('expected_result', lang)}**")
    c1, c2, c3 = st.columns(3)
    c1.container(border=True).write(f"**1. {t('find_policy', lang)}**\n\n`search_policy`")
    c2.container(border=True).write(f"**2. {t('check_gift', lang)}**\n\n`check_eligibility`")
    outcome = f"{t('eligible', lang)} · {ground_truth.expected_gift}"
    c3.container(border=True).write(f"**3. {t('expected_result', lang)}**\n\n{outcome}")

def _narrative(st: Any, lang: str, evidence: DemoEvidence) -> None:
    st.header(t("problem",lang),icon=":material/error_outline:"); st.write(t("problem_body",lang)); st.header(t("works",lang),icon=":material/auto_awesome:"); st.write(t("works_body",lang)); cols=st.columns(6)
    for col,key in zip(cols,("observe","evaluate","diagnose","patch","rerun","regress")): col.markdown(f"<div class='stage'>{t(key,lang)}</div>",unsafe_allow_html=True)
    a,b=st.columns(2); a.container(border=True).write(f"**{t('editable',lang)}**\n\nsystem_prompt · tool_description · context · workflow_config"); b.container(border=True).write(f"**{t('frozen',lang)}**\n\nscenario · ground truth · evaluator · benchmark · model/provider")
    _commerce_agent(st, lang)
    _ct6_business_context(st, lang)
    st.header(t("demo",lang),icon=":material/auto_fix_high:"); st.write(t("demo_intro",lang));
    ct6_request = next(item.test_case.input for item in COMMERCE_SCENARIOS if item.test_case.id == "CT6")
    with st.container(border=True):
        st.caption(t("request",lang)); st.markdown(f"### {ct6_request}")
        st.caption("Expected workflow: `search_policy` → applicable policy → `check_eligibility`")
        policy = get_policy("POLICY_B")
        a, b, c = st.columns(3)
        a.metric(t("policy", lang), policy.id)
        b.metric(t("minimum", lang), f"{policy.min_amount} RMB")
        c.metric(t("gift", lang), policy.gift)
        _demo(st,lang,evidence)
    st.header(t("evolution",lang),icon=":material/timeline:")
    bodies = (("story1", "V1: workflow_config max_steps = 2 → CT6 / CT7 fail → 2 → 3 → V2: 7 / 7"), ("story2", "Coverage exploration discovers EX2 → controlled validation 15 / 16 → 16 / 16"), ("story3", "External model: correct tool, wrong argument contract → tool_description → FAIL → PASS")) if lang == "en" else (("story1", "V1：workflow_config max_steps = 2 → CT6 / CT7 失败 → 2 → 3 → V2：7 / 7"), ("story2", "覆盖探索发现 EX2 → 受控验证 15 / 16 → 16 / 16"), ("story3", "外部模型：工具选对但参数契约错误 → tool_description → 失败 → 通过"))
    for title,body in bodies:
        with st.container(border=True): st.markdown(f"**{t(title,lang)}**  \n{body}")
    st.header(t("why",lang),icon=":material/compare_arrows:"); a,b=st.columns(2); a.container(border=True).write(f"**{t('without',lang)}**\n\nFailure → inspect logs manually → guess prompt change → rerun manually → risk regressions"); b.container(border=True).write(f"**{t('with',lang)}**\n\nFailure → structured trace → independent evaluation → bounded patch → regression decision")
    st.header(t("plan",lang),icon=":material/architecture:"); st.write(t("plan_body",lang)); st.info("Frozen evaluation · independent judge · auditable trace · bounded optimization · regression before acceptance · challenge generation / coverage" if lang == "en" else "冻结评估 · 独立评判 · 可审计轨迹 · 有边界的优化 · 接受前回归 · 挑战生成 / 覆盖探索")

def _positioning(st: Any, lang: str, evidence: DemoEvidence) -> None:
    st.header(t("positioning", lang), icon=":material/route:")
    st.write(t("positioning_line", lang))
    left, right = st.columns(2)
    left.container(border=True).write(f"**{t('observability',lang)}**\n\nRun Target Agent\n↓\nExecutionTrace\n↓\nEvaluationResult\n↓\nPASS / FAIL")
    right.container(border=True).write(f"**{t('optimization_loop',lang)}**\n\nFailurePattern\n↓\nRootCauseAnalysis\n↓\nPatchability\n↓\nHarnessPatch\n↓\nRegressionDecision\n↓\nACCEPT / REJECT")
    st.subheader(t("input_contract", lang))
    a,b,c=st.columns(3)
    a.container(border=True).write("**INPUT**\n\nTarget Agent\nBenchmark / scenarios\nEvaluator\nEditable Harness\nAllowed patch surface")
    b.container(border=True).write("**AGENTLAB**\n\nRun\nEvaluate\nDiagnose\nPatch\nRegress")
    c.container(border=True).write("**OUTPUT**\n\nExecution evidence\nFailurePattern\nRootCauseAnalysis\nHarnessPatch\nRegression comparison\nACCEPT / REJECT")
    st.subheader(t("guardrails", lang))
    a,b=st.columns(2)
    a.container(border=True).write("**EDITABLE**\n\nsystem_prompt\ntool_description\ncontext\nworkflow_config")
    b.container(border=True).write("**FROZEN**\n\nbenchmark\nground truth\nevaluator\nraw evidence\nmodel / provider during controlled comparison")
    st.info(t("optimizer_message", lang))
    st.header(t("failure_layers", lang), icon=":material/tune:")
    cards = [
        (t("workflow_constraint",lang), "required multi-step flow cannot complete", "workflow_step_limit", "workflow_config", "deterministic V1 → V2", "5 / 7 → 7 / 7"),
        (t("system_instruction",lang), "negated intent causes incorrect routing under the controlled router", "system_prompt", "system_prompt", "controlled provider-independent experiment", "15 / 16 → 16 / 16"),
        (t("tool_interface",lang), "correct tool selected, incorrect argument contract", "tool_argument_schema_failure", "tool_description", "external-model smoke experiment", "FAIL → PASS"),
    ]
    if lang == "zh":
        cards = [
            (t("workflow_constraint",lang), "必要的多步流程无法完成", "workflow_step_limit", "workflow_config", "确定性 V1 → V2", "5 / 7 → 7 / 7"),
            (t("system_instruction",lang), "受控 router 下否定意图导致路由错误", "system_prompt", "system_prompt", "独立于 Provider 的受控实验", "15 / 16 → 16 / 16"),
            (t("tool_interface",lang), "工具选对，但参数契约错误", "tool_argument_schema_failure", "tool_description", "外部模型 smoke 实验", "失败 → 通过"),
        ]
    cols=st.columns(3)
    for col,(title,weakness,diagnosis,target,source,result) in zip(cols,cards):
        col.container(border=True).write(f"**{title}**\n\n{t('observed_weakness',lang)}: {weakness}\n\nDiagnosis: `{diagnosis}`\n\n{t('patch_target_label',lang)}: `{target}`\n\n{t('evidence_label',lang)}: {source}\n\n{t('result_label',lang)}: {result}")
    st.info("AgentLab treats the Harness as multiple editable control surfaces: instructions, tool interfaces, context, and workflow constraints." if lang == "en" else "AgentLab 把 Harness 拆成多个可以独立诊断和验证的控制面：系统指令、工具接口、上下文和工作流约束。")
    st.header(t("not_every_failure", lang), icon=":material/block:")
    st.write(t("refuse_message", lang))
    st.success(f"{t('patchability_gate',lang)} · {t('no_bounded_patch',lang)}")
    st.write("The deterministic fallback path does not consume the editable prompt/context surfaces, so changing them would not affect this execution path." if lang == "en" else "确定性 fallback 路径不会读取可编辑的 prompt/context，因此修改这些组件不会影响这条执行路径。")
    st.header(t("regression_message", lang), icon=":material/shield:")
    st.write("5 / 7  →  7 / 7    ·    Regressions: 0    ·    Decision: ACCEPT")
    st.header(t("mvp_boundary", lang))
    a,b=st.columns(2)
    a.container(border=True).write("**"+t("mvp_can",lang)+"**\n\n• execute Target Agent benchmarks\n• collect ExecutionTrace\n• independent evaluation\n• classify failure patterns\n• root-cause analysis\n• bounded Harness patches\n• candidate version comparison\n• regression accept / reject\n• challenge / coverage scenarios\n• controlled and external-model validation")
    b.container(border=True).write("**"+t("mvp_does_not",lang)+"**\n\n• retrain foundation models\n• arbitrarily rewrite application source\n• change evaluator / ground truth\n• guarantee every failure is patchable\n• prove universal improvement across all models\n• optimize arbitrary third-party agents without an adapter")
    st.write(t("commerce_testbed", lang))
    a,b=st.columns(2); a.container(border=True).write(f"**{t('commerce_specific',lang)}**\n\npolicies\ncommerce tools\ncommerce ground truth"); b.container(border=True).write(f"**{t('core_specific',lang)}**\n\nrunner\nevaluation contracts\nfailure analysis\noptimizer\nregression")

def main() -> None:
    import streamlit as st
    validate_ui_translations()
    st.set_page_config(page_title="AgentLab",page_icon=":material/auto_awesome:",layout="wide"); _styles(st); st.session_state.setdefault("language","zh")
    @st.cache_resource
    def evidence() -> DemoEvidence: return build_demo_evidence()
    selected=st.segmented_control("Language / 语言",["中文","EN"],default="中文",key="language_selector",label_visibility="collapsed"); st.session_state.language="en" if selected=="EN" else "zh"; lang=st.session_state.language; result=evidence()
    st.markdown(f"<div class='hero'><h1>AgentLab</h1><p>{t('hero_subtitle',lang)}</p><p>{t('hero_detail',lang)}</p></div>",unsafe_allow_html=True); _narrative(st,lang,result); _positioning(st,lang,result)
    with st.expander(t("technical",lang)):
        st.caption(t("technical_caption",lang))
        secondary = result.second_cycle.regression_decision
        st.subheader(t("secondary_evidence", lang))
        st.caption(t("controlled_experiment", lang))
        a,b,c,d,e = st.columns(5)
        a.metric(t("baseline", lang), f"{secondary.baseline_pass_count} / {secondary.baseline_total}")
        b.metric(t("candidate", lang), f"{secondary.candidate_pass_count} / {secondary.candidate_total}")
        c.metric(t("improved", lang), ", ".join(secondary.improved_test_ids) or "—")
        d.metric(t("regressed", lang), len(secondary.regressed_test_ids))
        e.metric(t("decision", lang), secondary.decision.upper())
        st.caption(f"{t('evidence_type', lang)}: {t('controlled_experiment', lang)}")
        gate = result.deterministic_patchability
        st.subheader(t("patchability_gate", lang))
        st.write(f"**{t('no_bounded_patch', lang)}**")
        st.write(f"**{t('reason', lang)}:** {gate.message.split('.')[0]}.")
        st.write(f"**{t('meaning', lang)}:** Changing editable Harness components would not affect this deterministic execution path.")
        st.dataframe(evolution_rows(result), width="stretch")
        st.dataframe(validation_rows(result), width="stretch")
        with st.expander(t("raw_regression", lang)): st.json(secondary.model_dump())
        with st.expander(t("raw_failure", lang)): st.json(result.first_cycle.failure_patterns[0].model_dump())
        with st.expander(t("raw_root_cause", lang)): st.json(result.first_cycle.root_cause_analyses[0].model_dump())
        with st.expander(t("raw_patch", lang)): st.json(result.first_cycle.proposed_patch.model_dump() if result.first_cycle.proposed_patch else {})
        with st.expander(t("raw_coverage", lang)): st.json(result.coverage_report.model_dump())

if __name__=="__main__": main()
