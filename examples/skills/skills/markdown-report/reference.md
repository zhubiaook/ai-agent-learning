# markdown-report — Report Template

```markdown
# [Report Title]

## Summary
[1-paragraph overview of findings or purpose]

## Data Overview
| Metric | Value |
|--------|-------|
| ...    | ...   |

## Analysis
[Key findings, one sub-section per topic if needed]

## Conclusions & Recommendations
- [Recommendation 1]
- [Recommendation 2]
```

## Validation rules

`validate_report.py` checks:
- File starts with `#` title
- Contains a `## Summary` section
- Has at least 2 `##`-level sections

Adapt section names freely — only `# title` and `## Summary` are required by the validator.
