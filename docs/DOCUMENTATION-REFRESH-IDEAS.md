# Documentation Refresh Ideas

**Date:** 2026-01-07
**Context:** After a major development session that added belief systems, visualization polish (6 phases), trade network panel, and live configuration modal

This document captures ideas for a future comprehensive documentation refresh. The recent updates to STATUS.md and CLAUDE.md were tactical fixes; this outlines a more strategic restructuring.

---

## Current Documentation State

### What Exists

| Document | Purpose | State |
|----------|---------|-------|
| VISION.md | Project identity, methodology | Stable, authoritative |
| STATUS.md | Current capabilities, gaps | Updated but growing unwieldy |
| CLAUDE.md | Development guidance | Updated but duplicates STATUS.md |
| VISUALIZATION.md | UI/UX design reference | Partially outdated (many items now implemented) |
| theoretical-foundations.md | Textbook mappings | May need expansion |
| docs/ralph/ | Ralph loop protocol and PRDs | Growing collection |

### Pain Points

1. **STATUS.md is too long** (~450 lines) - hard to quickly understand capabilities
2. **Duplication** between CLAUDE.md and STATUS.md (both list modules, capabilities)
3. **VISUALIZATION.md** has "implemented" and "not implemented" mixed - unclear what's done
4. **No user guide** - only developer documentation exists
5. **PRD artifacts scattered** in docs/ralph/ without clear lifecycle
6. **No API reference** - must read source code for signatures

---

## Proposed Documentation Architecture

### Tier 1: Orientation (What is this?)

**VISION.md** - Unchanged, authoritative identity statement

**README.md** - Currently minimal, could expand to:
- Quick start (3 commands to see something)
- Screenshot/GIF of visualization
- Links to other docs
- Installation instructions

### Tier 2: Status & Planning (Where are we?)

**STATUS.md** - Refactor into sections:
- **1-page summary** at top (capabilities in ~20 bullet points)
- **Detailed capabilities** (current content, but condensed)
- **Known limitations** (current content)
- Move architecture details to separate doc

**ROADMAP.md** (new) - Future directions extracted from various docs:
- Near-term (planned PRDs)
- Medium-term (features discussed but not specified)
- Long-term (vision items not yet approached)

### Tier 3: User Documentation (How do I use it?)

**docs/user-guide.md** (new) - Non-developer usage:
- Running the visualization
- Understanding the UI
- Configuring simulations
- Interpreting results
- Export workflows

**docs/scenarios.md** (new) - Working with scenarios:
- YAML scenario format
- Built-in scenarios explained
- Creating custom scenarios
- Running comparisons

### Tier 4: Developer Documentation (How do I build on it?)

**CLAUDE.md** - Refocus on AI assistant guidance only:
- Project conventions
- Test commands
- Commit style
- What NOT to do
- Remove module listings (point to STATUS.md or API docs)

**docs/architecture.md** (new) - Technical deep dive:
- Module dependency diagram
- Four-phase tick loop explained
- Information environment abstraction
- Bargaining protocol interface
- Belief system architecture

**docs/api/** (new) - Auto-generated or manual API reference:
- Key classes and their methods
- Factory functions
- Configuration options

### Tier 5: Design Documents (Why did we build it this way?)

**VISUALIZATION.md** - Refactor:
- Mark clearly what's implemented vs aspirational
- Or split into VISUALIZATION-DESIGN.md (vision) and VISUALIZATION-STATUS.md (current)

**theoretical-foundations.md** - Expand:
- Add belief system foundations (Bayesian updating, bounded rationality)
- Add price belief theory (when implemented)

**docs/decisions/** (new) - ADR archive:
- Move ADRs from PRDs to permanent home
- Index by topic

### Tier 6: Process Documents (How do we work?)

**docs/ralph/** - Keep but organize:
- RALPH-INTERVIEW.md (protocol)
- Archive completed PRDs vs active ones
- Template files

---

## Specific Improvements

### VISUALIZATION.md Refresh

Current issues:
- §4 Trade Visualization describes Edgeworth box as future - it's implemented
- §6 Agent Perspective Mode marked future - it's implemented
- §12 Data Export lists formats - all now implemented

Options:
1. **Mark implemented items** with ✓ or [DONE] tags
2. **Split document** into design-vision vs current-state
3. **Remove implemented items** and keep only aspirational features

Recommendation: Option 1 (lowest effort, preserves design rationale)

### STATUS.md Condensation

Current: ~450 lines with detailed module tables
Proposed structure:
```
# Status

## Quick Summary (NEW - 20 lines)
- Simulation: ✓ complete
- Bargaining: ✓ Nash, Rubinstein
- Matching: ✓ Opportunistic, Stable Roommates
- Beliefs: ✓ type beliefs, memory
- Visualization: ✓ full-featured
- Tests: 669 passing

## Capabilities (condensed from current)
## Limitations (unchanged)
## Gaps vs Vision (unchanged)
```

### CLAUDE.md Deduplication

Remove from CLAUDE.md:
- Module purpose table (point to STATUS.md)
- Architecture diagram (move to docs/architecture.md)
- Detailed visualization feature list

Keep in CLAUDE.md:
- Project overview (1 paragraph)
- Development commands
- Commit conventions
- Theoretical grounding requirements
- Document hierarchy
- Next directions (brief)

---

## Implementation Approach

### Phase 1: Quick Wins (1 session)
- Add ✓ markers to VISUALIZATION.md for implemented items
- Add "Quick Summary" section to top of STATUS.md
- Create minimal README.md improvements

### Phase 2: Restructure (1-2 sessions)
- Create docs/architecture.md (extract from CLAUDE.md)
- Create docs/user-guide.md (basic usage)
- Slim down CLAUDE.md

### Phase 3: Expansion (ongoing)
- Create docs/scenarios.md
- Expand theoretical-foundations.md
- Consider auto-generated API docs

---

## Questions for Future Consideration

1. **Audience priority**: Is the primary reader a future-self developer, an AI assistant, or a potential external user?

2. **Versioning**: Should documentation be versioned with releases, or kept evergreen?

3. **Examples**: Would example scripts/notebooks add value, or is the visualization sufficient?

4. **Diagrams**: Would architecture diagrams (Mermaid, etc.) help understanding?

5. **Search**: As docs grow, should we add a search mechanism or better cross-linking?

---

## Changelog

- 2026-01-07: Initial draft after visualization polish session
