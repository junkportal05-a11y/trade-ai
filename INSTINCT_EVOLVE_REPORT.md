# Instinct Evolution Report

**Command**: `python3 ~/.claude/skills/continuous-learning-v2/scripts/instinct-cli.py evolve`

## Result: INSUFFICIENT INSTINCTS

The evolve command requires **at least 3 instincts** to analyze patterns and generate evolution candidates, but currently has **0 instincts** collected.

```
Need at least 3 instincts to analyze patterns.
Currently have: 0
```

## What This Means

The `continuous-learning-v2` system uses **instincts** as the fundamental unit of learned knowledge - compact, evidence-bounded patterns extracted from previous sessions. These instincts drive:

- **Skill/command/agent candidate generation** from trigger and domain clustering
- **Project -> global promotion** candidates
- **Context optimization** and task prioritization

Without at least 3 instincts, the system cannot:
- Perform pattern analysis across collected learnings
- Generate evolution candidates for skills, commands, or agents
- Identify promotion candidates from project to global scope
- Provide meaningful instinct-based recommendations

## Next Steps to Enable Evolution

### 1. Collect Instincts First

Instincts are typically collected automatically via the hook system during sessions. To collect instincts:

- Run tasks/sessions that trigger the learning hooks
- Ensure the continuous-learning-v2 hooks are active in your configuration
- After several sessions, instincts should accumulate to the required minimum of 3

### 2. Manual Instinct Import (if available)

Check if there are existing instincts to import:

```bash
# List available instincts
python3 ~/.claude/skills/continuous-learning-v2/scripts/instinct-cli.py list

# Import from a specific source
python3 ~/.claude/skills/continuous-learning-v2/scripts/instinct-cli.py import <source>
```

### 3. Wait for Natural Accumulation

The system is designed to collect instincts instinctively (hence the name) through:
- Session hooks that observe and extract patterns
- Cross-session learning that persists between runs
- Project-scoped instincts (v2.1+) that prevent cross-project contamination

### 4. Once 3+ Instincts Are Available

The evolve command will then:

```
1. Analyze existing instincts for pattern clustering
2. Show skill/command/agent candidates from trigger/domain clustering
3. Display project -> global promotion candidates
4. With --generate: output evolved files under:
   - project: ~/.claude/homunculus/projects/<project-id>/evolved/
   - global: ~/.claude/homunculus/evolved/
```

## Current Project State

- **Project**: `trade.ai` (C:\Users\aryan\OneDrive\Desktop\app\projects\trade.ai)
- **Instincts collected**: 0
- **Minimum required**: 3
- **Status**: Collect instincts before evolution can proceed

## Recommendation

Continue with normal Paperclip/OpenCode work. Instincts will be collected naturally through the hook system as sessions run. After approximately 3-5 significant sessions, the evolve command should become available for analysis and candidate generation.

## Related Skills

- `continuous-learning-v2` - The v2 learning system that manages instincts
- `skill-stocktake` - Audit existing skills and commands for quality
- `config-gc` - Garbage collection for config, may help manage instinct storage