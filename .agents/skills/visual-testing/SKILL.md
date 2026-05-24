---
name: visual-testing
description: Use when testing frontend pages for visual correctness, layout issues, broken UI elements, or responsive behavior. Triggers after implementing UI changes, before reporting a page "works", or when asked to test a web page. Use when you might otherwise say "the code looks correct" without actually seeing the rendered page.
---

# Visual Testing

## Overview

**Visual testing IS seeing the rendered page, not reading the code.** Code review finds logic bugs; screenshots find layout breaks, overflow issues, color contrast problems, and missing elements.

**Core principle:** If you haven't taken a screenshot of a page and looked at it with your own eyes, you haven't tested that page. Period.

**CRITICAL: Visual testing is NOT code review.** Reading component code, checking API responses, or verifying TypeScript types does NOT count as visual testing. Only a screenshot reveals:
- Overlapping elements, truncated text, broken layouts
- Color/contrast issues, missing icons, misaligned items
- Overflow, scrollbar behavior, responsive breakpoints
- Animation glitches, loading state flicker, empty state rendering

## Prerequisites

- **browser-use MCP must be configured and connected** — verify with `browser_list_sessions` or a quick `browser_navigate` + `browser_screenshot` before starting
- **Dev server must be running** — start with `npm run dev` (or equivalent)
- If browser-use fails to connect, check: is a browser instance available? (Chromium/Chrome with CDP enabled)

## When to Use

**Use when:**
- You implemented a new UI component or page
- You changed CSS, Tailwind classes, or layout logic
- You're asked to "test" or "verify" a page works
- Before merging any frontend change
- A user reports a visual bug

**Do NOT use when:**
- Testing backend-only API changes (use unit/integration tests)
- The change has zero visual impact (e.g., refactoring a utility function)

## Core Pattern

```
┌─────────────────┐
│ Page to test?   │
└────────┬────────┘
         │
    ┌────▼─────────────────────┐
    │ 1. Navigate with         │
    │    browser_navigate       │
    └────┬─────────────────────┘
         │
    ┌────▼─────────────────────┐
    │ 2. Screenshot + inspect  │
    │    browser_get_state      │
    └────┬─────────────────────┘
         │
    ┌────▼─────────────────────┐
    │ 3. Does it look right?   │─── NO ──► File bug on worktree
    └────┬─────────────────────┘              then fix
         │ YES
    ┌────▼─────────────────────┐
    │ 4. Test interactions:    │
    │   - Click buttons        │
    │   - Type in inputs       │
    │   - Scroll, resize       │
    │   - Hover, open modals   │
    └────┬─────────────────────┘
         │
    ┌────▼─────────────────────┐
    │ 5. Screenshot again      │
    │    after each interaction│
    └────┬─────────────────────┘
         │
    ┌────▼─────────────────────┐
    │ 6. Report with screenshots│
    │    as evidence            │
    └──────────────────────────┘
```

## Testing Workflow

### Step 1: Two-Source Test Plan

Before opening the browser, create a test plan from TWO sources:

**Source A — User Description** (if provided):
- What should the user be able to do on this page?
- What are the critical user journeys?

**Source B — Code Inspection** (read the component files):
- What UI elements exist? (buttons, inputs, modals, tabs)
- What states should be tested? (empty, loading, populated, error)
- What interactions exist? (click, hover, drag, scroll)

Merge A + B into a checklist. **Do not skip elements found in code just because the user didn't mention them.**

### Step 2: Visual Baseline

```
browser_navigate → URL
browser_screenshot → full_page: true
browser_get_state → include_screenshot: true
```

**What to check in the screenshot:**
- Page renders without blank/white screen
- All expected elements are visible
- Text is not truncated or overlapping
- Colors and spacing look intentional
- No horizontal scrollbar on desktop viewport

### Step 3: Interaction Testing

For each interactive element found in Step 1:

1. **Get state** → find element index via `browser_get_state`
2. **Interact** → `browser_click` or `browser_type`
3. **Screenshot** → verify visual result
4. **Assert** → did it behave as expected?

### Step 4: Bug Reporting

If something looks wrong:
1. **Screenshot the issue** (evidence, not description)
2. **Describe the expected behavior**
3. **Describe the actual behavior**
4. **File on the worktree** — do NOT fix on main branch

## Quick Reference

| What to Test | How |
|---|---|
| Page renders | `browser_screenshot` on load |
| Button clicks | `browser_get_state` → `browser_click` → screenshot |
| Form inputs | `browser_type` → screenshot → verify value |
| Modal/dialog open | Click trigger → screenshot → check overlay |
| Scroll behavior | `browser_scroll` → screenshot → check content |
| Empty state | Navigate with no data → screenshot |
| Responsive | Resize viewport → screenshot |
| Loading state | Trigger async action → screenshot before resolve |

## Common Mistakes

| Mistake | Fix |
|---|---|
| "I reviewed the component code and it looks fine" | Code ≠ rendering. Open the browser. |
| "The API returns correct data so the page must work" | Data can be correct but UI can still break. |
| "I clicked the button and it didn't error" | Did the VISUAL result look right? Screenshot it. |
| Testing only the happy path | Test empty states, error states, loading states. |
| One screenshot per page | Each interaction needs its own screenshot. |

## Real-World Impact

In baseline testing without this skill, agents consistently:
- Reviewed React component code instead of opening the browser
- Verified API responses but never took a screenshot
- Found 6 code-level issues but **zero visual issues**
- Rationalized: "efficient" and "structurally OK"

With visual testing:
- Layout breaks, overlapping text, and color issues are caught immediately
- Empty states and error boundaries are actually seen, not assumed
- Screenshots serve as evidence, not memory

## Red Flags — STOP and Open the Browser

- About to say "the code looks correct"
- About to report "page works" without a screenshot
- About to verify a UI change by reading a diff
- About to say "I manually verified it" without visual evidence
- About to call API testing "sufficient" for a frontend change

**All of these mean: Stop. Open the browser. Take a screenshot.**
