# Ralph Interview Protocol v3

A vision-anchored interview process for transforming project goals into ralph-ready PRDs and operational artifacts.

---

## Purpose

This protocol guides an LLM agent through a structured process that translates an existing project vision into comprehensive documentation suitable for autonomous ralph-loop execution.

**Critical framing**: The interview does not discover what to build. The vision document tells us what to build. The interview clarifies, operationalizes, and structures that vision into executable specifications.

**When to invoke this protocol:**
- `@ralph/RALPH-INTERVIEW.md` - mention this file to begin
- Before starting any ralph-loop on the project

**What this protocol produces:**
1. Structured extraction of the vision document
2. Project type determination (research software, learning, implementation)
3. Gap analysis: vision requirements vs. current codebase state
4. Resource constraint analysis (if applicable)
5. Clarified understanding through targeted questions
6. ADR drafts for major architectural decisions
7. A comprehensive PRD covering the full project vision
8. Phase decomposition for execution
9. Verification design appropriate to project type
10. Theory divergence tracking template (for theory-grounded work)
11. **Loop startup document** (START-RALPH-LOOP.md) with copy-paste prompts
12. Retrospective template (for learning projects)

---

## Prerequisite: Vision Document

This protocol requires a vision document. The agent must locate one of:

1. **VISION.md** - Explicit project vision file
2. **README.md** - If it contains vision/goals/purpose sections
3. **Explicit user statement** - User provides vision verbally if no doc exists

**If no vision document exists and user cannot articulate one:**
STOP. A ralph-loop cannot pursue a goal that doesn't exist. Help the user create a VISION.md first, then restart this protocol.

---

## Interview Phases

### Phase 0: Vision Anchoring & Project Type

**Objective:** Parse and internalize the vision document, then determine project type.

**Agent actions (autonomous, no questions yet):**

1. Locate the vision document (VISION.md, README.md, or request from user)
2. Read the document completely
3. Extract and present to user in structured format:

```
## Vision Extraction

### Primary Goal
[One sentence: what is this project trying to achieve?]

### Success Criteria
[List: how will we know the project succeeded?]

### Explicit Deliverables
[List: concrete things the vision says should exist]

### Open Questions in Vision
[List: ambiguities, "TBD" items, or unclear specifications]

### Assumptions I'm Making
[List: interpretations that might be wrong]
```

4. **Determine project type:**

```
## Project Type Assessment

Based on the vision, this appears to be:

[ ] **Research Software** - Theory defines correctness
    - Examples: economic simulations, scientific computing, ML research
    - Verification: Theory tests primary, property tests derived
    - Key artifacts: ADRs with literature references, THEORY-DIVERGENCES.md
    - Canonical sources: [identify textbooks/papers that define correctness]

[ ] **Learning/Exploration Project** - Understanding is the goal
    - Examples: learning labs, paper reproductions, skill-building
    - Verification: Design alignment, behavioral verification, retrospective
    - Key artifacts: RETROSPECTIVE.md, paper analysis documents
    - Success = mental model formation, not just working code

[ ] **Implementation Project** - Features define completeness
    - Examples: standard software, tools, applications
    - Verification: Functional tests, integration tests
    - Key artifacts: Standard PRD, progress tracking
```

5. Present extraction and type assessment, ask: "Does this accurately capture the vision and project type?"

**Phase exit:** User confirms extraction is accurate and project type is correct.

---

### Phase 1: Gap Analysis

**Objective:** Map the vision to current codebase state and identify what work needs to be done.

**Agent actions (autonomous exploration):**

1. Examine codebase structure relevant to vision goals
2. Identify what already exists vs. what the vision requires
3. Present to user:

```
## Gap Analysis

### Vision Requirement → Current State → Gap

| Requirement | Exists? | Current State | Work Needed |
|-------------|---------|---------------|-------------|
| [from vision] | Yes/Partial/No | [what's there] | [what's missing] |
```

4. Ask clarifying questions ONLY about gaps where:
   - Multiple implementation approaches exist
   - Priority/ordering is unclear
   - Technical constraints affect feasibility

**Questions to ask (examples):**

```
Q1.1: "The vision mentions [X]. I see [Y] exists. Should I extend Y or build X separately?"

Q1.2: "The vision lists multiple goals. For the PRD, should I:
- Cover all goals with phased execution
- Focus on [specific goal] first
- Something else?"

Q1.3: "The vision is silent on [technical decision]. Should I:
- Make a reasonable choice and document as ADR
- Ask you to decide now
- Flag it as pending?"
```

**Phase exit:** Gap analysis presented, clarifying questions resolved.

---

### Phase 1.5: Resource Constraint Analysis (Optional)

**Objective:** Identify constraints that affect scope and execution approach.

**When to include this phase:**
- Compute-intensive work (ML training, simulations)
- Time-bounded projects
- Infrastructure dependencies (cloud, GPUs, external services)

**Questions:**

```
Q1.5.1: "What resources are available for this work?"
- Compute: [local specs / cloud budget / none needed]
- Time budget: [hours / days / weeks / open-ended]
- Dependencies requiring setup: [list]

Q1.5.2: "Do resource constraints affect scope?"
- Full scope feasible with current resources
- Scope should be reduced to fit constraints
- Phased approach with resource checkpoints between phases
- Hybrid approach (local for X, cloud burst for Y)
```

**If constraints identified, produce:**

```
## Resource Constraint Analysis

### Available Resources
| Resource | Available | Required | Gap |
|----------|-----------|----------|-----|
| GPU VRAM | 16GB | [estimate] | [none/mild/severe] |
| Time | [budget] | [estimate] | [none/mild/severe] |
| [other] | ... | ... | ... |

### Scope Implications
[How constraints affect what's feasible in each phase]

### Mitigation Strategy
[Cloud burst, phased approach, scope reduction, etc.]
```

**Phase exit:** Resource constraints documented, scope implications understood.

---

### Phase 2: Clarification Interview & ADR Identification

**Objective:** Resolve ambiguities in the vision and identify architectural decisions requiring ADRs.

**Key principle:** This phase is NOT "what do you want to build?" It IS "help me understand the vision precisely enough to specify it."

**Questions emerge from:**
1. Open questions identified in Phase 0
2. Gaps identified in Phase 1
3. Ambiguities that would cause different implementations

**Question patterns:**

```
Ambiguity resolution:
"The vision says [X]. This could mean [interpretation A] or [interpretation B]. Which is intended?"

Operationalization:
"The vision's success criterion is [abstract goal]. What would be a concrete, verifiable version of this?"

Priority clarification:
"The vision mentions [A, B, C]. If these can't all be done in one phase, what's the priority order?"

Constraint surfacing:
"To achieve [vision goal], I'd typically do [approach]. Are there constraints that would rule this out?"
```

**ADR Identification:**

During clarification, identify decisions that warrant Architecture Decision Records:
- Choices between fundamentally different approaches
- Decisions that constrain future work
- Tradeoffs between theoretical purity and practical constraints
- Integration patterns with existing systems

**For each ADR candidate, draft:**

```
## ADR-XXX: [Decision Title]

**Status:** Proposed (awaiting approval)
**Created:** [date]
**Theoretical Basis:** [specific reference if applicable, e.g., "Kreps I Ch 5-7"]

### Context
[Why this decision is needed]

### Options Considered
1. **Option A**: [description]
   - Pro: [advantage]
   - Con: [disadvantage]

2. **Option B**: [description]
   - Pro: [advantage]
   - Con: [disadvantage]

### Recommended Decision
[Which option and why]

### Consequences
[What this decision enables/constrains]

---
*Awaiting approval before implementation proceeds.*
```

**Do NOT ask:**
- "What do you want to build?" (vision tells us)
- "What type of work is this?" (Phase 0 determined this)
- Generic questions not anchored to specific vision content

**Phase exit:**
- Convergence check - agent summarizes understanding, user confirms
- ADR drafts presented for decisions requiring them

---

### Phase 3: Verification Design

**Objective:** Establish how we'll know each vision goal is achieved, appropriate to project type.

#### For Research Software Projects

**Verification Hierarchy** (per DESIGN-PRINCIPLES.md):

```
Theory Verification (Primary)
    ↓ defines what "correct" means
Property Verification (Derived)
    ↓ operationalizes theoretical invariants
Functional Verification (Instrumental)
    ↓ ensures the machinery runs
```

**For each goal/deliverable:**

```
Q3.x: "[Goal] - what theory defines correctness?"

Theory verification:
- Canonical source: [textbook/paper reference]
- Testable prediction: [specific equation or property]
- Tolerance: [strict (1e-6) for formulas, moderate (1e-3) for optimization]

Property verification (derived from theory):
- [Invariant that must hold]

Functional verification:
- [Basic "it runs" criteria]
```

#### For Learning/Exploration Projects

**Verification Hierarchy:**

```
Design Alignment (Primary)
    ↓ embodies learning science / research principles
Behavioral Verification (Derived)
    ↓ system behaves as design requires
Outcome Measurement (Ultimate but Deferred)
    ↓ requires longitudinal data
```

**For each learning goal:**

```
Q3.x: "[Learning goal] - how should understanding be verified?"

Design alignment:
- Principle embodied: [learning science / research principle]
- Observable indicator: [what demonstrates alignment]

Behavioral verification:
- [Specific measurable behavior]

Self-assessment criteria:
- Can explain [concept] without referencing materials
- Can predict [outcome] before running experiment
- Can identify [pattern] in novel examples
```

**Additionally for learning projects:**

```
Q3.x: "What retrospective questions should be answered at completion?"
- What mental model was formed?
- What worked in the learning approach?
- What gaps remain?
- What questions emerged for future exploration?
```

#### For Implementation Projects

**Standard verification:**

```
Q3.x: "[Goal] - how should completion be verified?"
- Automated tests (specify what kind)
- Manual verification (specify criteria)
- Integration tests (specify scenarios)
- Performance benchmarks (specify thresholds)
```

**Phase exit:** Every vision goal has appropriate verification criteria for project type.

---

### Phase 3.5: Divergence Tracking Setup (Research Software Only)

**Objective:** Establish tracking for discovered divergences between implementation and theory.

**When to include:** Research software projects where theory defines correctness.

**Create THEORY-DIVERGENCES.md template:**

```markdown
# Theory Divergences Report

This document records divergences discovered between implementation and canonical theory during development.

## Summary

| ID | Theory | Status | Resolution |
|----|--------|--------|------------|
| DIV-001 | [description] | Pending/Fixed/Accepted | [approach] |

---

## Template for New Divergences

### DIV-XXX: [Title]

**Discovery Date:** [date]
**Test:** [test file::test_method]
**Canonical Source:** [textbook/paper reference]

#### Issue
[What was expected vs. what was observed]

#### Root Cause
[Why the divergence occurred]

#### Resolution
[How it was fixed, or why it's acceptable]

#### Theoretical Justification
[Why the resolution is consistent with theory]

---
```

**Phase exit:** THEORY-DIVERGENCES.md template created, path noted for PRD.

---

### Phase 4: Scope Confirmation

**Objective:** Confirm the PRD will cover the full vision (default) or document intentional scoping.

**Default assumption:** PRD covers the entire vision, decomposed into phases.

**Only ask if vision is very large or resources are constrained:**

```
Q4.1: "The vision encompasses [large scope]. Given [resource constraints if any], the PRD will cover:
- Full vision (phased execution)
- Scope to [specific phase/goal] only
- Scope adjusted per resource analysis
- Other"
```

**Phase exit:** Scope confirmed, aligned with resource constraints if applicable.

---

### Phase 5: Loop Parameters

**Objective:** Set execution parameters for the ralph-loop.

```
Q5.1: "What iteration budget is appropriate?"
- Conservative (10-20) - for well-specified phases
- Standard (20-50) - for moderate complexity
- Extended (50-100) - for exploratory or large work
- Specify number

Q5.2: "Progress tracking preferences?"
- Git commits only
- Git commits + progress.txt
- All methods (git + progress + PRD status updates)

Q5.3: "If a phase completes early, should the loop:"
- Stop and await next phase approval
- Continue to next phase automatically
- Ask before continuing

Q5.4: "Escalation triggers - loop should STOP if:"
- [Default: changes to core architecture without ADR]
- [Default: test failures that suggest theory divergence]
- [Custom triggers based on project]
```

**Phase exit:** Parameters set.

---

### Phase 6: Loop Startup Document Creation

**Objective:** Produce copy-paste ready prompts for executing the ralph-loop.

**Generate START-RALPH-LOOP.md:**

```markdown
# Ralph Loop Startup: [PRD-NAME]

Copy and paste the command below to start the ralph-loop.

---

## Pre-flight Checklist

Before starting:
- [ ] All existing tests pass: `[test command]`
- [ ] On correct branch: `git branch`
- [ ] Working directory clean: `git status`
- [ ] PRD reviewed and any edits made
- [ ] ADRs approved (if applicable)

---

## Startup Prompt

```
/ralph-loop:ralph-loop "Execute [PRD-NAME].json systematically.

[PHASE-SPECIFIC INSTRUCTIONS - customized per PRD]

CONSTRAINTS:
- [Phase ordering constraints]
- [Escalation triggers]
- [Approval requirements between phases]

Track progress via git commits, update PRD status fields as features complete." --max-iterations [N] --completion-promise "[PROMISE]"
```

---

## Resume Prompt (for interrupted loops)

```
/ralph-loop:ralph-loop "Resume [PRD-NAME].json execution.

Check current state:
1. Read progress.txt for last known state
2. Check PRD for feature passes and phase status values
3. Review recent git commits

Continue from where execution stopped. Ask before proceeding to a new phase." --max-iterations [N] --completion-promise "[PROMISE]"
```

---

## Phase Continuation Prompt

After reviewing a completed phase and approving continuation:

```
/ralph-loop:ralph-loop "Continue [PRD-NAME].json to Phase [N]: [Phase Name].

Previous phase verified complete. Proceed with next phase features." --max-iterations [N] --completion-promise "[PROMISE]"
```

---

## Key Files

| File | Purpose |
|------|---------|
| `[PRD-NAME].json` | Full PRD specification |
| `VISION.md` | Authoritative project vision |
| `[ADR files]` | Architectural decisions |
| `[THEORY-DIVERGENCES.md]` | Theory divergence tracking (if applicable) |
| `[other relevant docs]` | [purposes] |

---

## Expected Outputs

**Phase [N]:**
- [Expected files/artifacts]
- [Expected test files]
- [Expected documentation updates]

[Repeat for each phase]
```

**Phase exit:** START-RALPH-LOOP.md created and reviewed.

---

## Convergence Check

Before generating the PRD, the agent must present a summary and receive confirmation:

```
## Understanding Summary

**Project**: [name from vision]
**Project Type**: [Research Software / Learning / Implementation]

**Vision in my words**: [1-2 sentence restatement]

**Scope**: [full vision / specific subset]
**Resource Constraints**: [none / summary of constraints]

**Phases I'll define**:
1. [Phase name]: [what it accomplishes]
2. [Phase name]: [what it accomplishes]
...

**Key clarifications received**:
- [Decision 1]
- [Decision 2]

**ADRs to include**: [list or "none"]

**Verification approach**: [summary appropriate to project type]

**Divergence tracking**: [Yes with template / Not applicable]

Does this accurately capture what the PRD should specify?
```

**Only proceed to PRD generation after user confirms.**

---

## PRD Generation

Generate PRD in this JSON format:

```json
{
  "task": {
    "name": "Project name from vision",
    "description": "Full vision description",
    "created": "ISO timestamp",
    "vision_source": "path/to/VISION.md",
    "project_type": "research_software | learning | implementation",
    "completion_promise": "<promise>PROJECT-NAME-COMPLETE</promise>"
  },

  "context": {
    "codebase_state": "greenfield | active | maintenance | legacy",
    "primary_language": "language",
    "frameworks": ["list"],
    "vision_extraction": {
      "primary_goal": "one sentence",
      "success_criteria": ["list from vision"],
      "deliverables": ["list from vision"]
    },
    "gap_analysis_summary": "what exists vs what's needed",
    "resource_constraints": {
      "compute": "description or null",
      "time_budget": "description or null",
      "other": "description or null"
    },
    "canonical_sources": ["textbook/paper references for research software"]
  },

  "phases": [
    {
      "phase": 1,
      "name": "Phase name",
      "description": "What this phase accomplishes",
      "features": ["FEAT-001", "FEAT-002"],
      "entry_criteria": "what must be true to start",
      "exit_criteria": "what must be true to complete",
      "estimated_iterations": 20
    }
  ],

  "features": [
    {
      "id": "FEAT-001",
      "name": "Feature name",
      "phase": 1,
      "description": "What this feature does toward vision goals",
      "priority": 1,
      "passes": false,
      "criteria": {
        "functional": ["criterion 1"],
        "property": ["invariant 1"],
        "theory": ["theoretical requirement if applicable"]
      },
      "verification_commands": ["command 1"]
    }
  ],

  "architectural_decisions": {
    "resolved": [
      {
        "id": "ADR-001",
        "decision": "description",
        "choice": "what was decided",
        "rationale": "why",
        "source": "vision | interview | inferred",
        "canonical_reference": "textbook/paper if applicable"
      }
    ],
    "pending_adrs": []
  },

  "tracking": {
    "theory_divergences_file": "path or null",
    "retrospective_template": "path or null (for learning projects)"
  },

  "escalation_triggers": [
    "Trigger 1: condition that should pause the loop"
  ],

  "loop_parameters": {
    "max_iterations": 30,
    "progress_tracking": ["git_commits", "progress_file"],
    "on_phase_complete": "stop | continue | ask"
  }
}
```

---

## Additional Artifacts by Project Type

### For Research Software Projects

**THEORY-DIVERGENCES.md** - Created in Phase 3.5

**ADR files** - One per major architectural decision, format from Phase 2

### For Learning/Exploration Projects

**RETROSPECTIVE-TEMPLATE.md:**

```markdown
# [Project Name]: Retrospective

## Self-Assessment Against Original Success Criteria

| Criterion | Assessment | Evidence |
|-----------|------------|----------|
| [from vision] | Achieved / Partial / Gap | [specific evidence] |

---

## Track-by-Track Analysis

### [Track/Phase Name]

**What was built:**
- [list of artifacts, code, documents]

**Key learnings:**
1. [learning 1]
2. [learning 2]

**What worked:**
- [effective approach 1]

**What didn't work:**
- [ineffective approach 1]

---

## Mental Model Formed

### Before
[What you understood before starting]

### After
[What you understand now]

### Visual representation (if applicable)
```
[diagram or structured representation of mental model]
```

---

## Open Questions for Future Exploration

### High Priority
1. [question that blocks next work]

### Medium Priority
1. [question worth investigating]

### Lower Priority
1. [question for eventual exploration]

---

## Next Steps

### Immediate
1. [next action]

### Short-term
1. [near-future work]

### Long-term
1. [eventual direction]
```

**Paper Analysis Template** (if vision involves paper reproduction):

```markdown
# [Paper Title]

**Paper**: [arXiv/DOI link]
**Authors**: [names]
**Date**: [publication date]

## Reading Notes

### The Central Question
[What problem does this paper address?]

### The Key Innovation
[What's novel about the approach?]

### Core Claims (numbered for reference)
1. [Claim 1]
2. [Claim 2]
...

### My Interpretation
[Understanding in own words]

---

## Claims Identified for Reproduction

### High Priority (feasible with current setup)
1. **[Claim reference]**: [description]
   - Method: [how to test]
   - Connection: [how it relates to our work]

### Medium Priority (requires more setup)
1. ...

### Lower Priority (may exceed scope)
1. ...

---

## Questions This Paper Raises
1. [question 1]
2. [question 2]

## Connection to Our Work
| Our Component | Paper's Claim | Connection |
|---------------|---------------|------------|
| [component] | [claim] | [how they relate] |

---

## Sources
- [link to paper]
- [link to supplementary materials]
```

---

## Completion Promise

The completion promise signals the ralph-loop should terminate.

**For phased PRDs:** Each phase may have its own intermediate promise.

```
Phase 1 complete: <promise>PROJECT-NAME-PHASE-1-COMPLETE</promise>
Phase 2 complete: <promise>PROJECT-NAME-PHASE-2-COMPLETE</promise>
Full project: <promise>PROJECT-NAME-COMPLETE</promise>
```

**Emit only when:**
- All features in scope have `passes: true`
- All verification commands pass
- No escalation triggers have fired
- Theory divergences resolved or documented as acceptable (research software)

---

## Interview Checklist

Before concluding, verify:

### Core Deliverables
- [ ] Vision document located and extracted
- [ ] Project type determined and confirmed
- [ ] Gap analysis completed
- [ ] All ambiguities from vision clarified
- [ ] Every goal has verification criteria appropriate to project type
- [ ] Scope confirmed (full vision or explicit subset)
- [ ] Loop parameters set
- [ ] Convergence check passed
- [ ] PRD generated and presented

### Operational Artifacts
- [ ] START-RALPH-LOOP.md created with copy-paste prompts
- [ ] Pre-flight checklist included
- [ ] Resume and continuation prompts included

### Project-Type Specific
- [ ] **Research Software**: ADR drafts for major decisions
- [ ] **Research Software**: THEORY-DIVERGENCES.md template created
- [ ] **Research Software**: Canonical sources identified in PRD
- [ ] **Learning Projects**: RETROSPECTIVE-TEMPLATE.md created
- [ ] **Learning Projects**: Paper analysis template (if applicable)

### Optional (if applicable)
- [ ] Resource constraint analysis completed
- [ ] Scope adjusted for constraints

---

## Foundational Context

This protocol operationalizes principles from **DESIGN-PRINCIPLES.md**:

- **Completion as contract** - PRD promises are measurable and verifiable
- **Theory-primary verification** - For research projects, theory tests define correctness
- **External memory as primitive** - Progress persists via filesystem and git
- **Predictable failure beats unpredictable success** - Specs make failure informative

If DESIGN-PRINCIPLES.md exists, read it for deeper context.

---

## Usage Instructions for Agents

When this file is mentioned (`@ralph/RALPH-INTERVIEW.md`):

1. **Locate vision document** - VISION.md, README.md, or ask user
2. **Execute Phase 0** - Extract vision AND determine project type
3. **Execute Phase 1** - Gap analysis against codebase
4. **Execute Phase 1.5** - Resource constraint analysis (if applicable)
5. **Execute Phase 2** - Clarification interview AND ADR identification
6. **Execute Phase 3** - Design verification criteria (per project type)
7. **Execute Phase 3.5** - Divergence tracking setup (research software only)
8. **Execute Phase 4** - Confirm scope (default: full vision)
9. **Execute Phase 5** - Set loop parameters
10. **Convergence check** - Summarize, get confirmation
11. **Generate PRD** - Comprehensive, phased, verifiable
12. **Execute Phase 6** - Create START-RALPH-LOOP.md
13. **Generate additional artifacts** - Per project type (retrospective template, paper analysis)
14. **Await approval** - User must confirm all artifacts before loop execution

---

## Changelog

### v3 (2026-01-07)
- Added project type determination (research software / learning / implementation)
- Added Phase 1.5: Resource Constraint Analysis
- Enhanced Phase 2 with ADR identification and drafting
- Added Phase 3.5: Divergence Tracking Setup for research software
- Added Phase 6: Loop Startup Document Creation
- Added RETROSPECTIVE-TEMPLATE.md for learning projects
- Added Paper Analysis Template for research/learning projects
- Expanded PRD schema with project_type, resource_constraints, tracking fields
- Updated interview checklist with project-type-specific items

### v2 (2026-01-06)
- Initial vision-anchored protocol
- Phased interview structure
- PRD generation with completion promises
