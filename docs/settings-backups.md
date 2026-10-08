# Settings backup compatibility

New settings backups begin with `# SetupHelper settingsBackup JSONL v1`. Each
following line is a JSON array containing either the setting path and value, or
those fields followed by type, default, minimum, maximum and silent attributes.
Values and attributes remain strings. JSON escaping preserves commas, quotes,
Unicode, carriage returns and embedded newlines without creating extra records.

The updated restore operation also reads existing unmarked backups using their
original two-field or seven-field comma-separated format. It preserves that
legacy interpretation, including literal quotes. An old backup that already
split an embedded newline or comma cannot be reconstructed automatically;
create a fresh backup from the source device when possible.

Update SetupHelper on the restore destination before using a new-format backup.
Older SetupHelper versions do not understand the version header or JSON records.
Keep an existing backup until the replacement has been verified. Unknown future
format versions are rejected, and malformed records are reported by line number
without exposing setting values in logs.

This change affects only `settingsBackup` records. It does not change the layout
of separately backed-up setup options, overlays or logs. Automated tests exercise
real temporary backup files with simulated D-Bus objects; acceptance on actual
hardware remains a separate operator check.
