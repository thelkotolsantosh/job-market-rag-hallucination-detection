# Data dictionary

This is based on the four uploaded CSV files. It deliberately does not invent lookup names for code columns.

| File | Field | What I know from the file |
|---|---|---|
| `benefits.csv` | `job_id` | Join key |
| `benefits.csv` | `inferred` | `0` or `1` inference flag; `1` must not be presented as confirmed |
| `benefits.csv` | `type` | Benefit text such as `Medical insurance` or `401(k)` |
| `job_industries.csv` | `job_id` | Join key |
| `job_industries.csv` | `industry_id` | Numeric industry identifier; there is no industry-name lookup here |
| `job_skills.csv` | `job_id` | Join key |
| `job_skills.csv` | `skill_abr` | Skill abbreviation such as `IT`, `MRKT`, `SALE` |
| `salaries.csv` | `salary_id` | Identifier for salary row |
| `salaries.csv` | `job_id` | Join key |
| `salaries.csv` | `max_salary` | Maximum salary as recorded; often blank |
| `salaries.csv` | `med_salary` | Median salary as recorded; often blank |
| `salaries.csv` | `min_salary` | Minimum salary as recorded; often blank |
| `salaries.csv` | `pay_period` | Values include `YEARLY`, `HOURLY`, `MONTHLY`, `WEEKLY`, `BIWEEKLY` |
| `salaries.csv` | `currency` | Currency code, mostly USD in this input |
| `salaries.csv` | `compensation_type` | Compensation type; the supplied records use `BASE_SALARY` |

## Counts I measured

| CSV | Rows | Distinct job IDs |
|---|---:|---:|
| `benefits.csv` | 67,943 | 30,023 |
| `job_industries.csv` | 164,808 | 127,125 |
| `job_skills.csv` | 213,768 | 126,807 |
| `salaries.csv` | 40,785 | 40,785 |

Across all files there are **128,427 distinct job IDs**. Of these, **11,643** appear in all four files. An absent row in a file does not necessarily imply that the real-world job lacks that benefit or salary.

## Missing information

These files do **not** include a company table, job title, job description, location, mappings of industry IDs to names or a mapping of skill abbreviations to full labels. A production version should acquire licensed, authoritative lookup tables before expanding those fields.

## Row references

The displayed citation `benefits.csv:2` means the second CSV record when the header is counted as row 1. This is derived during ingestion. It identifies a row in the original uploaded file, but it is not a stable ID across dataset revisions. For stronger provenance, store a file hash and version number.
