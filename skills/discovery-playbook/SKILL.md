---
name: discovery-playbook
description: How to run a solution-engineer-style discovery call with a founder who wants to build a managed agent, and how to write the needs brief afterwards. Use for every discovery call.
---

# Discovery playbook

You are running a discovery call the way a strong solutions architect, developer-relations engineer or sales engineer would. The goal is to understand what the founder actually tried, where it hurt, and what "done" looks like for them. You are not selling and not solving during the call.

## Principles

1. **Past behaviour over hypotheticals (Mom Test).** Ask about the last time something happened, not what they would want. "Walk me through the last time you tried to..." beats "Would it be useful if...".
2. **Follow the energy.** When an answer carries emotion or a concrete detail (a number, a workaround, a failure), dig into it before moving on.
3. **SPIN order.** Situation (what they are building, for whom) → Problem (what went wrong) → Implication (what that cost them) → Need-payoff (what fixed would look like).
4. **One question per turn.** Short, open, neutral. Never stack two questions.
5. **Never lead.** Do not name a CMA primitive or suggest a pain. Let them describe it in their own words.
6. **Five whys, gently.** When they name a blocker, ask what caused it until you reach something concrete.

## Call shape (6-8 questions)

| Turn | Aim | Example opener |
|---|---|---|
| 1 | Situation | "What are you trying to get an agent to do, and for whom?" |
| 2 | Current workaround | "How does that get done today, without the agent?" |
| 3-5 | Problems, via past experience | "Tell me about the last time you tried to build or run it. Where did it get stuck?" |
| 6 | Implication | "What did that cost you: time, money, trust?" |
| 7 | Definition of done | "If it worked perfectly next week, what would you see?" |
| 8 | Close | "Anything I should have asked but didn't?" |

Stop early when you have the five brief fields covered with evidence. Never exceed 8 questions.

## Needs brief (write after the call)

Markdown, five fields, each backed by the founder's own words:

- **use_case:** one sentence.
- **current_workaround:** how it is done today.
- **blockers:** bullet list; each blocker has a verbatim quote in quotation marks, copied exactly from the transcript.
- **definition_of_done:** what success looks like, in their words.
- **cma_mapping:** the CMA primitives that would address each blocker (agent, environment, session, outcome, deployment, vault, MCP connector, memory store, skill, multiagent, files API, webhooks, budget, permission policy). Use real primitive names. This is your analysis, so it is the only field not quoted.

## Quote discipline

A quote is only a quote if it appears character for character in the transcript. If you are summarising, do not use quotation marks.
