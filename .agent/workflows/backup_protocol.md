---
description: Backup protocol before modifying code
---

Before modifying any code file (especially `app.py` or `app_keyloop.py`), you MUST create a backup in the `backup/` directory.

# Naming Convention
Format: `MMDD_HH_MM_backup[_KL].txt`

1. **Timestamp**: Get current month, day, hour, minute. (e.g., 1211_14_54 for Dec 11, 14:54)
2. **Suffix**:
   - If the target file is `app_keyloop.py`, append `_KL`.
   - Result: `1211_14_54_backup_KL.txt`
   - Otherwise: `1211_14_54_backup.txt`

# Workflow Steps
1. Determine current time.
2. Construct filename based on the rule above.
3. Run command: `copy [TargetFile] backup\[NewFilename]`
4. Proceed with code modifications.
