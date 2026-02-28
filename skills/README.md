
# 🚀 Antigravity Career Agent Skills

> Enterprise-grade AI agent skills for crafting job-winning emails,
> cover letters, and CVs/resumes targeting US, EU, and Asia markets.

## Skills Included

| Skill | Description |
|-------|-------------|
| `01-email-writing` | 5 proven email frameworks for job search communication |
| `02-cover-letter-writing` | 5 global cover letter formats with templates |
| `03-cv-resume-writing` | 5 CV/resume formats optimized for ATS + human readers |
| `04-regional-adaptation` | Region-specific rules for US, EU (DACH/Nordic/UK), Asia |
| `05-ats-optimization` | Keyword extraction, formatting rules, score maximization |

## Quick Start

```yaml
# In your agent config, reference skills like:
skills:
  - path: ./skills/01-email-writing/skill.md
  - path: ./skills/02-cover-letter-writing/skill.md
  - path: ./skills/03-cv-resume-writing/skill.md
  - path: ./skills/04-regional-adaptation/skill.md
  - path: ./skills/05-ats-optimization/skill.md
  - path: ./skills/_shared/tone-guidelines.md
  - path: ./skills/_shared/power-verbs.md
Architecture
Each skill.md follows the structure:

ROLE — Who the agent becomes
CONTEXT — When to activate this skill
FORMATS — The exact templates with placeholders
RULES — Hard constraints and guardrails
EXAMPLES — Gold-standard outputs
ANTI-PATTERNS — What to never do
text
