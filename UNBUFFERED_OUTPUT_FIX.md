# Unbuffered Output Fix for KBase Logs

**Date:** 2026-02-17
**Issue:** KBase app running 16+ minutes with NO logs visible

## Root Cause: Python Output Buffering

Python buffers stdout by default. With buffering:
- `print()` statements write to buffer, not immediately to stdout
- Buffer doesn't flush until:
  - Process completes
  - Buffer fills (could be MB of data)
  - Explicit `flush()` called
  - OR Python runs in unbuffered mode

**Result:** Logs don't appear in KBase UI even though code is executing!

## The Fix: Unbuffered Python

### Before (run_async.sh)
```bash
python -m KBDatalakeDashboard.KBDatalakeDashboardServer
```
**Problem:** Python runs in buffered mode, no logs visible

### After (run_async.sh)
```bash
export PYTHONUNBUFFERED=1
python -u -m KBDatalakeDashboard.KBDatalakeDashboardServer
```
**Solution:**
- `-u` flag: Unbuffered binary stdout/stderr
- `PYTHONUNBUFFERED=1`: Environment variable for unbuffered mode
- Both together ensure ALL output appears immediately

## Additional Improvements

### 1. Debug logging in run_async.sh
```bash
echo "=================================================="
echo "Starting KBDatalakeDashboard server"
echo "PYTHONPATH: $PYTHONPATH"
echo "Config: $KB_DEPLOYMENT_CONFIG"
echo "=================================================="
```
**Benefit:** Confirms script is actually executing

### 2. Debug logging in __init__
```python
print("=" * 80, flush=True)
print("KBDatalakeDashboard __init__ called", flush=True)
print(f"Callback URL: {self.callback_url}", flush=True)
print(f"Shared folder: {self.shared_folder}", flush=True)
print("Initializing DataFileUtil...", flush=True)
print("DataFileUtil initialized successfully", flush=True)
print("=" * 80, flush=True)
```
**Benefit:** Verifies module initialization

### 3. Flushed prints in run_genome_datalake_dashboard
```python
import sys
print("START: run_genome_datalake_dashboard", flush=True)
sys.stdout.flush()
# ... more prints with flush=True throughout
```
**Benefit:** Every operation is logged immediately

## Expected Log Output (Next Deployment)

```
==================================================
Starting KBDatalakeDashboard server
PYTHONPATH: /kb/module/lib:...
Config: /kb/module/deploy.cfg
==================================================
================================================================================
KBDatalakeDashboard __init__ called
Config keys: ['scratch', 'workspace-url', ...]
Callback URL: http://...
Shared folder: /kb/module/work/tmp
Initializing DataFileUtil...
DataFileUtil initialized successfully
================================================================================
================================================================================
START: run_genome_datalake_dashboard
Params: {'workspace_name': '...', 'input_ref': '...'}
================================================================================
Validating parameters...
Parameters validated successfully
Workspace: ..., Input ref: ...
Creating output directory...
Output directory: /kb/module/work/tmp/abc123-...
Copying HTML directory from /kb/module/data/html...
HTML directory copied successfully
Copying heatmap viewer...
Heatmap directory: /kb/module/work/tmp/abc123-.../heatmap
Heatmap viewer copied successfully
Writing app-config.json...
Wrote app-config.json to /kb/module/work/tmp/abc123-.../app-config.json
Wrote app-config.json to /kb/module/work/tmp/abc123-.../heatmap/app-config.json
Directory size to upload: 2.3M
Uploading HTML directory to Shock...
This may take a while for large directories...
```

**Then either:**
- Upload completes → "Upload complete! Shock ID: ..."
- Upload hangs → We see exactly where it stops

## Why This Matters

**Before:** App runs for hours with no visibility
- Can't debug
- Can't identify bottleneck
- Complete black box

**After:** Real-time logs showing every step
- See where it hangs (likely Shock upload)
- Can measure timing
- Can add timeout or optimize

## Commits

1. **28bb4db** - Added print logging (but still buffered)
2. **99e55c7** - Added flush=True to prints (helped but not enough)
3. **LATEST** - Unbuffered Python mode (should finally work!)

## Test Plan

1. Re-run "Run Genome Datalake Dashboard" in KBase
2. Immediately check logs - should see:
   ```
   ==================================================
   Starting KBDatalakeDashboard server
   ```
3. Within 10 seconds, should see:
   ```
   KBDatalakeDashboard __init__ called
   ```
4. Within 30 seconds, should see:
   ```
   START: run_genome_datalake_dashboard
   ```
5. If logs appear → SUCCESS! Identify actual bottleneck
6. If logs still don't appear → Deeper issue (not output buffering)

## References

- Python `-u` flag: https://docs.python.org/3/using/cmdline.html#cmdoption-u
- PYTHONUNBUFFERED: https://docs.python.org/3/using/cmdline.html#envvar-PYTHONUNBUFFERED
- Python buffering: https://docs.python.org/3/library/sys.html#sys.stdout

## Next Steps After Logs Appear

Once logs are visible, we'll likely see it's hanging on:
1. **Shock upload** - zipping and uploading ~2-3MB directory
   - Solution: Add timeout, or exclude large files, or stream upload
2. **Data file copying** - shutil.copytree might be slow
   - Solution: Profile with time.time() around each operation
3. **DataFileUtil initialization** - might be making network calls
   - Solution: Add timeout or caching

But we won't know until **logs actually appear**!
