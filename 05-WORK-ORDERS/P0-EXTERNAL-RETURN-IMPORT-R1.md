# P0-EXTERNAL-RETURN-IMPORT-R1

**Status:** WAIT_EXTERNAL_RESULT_BUNDLE

The external execution handoff is complete.

Next scientific action requires at least one returned external result bundle produced by:

`external-handoff/common/collect_return.py`.

Preferred first returns:
1. MBE Behavioral-Lift;
2. ENF safe-control-gym;
3. WMR ARC-AGI-3;
4. LongMemEval-V2;
5. TCV;
6. MF SkillsBench;
7. SCB P×R.

On return:
- verify ZIP CRC and RETURN-ENVELOPE;
- verify source/data pins;
- verify leakage/resource contracts;
- import raw outputs before computing verdicts;
- runtime failures remain UNTESTED;
- do not promote from a PARTIAL_RETURN.
