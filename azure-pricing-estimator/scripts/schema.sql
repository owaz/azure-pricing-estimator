BEGIN IMMEDIATE;
CREATE TEMP TABLE schema_assertion (valid INTEGER NOT NULL CHECK (valid = 1));
INSERT INTO schema_assertion
SELECT CASE
  WHEN (SELECT application_id FROM pragma_application_id) = 0
   AND (SELECT user_version FROM pragma_user_version) = 0
   AND NOT EXISTS (SELECT 1 FROM sqlite_master WHERE name NOT LIKE 'sqlite_%')
    THEN 1
  WHEN (SELECT application_id FROM pragma_application_id) = 1095783252
   AND (SELECT user_version FROM pragma_user_version) = 1
   AND (SELECT count(*) FROM sqlite_master
        WHERE type = 'table' AND name IN ('requests', 'run_lock')) = 2
    THEN 1
  ELSE 0 END;
INSERT INTO schema_assertion
SELECT CASE WHEN (SELECT quick_check FROM pragma_quick_check LIMIT 1) = 'ok'
  THEN 1 ELSE 0 END;
CREATE TABLE IF NOT EXISTS run_lock (
  singleton INTEGER PRIMARY KEY CHECK (singleton = 1),
  owner TEXT NOT NULL CHECK (length(owner) = 32),
  expires_at INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS requests (
  message_hash TEXT PRIMARY KEY NOT NULL CHECK (length(message_hash) = 64),
  reference TEXT NOT NULL UNIQUE DEFAULT (lower(hex(randomblob(16)))),
  status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'blocked', 'completed')),
  estimate_state TEXT NOT NULL DEFAULT 'pending' CHECK (estimate_state IN ('pending', 'started', 'done')),
  draft_state TEXT NOT NULL DEFAULT 'pending' CHECK (draft_state IN ('pending', 'started', 'done')),
  teams_state TEXT NOT NULL DEFAULT 'pending' CHECK (teams_state IN ('pending', 'started', 'done')),
  estimate_receipt TEXT NOT NULL DEFAULT '',
  draft_receipt TEXT NOT NULL DEFAULT '',
  teams_receipt TEXT NOT NULL DEFAULT '',
  reason TEXT NOT NULL DEFAULT '',
  updated_at INTEGER NOT NULL,
  CHECK (draft_state = 'pending' OR estimate_state = 'done'),
  CHECK (teams_state = 'pending' OR draft_state = 'done'),
  CHECK (status <> 'completed' OR
    (estimate_state = 'done' AND draft_state = 'done' AND teams_state = 'done')),
  CHECK ((estimate_state = 'done') = (length(estimate_receipt) = 64)),
  CHECK ((draft_state = 'done') = (length(draft_receipt) = 64)),
  CHECK ((teams_state = 'done') = (length(teams_receipt) = 64))
);
-- The adapter's extension marker distinguishes a legacy database from lost checkpoints.
INSERT INTO schema_assertion
SELECT CASE WHEN __ARTIFACTS_REQUIRED__ = 0 OR EXISTS (
  SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'estimate_artifacts'
) THEN 1 ELSE 0 END;
INSERT INTO schema_assertion
SELECT CASE WHEN EXISTS (
  SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'estimate_artifacts'
) OR NOT EXISTS (
  SELECT 1 FROM run_lock WHERE expires_at > CAST(strftime('%s', 'now') AS INTEGER)
    AND owner <> '__OWNER__'
) THEN 1 ELSE 0 END;
CREATE TABLE IF NOT EXISTS estimate_artifacts (
  message_hash TEXT NOT NULL REFERENCES requests(message_hash),
  source_hash TEXT NOT NULL CHECK (length(source_hash) = 64 AND source_hash NOT GLOB '*[^0-9a-f]*'
    AND instr(source_hash, char(0)) = 0),
  state TEXT NOT NULL CHECK (state IN ('started', 'done')),
  intent_hash TEXT NOT NULL CHECK (length(intent_hash) = 64 AND intent_hash NOT GLOB '*[^0-9a-f]*'
    AND instr(intent_hash, char(0)) = 0),
  saved_id_hash TEXT NOT NULL DEFAULT '',
  updated_at INTEGER NOT NULL CHECK (typeof(updated_at) = 'integer' AND updated_at >= 0),
  PRIMARY KEY (message_hash, source_hash),
  CHECK ((state = 'started' AND saved_id_hash = '') OR
    (state = 'done' AND length(saved_id_hash) = 64 AND saved_id_hash NOT GLOB '*[^0-9a-f]*'
      AND instr(saved_id_hash, char(0)) = 0))
);
CREATE UNIQUE INDEX IF NOT EXISTS estimate_artifacts_saved_id
  ON estimate_artifacts (saved_id_hash) WHERE state = 'done';
PRAGMA application_id = 1095783252;
PRAGMA user_version = 1;
DROP TABLE schema_assertion;
COMMIT;
