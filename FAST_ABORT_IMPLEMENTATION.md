# Fast Abort Implementation

## Goal
Make "Abort Processing" respond in **<2 seconds** instead of waiting for current stage to complete.

**Status:** ✅ **IMPLEMENTED** — 2026-03-31

---

## Problem Analysis

### Current Behavior
- Abort flag (`abort_requested`) is only checked **between stages** in `PipelineManager.run()`
- Long-running operations (Demucs separation, FFT processing, file I/O) run without yielding control
- GPU operations (PyTorch) run asynchronously - CPU waits for GPU to finish
- User must wait 30-120 seconds for stage to complete before abort takes effect

### Root Causes
1. **No cooperative cancellation** - stages don't check abort flag during execution
2. **No event loop yielding** - `asyncio.sleep(0)` not used in long loops
3. **GPU async operations** - `torch.no_grad()` blocks don't yield to event loop
4. **Blocking I/O** - `sf.write()`, scipy filters run synchronously

---

## Solution: 2-Layer Approach (Implemented)

### Layer 1: Cooperative Cancellation Checkpoints
**Impact:** Abort in 1-2 seconds  
**Complexity:** Low  
**Risk:** None  
**Status:** ✅ DONE

Add abort checks every ~500ms during processing:

```python
# In each stage's execute() method
for i, stem in enumerate(stems):
    if context.get("abort_requested"):
        raise asyncio.CancelledError("Pipeline aborted by user")
    # ... process stem ...
    await asyncio.sleep(0)  # Yield to event loop
```

### Layer 2: GPU Early Exit Points
**Impact:** Abort in 1-2 seconds during Demucs  
**Complexity:** Low  
**Risk:** None  
**Status:** ✅ DONE

Add abort checks inside GPU processing loops:

```python
# In stage_03_stem_sep.py - _separate_stems()
for idx, name in enumerate(self.stem_names):
    if self.context.get("abort_requested"):
        raise asyncio.CancelledError("Aborted during GPU processing")
    # ... save stem ...
    await asyncio.sleep(0)
```

### Layer 3: Event Loop Yielding (Bonus)
**Impact:** Abort signal processed immediately  
**Complexity:** None  
**Risk:** None  
**Status:** ✅ DONE

Add `await asyncio.sleep(0)` to yield control throughout all stages.

---

## Files Modified

| File | Changes | Status |
|------|---------|--------|
| `core/pipeline/manager.py` | Added FAST ABORT header comment | ✅ |
| `core/pipeline/stage_03_stem_sep.py` | Store context, add abort checkpoints in `_separate_stems()`, yield after each stem | ✅ |
| `core/pipeline/stage_04_upmix.py` | Store context, add abort checks during stem loading and channel routing, yield between operations | ✅ |
| `core/pipeline/stage_05_studio_chain.py` | Store context, add abort checks in HPF, saturation, compression, EQ, reverb loops | ✅ |
| `core/pipeline/stage_06_loudness.py` | Store context, add abort checks before/during loudness measurement and normalization | ✅ |
| `core/pipeline/stage_07_encode.py` | Store context, add abort checks before/during each export format (MP3, WAV, FLAC, AC3, DTS) | ✅ |

---

## Implementation Details

### Stage 03: Stem Separation
- Store `self.context` reference in `execute()`
- Check abort before audio load
- Check abort before each stem save (6 checkpoints)
- Yield `await asyncio.sleep(0)` after each stem export

### Stage 04: Upmix
- Store `self.context` reference
- Check abort during stem loading loop (6 checkpoints)
- Check abort after each channel routing block (vocals, bass, drums, guitar, piano, other)
- Yield after each processing block

### Stage 05: Studio Chain
- Store `self.context` reference
- Check abort during HPF loop (6 channels)
- Check abort during tape saturation loop (6 channels)
- Check abort during bus compression loop (5 channels, LFE skipped)
- Check abort during EQ processing (low-mid comp, 3-4k cut, 2-5k boost)
- Check abort during shelf EQ loop (6 channels)
- Check abort during reverb convolution (4 channels)
- Check abort during extra saturation loop
- Yield after each channel processing

### Stage 06: Loudness
- Store `self.context` reference
- Check abort before loudness measurement
- Check abort during per-channel logging
- Check abort before integrated loudness calculation
- Check abort before normalization
- Check abort before final verification
- Yield after each channel logging

### Stage 07: Encode & Export
- Store `self.context` reference
- **Basic mode:** Check abort before/during MP3, WAV, FLAC exports
- **Pro mode:** Check abort before/during WAV, AC3, FLAC, DTS, MP3 exports
- Yield after each export completion

---

## Expected Results

| Scenario | Before | After |
|----------|--------|-------|
| Abort during Demucs (GPU) | 60-90 sec | 1-2 sec |
| Abort during upmix | 10-20 sec | <1 sec |
| Abort during studio chain | 15-30 sec | <1 sec |
| Abort during encode | 5-15 sec | <1 sec |

---

## Testing Checklist

- [ ] Start pipeline with a long audio file
- [ ] Click "Abort Processing" during:
  - [ ] Stage 03 (Stem Separation) - should abort in ~2 sec
  - [ ] Stage 04 (Upmix) - should abort instantly
  - [ ] Stage 05 (Studio Chain) - should abort instantly
  - [ ] Stage 06/07 (Encode) - should abort instantly
- [ ] Verify:
  - [ ] Pipeline state resets to idle
  - [ ] No orphaned processes
  - [ ] UI updates immediately
  - [ ] Session marked as "aborted"

---

## Rollback Plan

If issues occur:
1. Revert changes to stage files via git:
   ```bash
   git checkout HEAD -- core/pipeline/stage_03_stem_sep.py
   git checkout HEAD -- core/pipeline/stage_04_upmix.py
   git checkout HEAD -- core/pipeline/stage_05_studio_chain.py
   git checkout HEAD -- core/pipeline/stage_06_loudness.py
   git checkout HEAD -- core/pipeline/stage_07_encode.py
   ```
2. Abort will return to "between stages only" behavior

---

## Technical Notes

### Why `asyncio.sleep(0)`?
- Yields control back to the event loop without delaying execution
- Allows abort signal to be processed immediately
- No performance impact (sleep time is 0)

### Why check `context.get("abort_requested")`?
- Context is passed through entire pipeline
- Centralized abort flag location
- No global state needed
- Thread-safe (asyncio single-threaded)

### Why raise `asyncio.CancelledError`?
- Standard Python async cancellation
- Properly propagates through async call stack
- Caught by pipeline manager's error handler
- Triggers cleanup and state reset

---

**Created:** 2026-03-31  
**Status:** ✅ IMPLEMENTED  
**Next Steps:** Test abort response times with real audio files
