---
name: markdown-report
description: Generates structured Markdown reports from data or documents. Use when the user asks to write a report, produce a formatted analysis, or create a data summary document.
---

# Markdown Report

Generate a report using the template in [reference.md](reference.md), then validate before delivering.

## Checklist

- [ ] 1. Identify report type and key data points from the source
- [ ] 2. Draft report using template from [reference.md](reference.md)
- [ ] 3. Write output to a `.md` file
- [ ] 4. Run: `python scripts/validate_report.py <file>`
- [ ] 5. Fix any errors; re-run until `OK`

Never skip validation. Deliver only after the script prints `OK`.

## Execution marker

```
✅ [Skill: markdown-report executed]
```
