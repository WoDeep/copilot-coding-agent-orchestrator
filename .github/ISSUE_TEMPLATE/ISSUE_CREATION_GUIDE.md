# TimeAttack Issue Creation Guide

> **Single Source of Truth** for creating and managing development issues.

---

## ⚠️ PROJECT CRITICALITY DISCLAIMER

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  🏎️ MISSION-CRITICAL APPLICATION - READ BEFORE STARTING ANY WORK            │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  TimeAttack is a SAFETY-CRITICAL tool for professional race engineers.      │
│                                                                              │
│  HIGH STAKES:                                                                │
│  • Calculations determine tire wear predictions, fuel strategy, and         │
│    setup changes.                                                           │
│  • An error here means the difference between P1 and DNF.                   │
│  • Incorrect data could lead to DRIVER SAFETY ISSUES.                       │
│  • Teams invest millions of dollars based on this data.                     │
│                                                                              │
│  REAL-WORLD PHYSICS:                                                        │
│  • We model 1300kg GT3 cars moving at 280+ km/h.                            │
│  • All values must be PHYSICALLY VALID.                                     │
│  • Data represents real drivers, real cars, real IP.                        │
│                                                                              │
│  YOUR RESPONSIBILITY:                                                        │
│  • NEVER create mock/fake data - use ONLY real test datasets.               │
│  • Validate ALL calculations against known physics.                         │
│  • Document ALL assumptions and edge cases.                                 │
│  • When in doubt, ASK - don't guess.                                        │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 📁 Repository Structure for Issues

All planning artifacts are stored in a consistent structure:

```
project_management/
├── epics/
│   ├── EPIC_OVERVIEW.md              # Master list of all epics
│   ├── EPIC_XXX_NAME.md              # Epic definition file
│   │
│   ├── TC_A/                         # Technical Component A folder
│   │   ├── TC-A-00_EPIC_DEFINITION.md    # Epic overview for this component
│   │   ├── TC-A-01_ISSUE_TITLE.md        # Individual issue file
│   │   ├── TC-A-01_COMPLETION_REPORT.md  # Status/handoff document
│   │   └── ...
│   │
│   ├── TC_B/                         # Technical Component B folder
│   │   └── ...
│   │
│   └── TC_[X]/                       # Additional components as needed
│
└── roadmap/                          # Roadmap and dependency docs
```

### Naming Conventions

| Type | Format | Example |
|------|--------|---------|
| Epic File | `EPIC_XXX_NAME.md` | `EPIC_014_VEHICLE_MODEL.md` |
| Component Folder | `TC_X/` | `TC_M/` |
| Issue File | `TC-X-YY_TITLE.md` | `TC-M-01_REQUIREMENTS.md` |
| Completion Report | `TC-X-YY_COMPLETION_REPORT.md` | `TC-M-01_COMPLETION_REPORT.md` |

---

## 📋 Issue Template

Every issue MUST follow this structure:

```markdown
# TC-[X]-[YY]: [Issue Title]

**Component**: [Component Name]  
**Epic**: [Epic Number and Name]  
**Priority**: [P0-Critical | P1-High | P2-Medium | P3-Low]  
**Estimated Effort**: [XS | S | M | L | XL]  
**Dependencies**: [List prerequisite issues]

---

## 🏎️ Project Vision & Criticality

TimeAttack is a mission-critical tool for race engineers. [Brief context about what 
this component does and why it matters.]

**High Stakes**: [Explain the real-world impact of this work]  
**Real-World Physics**: [If applicable, explain physical constraints]

---

## 🏗️ Architectural Context

[Explain where this fits in the system architecture]

**Input Sources**:
- [Where does data come from?]

**Output Consumers**:
- [Who/what uses the output?]

**Data Flow**: 
```
[Source] -> Your Code -> [Destination]
```

---

## 📋 Task List

Follow the handbook.md workflow: Requirements → Implementation → Testing → Documentation

### 1. Investigate Requirements
- [ ] Read: [relevant documentation paths]
- [ ] Understand: [key concepts to grasp]

### 2. Write/Update Requirements
- [ ] Define: [what needs to be specified]
- [ ] Document in: [file path]

### 3. Investigate Architecture
- [ ] Review: [existing code/systems]
- [ ] Identify: [integration points]

### 4. Implement Code
- [ ] Create/Update: [specific files]
- [ ] Key Logic: [brief description of implementation]

### 5. Create Test Cases
- [ ] Unit Tests: [what to test]
- [ ] Integration Tests: [what to test]
- [ ] Use Real Data: [specify dataset]

### 6. Run Tests
- [ ] All tests passing
- [ ] Validation against real data

### 7. Create Documentation
- [ ] Code comments/docstrings
- [ ] API documentation
- [ ] Usage examples

### 8. Update Status Document
- [ ] Complete TC-X-YY_COMPLETION_REPORT.md
- [ ] Add notes for successor team

---

## ⚠️ Constraints

- **NEVER CREATE MOCK DATA** - Use real test datasets only
- **Validate Against Physics** - Results must be physically plausible
- **Document Assumptions** - Every assumption must be recorded
- **Follow Existing Patterns** - Match existing code style

---

## 📁 Files to Modify

| Action | File Path | Description |
|--------|-----------|-------------|
| Create | `path/to/new/file.py` | Description |
| Update | `path/to/existing.py` | What to change |
| Read | `path/to/reference.md` | Reference material |

---

## ✅ Acceptance Criteria

- [ ] Criterion 1: [Specific, measurable requirement]
- [ ] Criterion 2: [Specific, measurable requirement]
- [ ] Criterion 3: [Specific, measurable requirement]
- [ ] All tests passing (>80% coverage)
- [ ] Documentation complete
- [ ] Completion Report updated

---

## 📖 Reference Documents

- Epic: `project_management/epics/EPIC_XXX_NAME.md`
- Requirements: `concept/requirements/[relevant].md`
- Architecture: `ARCHITECTURE_BLUEPRINT.md`
- Handbook: `handbook.md`

---

## 🔗 Related Issues

- Blocks: [Issues this blocks]
- Depends On: [Prerequisite issues]
- Related: [Related but not dependent]
```

---

## 📊 Completion Report Template (Status Handoff Document)

**CRITICAL**: Every issue must have a corresponding Completion Report. This document serves as the **handoff between teams** - the predecessor documents their work and leaves instructions for the successor.

Create this file when starting work: `TC-X-YY_COMPLETION_REPORT.md`

```markdown
# TC-X-YY: [Issue Title] - Completion Report

**Issue**: TC-X-YY  
**Component**: [Component Name]  
**Status**: 🔄 IN PROGRESS | ✅ COMPLETE | ⚠️ BLOCKED | ❌ FAILED  
**Date Started**: YYYY-MM-DD  
**Date Completed**: YYYY-MM-DD  
**Developer/Team**: [Name]

---

## Executive Summary

[2-3 sentences describing what was accomplished]

---

## Work Completed

### 1. Requirements
- [ ] Requirements documented
- **File**: `path/to/requirements.md`
- **Notes**: [Any important decisions or clarifications]

### 2. Implementation
- [ ] Code implemented
- **Files Created/Modified**:
  - `path/to/file1.py` - [Description]
  - `path/to/file2.py` - [Description]
- **Key Decisions**: [Important implementation decisions made]

### 3. Testing
- [ ] Tests written and passing
- **Test File**: `path/to/tests/test_feature.py`
- **Test Results**: X tests, Y passing, Z coverage
- **Validation Data Used**: [Dataset name and path]

### 4. Documentation
- [ ] Documentation complete
- **Files Updated**:
  - `path/to/README.md`
  - `docs/api/feature.md`

---

## Validation Results

[Show actual results from testing with real data]

```
Example Output:
- Test Dataset: processed_Reduced_AbuDhabi_Strat2_MW.csv
- Samples Processed: 13,295
- Results: [specific validated results]
```

---

## ⚠️ Known Issues / Limitations

1. **Issue**: [Description]
   - **Impact**: [How it affects the system]
   - **Workaround**: [If any]
   - **Future Fix**: [Suggested approach]

---

## 📝 Notes for Successor Team

> **READ THIS SECTION CAREFULLY BEFORE STARTING DEPENDENT WORK**

### What You Need to Know
1. [Important context for the next team]
2. [Gotchas or non-obvious behaviors]
3. [Assumptions made that affect downstream work]

### Recommended Next Steps
1. [Suggested order of operations]
2. [Things to validate before proceeding]

### Files to Review First
1. `path/to/critical/file.py` - [Why it's important]
2. `path/to/another/file.md` - [Why it's important]

### Integration Points
- **Input**: [How to provide input to this component]
- **Output**: [What output this component provides]
- **API**: [Key functions/classes to use]

```python
# Example usage for successor team
from packages.module import Component

# Basic usage pattern
component = Component(config)
result = component.process(input_data)
```

---

## Checklist

- [ ] All acceptance criteria met
- [ ] Tests passing (>80% coverage)
- [ ] Documentation complete
- [ ] Code reviewed
- [ ] Notes for successor team written
- [ ] Related issues updated
- [ ] Epic progress updated

---

## Sign-Off

**Completed By**: [Name]  
**Reviewed By**: [Name]  
**Date**: YYYY-MM-DD
```

---

## 🏷️ Labels

### Component Labels
| Label | Component |
|-------|-----------|
| `technical-component-a` | Track Position Detection |
| `technical-component-b` | Vehicle Dynamics |
| `technical-component-c` | Orchestration Pipeline |
| `technical-component-d` | Load Collectives |
| `technical-component-e` | Visualization |
| `technical-component-f` | Session Management |
| `technical-component-g` | Lap Simulation |
| `technical-component-h` | Tire Strategy |
| `technical-component-i` | Alerts |
| `technical-component-j` | Data Quality |
| `technical-component-k` | Reports |
| `technical-component-l` | Configuration |
| `technical-component-m` | Benchmarking |
| `technical-component-n` | Collaboration |
| `technical-component-o` | Mobile |

### Priority Labels
| Label | Meaning | Color |
|-------|---------|-------|
| `P0-critical` | MVP blocker, safety-critical | 🔴 Red |
| `P1-high` | Important for MVP | 🟠 Orange |
| `P2-medium` | Nice to have | 🟡 Yellow |
| `P3-low` | Post-MVP | 🟢 Green |

### Type Labels
| Label | Meaning |
|-------|---------|
| `type-requirements` | Requirements definition |
| `type-design` | Architecture and design |
| `type-implementation` | Code implementation |
| `type-testing` | Testing tasks |
| `type-documentation` | Documentation |
| `type-bug` | Bug fixes |

### Status Labels
| Label | Meaning |
|-------|---------|
| `status-blocked` | Blocked by dependency |
| `status-in-progress` | Currently being worked |
| `status-review` | In code review |
| `status-testing` | In testing phase |

### Special Labels
| Label | Meaning |
|-------|---------|
| `mvp` | Required for MVP |
| `post-mvp` | Post-MVP feature |
| `safety-critical` | Affects driver safety |
| `good-first-issue` | Good for new team members |

---

## 📏 Effort Estimation

| Size | Duration | Criteria |
|------|----------|----------|
| **XS** | 1-2 days | Simple, well-defined, low risk |
| **S** | 3-5 days | Clear requirements, medium complexity |
| **M** | 1-2 weeks | Complex but understood, some unknowns |
| **L** | 2-4 weeks | High complexity, multiple unknowns |
| **XL** | 4+ weeks | Very complex - consider breaking down |

---

## 🔄 Workflow

### Creating a New Issue

1. **Create the Issue File**
   ```bash
   # In the appropriate TC_X folder
   touch project_management/epics/TC_X/TC-X-YY_ISSUE_TITLE.md
   ```

2. **Create the Completion Report**
   ```bash
   touch project_management/epics/TC_X/TC-X-YY_COMPLETION_REPORT.md
   ```

3. **Fill in the Issue Template** (see above)

4. **Create GitHub Issue** (optional - for tracking)
   ```bash
   gh issue create \
     --title "TC-X-YY: Issue Title" \
     --label "technical-component-x,P1-high,type-implementation" \
     --body-file project_management/epics/TC_X/TC-X-YY_ISSUE_TITLE.md
   ```

### Working on an Issue

1. **Read the Issue File** thoroughly
2. **Check predecessor's Completion Report** for context
3. **Follow handbook.md workflow**: Requirements → Implementation → Testing → Documentation
4. **Update Completion Report** as you work
5. **Add Notes for Successor** before marking complete

### Completing an Issue

1. **Verify all acceptance criteria** are met
2. **Run all tests** and ensure passing
3. **Complete the Completion Report** with:
   - Validation results
   - Known issues
   - **Detailed notes for successor team**
4. **Update Epic progress** in the epic file
5. **Link PRs** to the issue

---

## 📚 Reference Documents

| Document | Purpose |
|----------|---------|
| `handbook.md` | Development workflow |
| `ARCHITECTURE_BLUEPRINT.md` | System architecture |
| `CONTRIBUTING.md` | Contribution guidelines |
| `project_management/epics/EPIC_OVERVIEW.md` | All epics |
| `concept/requirements/*.md` | Feature requirements |

---

## ✅ Checklist for Issue Authors

Before assigning an issue to an external team:

- [ ] Criticality disclaimer included
- [ ] Architectural context explained
- [ ] All task steps clearly defined
- [ ] File paths are accurate and complete
- [ ] Constraints clearly stated (especially "NO MOCK DATA")
- [ ] Acceptance criteria are specific and testable
- [ ] Reference documents linked
- [ ] Completion Report template created
- [ ] Dependencies clearly listed

---

## 🚨 Common Mistakes to Avoid

1. **Creating Mock Data**: NEVER do this - use real test datasets
2. **Skipping Completion Report**: Always document for the next team
3. **Vague Acceptance Criteria**: Be specific and measurable
4. **Missing File Paths**: Always include exact paths
5. **Ignoring Dependencies**: Check predecessor completion reports
6. **No Validation**: Always validate with real data
7. **Poor Handoff Notes**: Write as if explaining to someone new

---

*Last Updated: 2025-11-26*
