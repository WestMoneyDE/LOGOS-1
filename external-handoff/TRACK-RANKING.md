# External execution ranking

Ranking is based on scientific information gain versus current execution friction, not on importance of the underlying theory.

| Rank | Track | Information gain | Friction | Primary blocker |
|---:|---|---|---|---|
| 1 | MBE Behavioral-Lift | High | Low | Mount/download official 8,282-row LLM split |
| 2 | ENF safe-control-gym | High | Low–medium | Install pinned simulator dependencies |
| 3 | WMR ARC-AGI-3 | High | Medium | Official SDK + public game cache |
| 4 | LongMemEval-V2 | Very high | High | Dataset + reader/embedding endpoints + judge |
| 5 | TCV Wrong but Useful | High | High | Official ancillary + repeated model backends |
| 6 | MF SkillsBench | High | High | BenchFlow/Docker + many agent trials |
| 7 | SCB P×R | Very high | Very high | Joint Skill-Usage/AgentRewind/Harbor integration |
| — | TANGLE | High | Release-blocked | Official benchmark artifact not yet resolved |

MBE and ENF are first because they can deliver high-value external evidence with the least execution friction. SCB P×R is intentionally last because it depends on multiple source ecosystems and a common recovery-capable Terminal-Bench runtime.
