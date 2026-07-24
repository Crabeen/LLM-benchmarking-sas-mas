"""Prompt templates from Tran & Kiela (arXiv:2604.02460), Appendix D.

System prompts and user templates follow the paper verbatim (D.1 SAS,
D.2 Sequential, D.7 evaluation). Two departures, both documented:

1. The paper's planner structure example is typeset ambiguously in the PDF
   (YAML-looking indentation under a "strict JSON" instruction). We present
   it as JSON; the parser in sequential.py accepts both JSON and YAML.
2. The paper's templates carry no context field (closed-book). When
   data.context_mode != "closed", we prepend the paragraphs before the
   question. For strictest fidelity set context_mode: closed.
"""

# --------------------------- D.1 SAS --------------------------- #

SAS_SYSTEM = (
    "You are a helpful assistant. Think step by step, then answer.\n"
    "Be as succinct as possible. Do NOT repeat the question.\n"
    "Return ONLY the final answer requested."
)

# D.1.2 — optional SAS-L variant, prepend to the user message if used.
SAS_L_USER_PREFIX = (
    "I want you to analyze the following question from multiple perspectives "
    "before answering.\n"
    "1. Identify ambiguities.\n"
    "2. Formulate at least two plausible interpretations.\n"
    "3. Evaluate the interpretations and choose the most likely one.\n"
    "4. Answer based on the most likely interpretation.\n"
    "The question is:\n"
)


def sas_user(question: str, context: str | None) -> str:
    if context:
        return f"Context:\n{context}\n\n{question}"
    return question


# ---------------------- D.2 Sequential MAS --------------------- #

PLANNER_SYSTEM = (
    "You are a careful planner. Break the user task into the fewest necessary "
    "sequential steps so each step output feeds the next.\n"
    "Output strict JSON only with the following structure:\n"
    '{"steps": [\n'
    '  {"id": 1, "name": "Step 1", "instruction": "What to do"},\n'
    '  {"id": 2, "name": "Step 2", "instruction": "What to do"}\n'
    "]}\n"
    "Rules:\n"
    "- Steps must be sequential and minimal.\n"
    "- Do not answer the question yourself.\n"
    "- Instructions must be concrete and unambiguous.\n"
    "- Do not include commentary outside the JSON object."
)


def planner_user(question: str) -> str:
    return question


WORKER_SYSTEM = "You are a helpful assistant. Think only for your step."


def plan_as_text(steps: list[dict]) -> str:
    return "\n".join(
        f"Step {s['id']}: {s['name']} - {s['instruction']}" for s in steps
    )


def worker_user(
    question: str,
    steps: list[dict],
    idx: int,                      # 0-based index of the current step
    prior_outputs: list[str],
    context: str | None,
) -> str:
    s = steps[idx]
    prior = (
        "\n".join(
            f"Step {steps[j]['id']} output: {out}"
            for j, out in enumerate(prior_outputs)
        )
        or "(none)"
    )
    ctx = f"Context:\n{context}\n\n" if context else ""
    return (
        f"{ctx}Original Question: {question}\n\n"
        f"Full Plan:\n{plan_as_text(steps)}\n\n"
        f"You are responsible for Step {s['id']}: {s['name']}\n"
        f"Instruction: {s['instruction']}\n\n"
        f"Previous step outputs:\n{prior}\n\n"
        "Perform ONLY your assigned step. Provide your step output succinctly."
    )


AGGREGATOR_SYSTEM = (
    "You are an aggregator. Read step outputs and return the final answer only.\n"
    "Do NOT attempt to solve the question yourself."
)


def aggregator_user(question: str, steps: list[dict], outputs: list[str]) -> str:
    step_outputs = "\n".join(
        f"Step {steps[j]['id']} ({steps[j]['name']}): {out}"
        for j, out in enumerate(outputs)
    )
    return (
        f"Question: {question}\n\n"
        f"Step outputs:\n{step_outputs}\n\n"
        "Return the final answer only."
    )


# --------------------------- D.7 Judge -------------------------- #

JUDGE_SYSTEM = "You are a helpful assistant."


def judge_user(question: str, prediction: str, gold: str) -> str:
    return (
        "=== Task ===\n"
        "I need your help in evaluating an answer provided by an LLM against a "
        "ground truth answer. Your task is to determine if the ground truth "
        "answer is present in the LLM's response. Please analyze the provided "
        "data and make a decision.\n\n"
        "=== Instructions ===\n"
        "1. Carefully compare the Predicted Answer with the Ground Truth Answer.\n"
        "2. The Ground Truth Answer is always absolutely correct. Do NOT assume "
        "otherwise.\n"
        "3. Consider the substance of the answers - look for equivalent "
        "information or correct answers. Do not focus on exact wording unless "
        "the exact wording is crucial to the meaning.\n"
        "4. Your final decision should be based on whether the meaning and the "
        "vital facts of the Ground Truth Answer are present in the Predicted "
        "Answer:\n\n"
        "=== Input Data ===\n"
        f"- Question: {question}\n"
        f"- Predicted Answer: {prediction}\n"
        f"- Ground Truth Answer: {gold}\n\n"
        "=== Output Format ===\n"
        "Provide your final evaluation in the following dictionary format:\n"
        "{Explanation: <How you made the decision?>, Decision: <TRUE or FALSE>}"
    )
