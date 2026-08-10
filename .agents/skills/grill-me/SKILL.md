---
name: grill-me
description: Run a relentless, structured interview to sharpen a plan, architecture, or design before implementation.
---

# Grill-Me Skill (Interactive Interviewer)

When the user asks to be grilled, stress-tested, or uses `/grill-me`:

## Core Principles
1. **One Question at a Time**: Never overwhelm the user with a wall of questions. Ask exactly one focused, high-leverage question at a time.
2. **Provide Recommended Answers**: Prefix your preferred suggestion with `(Recommended)` and offer 2-3 clear options so the user can easily respond or write in their own choice.
3. **Context Awareness (Scan First)**: Before asking any question, search the local codebase, documentation (`PROJECT_DOCUMENTATION.txt`), and existing configurations (`config.ini`) to avoid asking redundant questions.
4. **Branching Decision Tree**: Systematically walk through design branches:
   - Functional requirements & goal scope
   - Technical implementation & driver selection (`ios` vs `mock`)
   - Edge cases, fallbacks & self-assertion checks
   - Verification & expected output format
5. **Final Plan Synthesis**: Once all branches are resolved, output a polished, structured implementation plan or PRD before writing code.
