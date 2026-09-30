BEGIN IMMEDIATE;
CREATE TEMP TABLE input AS SELECT
  '__ACTION__' AS action, '__MESSAGE__' AS message, '__OWNER__' AS owner,
  '__STAGE__' AS stage, '__RECEIPT__' AS receipt, '__REASON__' AS reason,
  '__SOURCE__' AS source,
  CAST(strftime('%s', 'now') AS INTEGER) AS now;
CREATE TEMP TABLE operation_assertion (valid INTEGER NOT NULL CHECK (valid = 1));
INSERT INTO operation_assertion
SELECT CASE WHEN (SELECT application_id FROM pragma_application_id) = 1095783252
  AND (SELECT user_version FROM pragma_user_version) = 1
  AND EXISTS (SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'estimate_artifacts')
  AND EXISTS (SELECT 1 FROM sqlite_master WHERE type = 'index' AND name = 'estimate_artifacts_saved_id')
  THEN 1 ELSE 0 END;
INSERT INTO operation_assertion
SELECT CASE WHEN action IN ('init', 'acquire', 'release', 'status')
  OR EXISTS (SELECT 1 FROM run_lock WHERE singleton = 1
    AND owner = input.owner AND expires_at > input.now)
  THEN 1 ELSE 0 END FROM input;

INSERT OR IGNORE INTO run_lock
SELECT 1, owner, now + 900 FROM input WHERE action = 'acquire';
UPDATE run_lock SET
  owner = (SELECT owner FROM input),
  expires_at = (SELECT now + 900 FROM input)
WHERE (SELECT action FROM input) = 'acquire'
  AND (expires_at <= (SELECT now FROM input) OR owner = (SELECT owner FROM input));
UPDATE run_lock SET expires_at = (SELECT now + 900 FROM input)
WHERE (SELECT action FROM input) = 'heartbeat' AND owner = (SELECT owner FROM input);
DELETE FROM run_lock WHERE (SELECT action FROM input) = 'release'
  AND owner = (SELECT owner FROM input);

INSERT OR IGNORE INTO requests (message_hash, updated_at)
SELECT message, now FROM input WHERE action = 'claim';
INSERT INTO operation_assertion
SELECT CASE WHEN EXISTS (SELECT 1 FROM requests WHERE message_hash = input.message)
  THEN 1 ELSE 0 END FROM input
WHERE action IN ('begin', 'confirm', 'retry-stage', 'block', 'retry', 'complete',
  'artifact-begin', 'artifact-status', 'artifact-confirm', 'artifact-list');
INSERT INTO operation_assertion
SELECT CASE WHEN EXISTS (SELECT 1 FROM requests
  WHERE message_hash = input.message AND status = 'active'
  AND CASE input.stage
    WHEN 'estimate' THEN estimate_state
    WHEN 'draft' THEN draft_state
    WHEN 'teams' THEN teams_state END =
      CASE input.action WHEN 'begin' THEN 'pending' ELSE 'started' END
  AND (input.stage = 'estimate' OR estimate_state = 'done')
  AND (input.stage <> 'teams' OR draft_state = 'done'))
  THEN 1 ELSE 0 END FROM input WHERE action IN ('begin', 'confirm', 'retry-stage');
INSERT INTO operation_assertion
SELECT CASE WHEN length(receipt) = 64 THEN 1 ELSE 0 END FROM input WHERE action = 'confirm';
INSERT INTO operation_assertion
SELECT CASE WHEN EXISTS (SELECT 1 FROM requests WHERE message_hash = input.message
  AND status <> 'completed') THEN 1 ELSE 0 END FROM input WHERE action IN ('block', 'retry');
INSERT INTO operation_assertion
SELECT CASE WHEN EXISTS (SELECT 1 FROM requests WHERE message_hash = input.message
  AND status IN ('active', 'completed') AND estimate_state = 'done'
  AND draft_state = 'done' AND teams_state = 'done') THEN 1 ELSE 0 END
FROM input WHERE action = 'complete';

-- Check all sources before reading or changing checkpoints; never hide a malformed row.
INSERT INTO operation_assertion
SELECT CASE WHEN NOT EXISTS (
  SELECT 1 FROM estimate_artifacts WHERE message_hash = input.message AND NOT COALESCE(
    typeof(source_hash) = 'text' AND length(source_hash) = 64
    AND source_hash NOT GLOB '*[^0-9a-f]*' AND instr(source_hash, char(0)) = 0
    AND typeof(intent_hash) = 'text' AND length(intent_hash) = 64
    AND intent_hash NOT GLOB '*[^0-9a-f]*' AND instr(intent_hash, char(0)) = 0
    AND typeof(saved_id_hash) = 'text'
    AND ((state = 'started' AND saved_id_hash = '') OR
      (state = 'done' AND length(saved_id_hash) = 64
        AND saved_id_hash NOT GLOB '*[^0-9a-f]*' AND instr(saved_id_hash, char(0)) = 0))
    AND typeof(updated_at) = 'integer' AND updated_at >= 0, 0)
) THEN 1 ELSE 0 END FROM input
WHERE action IN ('artifact-begin', 'artifact-status', 'artifact-confirm', 'artifact-list')
  OR (action = 'confirm' AND stage = 'estimate');
INSERT INTO operation_assertion
SELECT CASE WHEN EXISTS (
  SELECT 1 FROM requests WHERE message_hash = input.message
    AND status = 'active' AND estimate_state = 'started'
) AND length(source) = 64 AND length(receipt) = 64 THEN 1 ELSE 0 END
FROM input WHERE action IN ('artifact-begin', 'artifact-confirm');
INSERT INTO operation_assertion
SELECT CASE WHEN NOT EXISTS (
  SELECT 1 FROM estimate_artifacts WHERE message_hash = input.message
    AND source_hash = input.source AND intent_hash <> input.receipt
) THEN 1 ELSE 0 END FROM input WHERE action = 'artifact-begin';
INSERT INTO estimate_artifacts (message_hash, source_hash, state, intent_hash, updated_at)
SELECT message, source, 'started', receipt, now FROM input WHERE action = 'artifact-begin'
  AND NOT EXISTS (SELECT 1 FROM estimate_artifacts
    WHERE message_hash = input.message AND source_hash = input.source);
INSERT INTO operation_assertion
SELECT CASE WHEN EXISTS (
  SELECT 1 FROM estimate_artifacts WHERE message_hash = input.message AND source_hash = input.source
    AND (state = 'started' OR (state = 'done' AND saved_id_hash = input.receipt))
) AND NOT EXISTS (
  SELECT 1 FROM estimate_artifacts WHERE saved_id_hash = input.receipt
    AND (message_hash <> input.message OR source_hash <> input.source)
) THEN 1 ELSE 0 END FROM input WHERE action = 'artifact-confirm';
UPDATE estimate_artifacts SET state = 'done', saved_id_hash = (SELECT receipt FROM input),
  updated_at = (SELECT now FROM input)
WHERE (SELECT action FROM input) = 'artifact-confirm' AND state = 'started'
  AND message_hash = (SELECT message FROM input) AND source_hash = (SELECT source FROM input);
INSERT INTO operation_assertion
SELECT CASE WHEN NOT EXISTS (
  SELECT 1 FROM estimate_artifacts WHERE message_hash = input.message AND state <> 'done'
) THEN 1 ELSE 0 END FROM input WHERE action = 'confirm' AND stage = 'estimate';

UPDATE requests SET
  estimate_state = CASE WHEN (SELECT stage FROM input) = 'estimate'
    THEN CASE (SELECT action FROM input) WHEN 'begin' THEN 'started'
      WHEN 'confirm' THEN 'done' ELSE 'pending' END ELSE estimate_state END,
  draft_state = CASE WHEN (SELECT stage FROM input) = 'draft'
    THEN CASE (SELECT action FROM input) WHEN 'begin' THEN 'started'
      WHEN 'confirm' THEN 'done' ELSE 'pending' END ELSE draft_state END,
  teams_state = CASE WHEN (SELECT stage FROM input) = 'teams'
    THEN CASE (SELECT action FROM input) WHEN 'begin' THEN 'started'
      WHEN 'confirm' THEN 'done' ELSE 'pending' END ELSE teams_state END,
  estimate_receipt = CASE WHEN (SELECT stage FROM input) = 'estimate'
      AND (SELECT action FROM input) = 'confirm'
    THEN (SELECT receipt FROM input) ELSE estimate_receipt END,
  draft_receipt = CASE WHEN (SELECT stage FROM input) = 'draft'
      AND (SELECT action FROM input) = 'confirm'
    THEN (SELECT receipt FROM input) ELSE draft_receipt END,
  teams_receipt = CASE WHEN (SELECT stage FROM input) = 'teams'
      AND (SELECT action FROM input) = 'confirm'
    THEN (SELECT receipt FROM input) ELSE teams_receipt END,
  updated_at = (SELECT now FROM input)
WHERE message_hash = (SELECT message FROM input)
  AND (SELECT action FROM input) IN ('begin', 'confirm', 'retry-stage');
UPDATE requests SET
  status = CASE (SELECT action FROM input)
    WHEN 'block' THEN 'blocked' WHEN 'retry' THEN 'active' ELSE 'completed' END,
  reason = CASE (SELECT action FROM input) WHEN 'block' THEN (SELECT reason FROM input) ELSE '' END,
  updated_at = (SELECT now FROM input)
WHERE message_hash = (SELECT message FROM input)
  AND (SELECT action FROM input) IN ('block', 'retry', 'complete');

SELECT 'init', 1, lower(hex(randomblob(16))) FROM input WHERE action = 'init';
SELECT CASE WHEN EXISTS (SELECT 1 FROM run_lock WHERE owner = input.owner
  AND expires_at > input.now) THEN 'acquired' ELSE 'busy' END,
  (SELECT expires_at FROM run_lock WHERE singleton = 1)
FROM input WHERE action = 'acquire';
SELECT 'heartbeat', (SELECT expires_at FROM run_lock WHERE singleton = 1)
FROM input WHERE action = 'heartbeat';
SELECT 'released' FROM input WHERE action = 'release';
SELECT CASE WHEN status = 'completed' THEN 'skip_completed'
    WHEN status = 'blocked' THEN 'skip_blocked'
    WHEN 'started' IN (estimate_state, draft_state, teams_state) THEN 'reconcile'
    ELSE 'ready' END,
  reference, status, estimate_state, draft_state, teams_state,
  estimate_receipt, draft_receipt, teams_receipt, reason
FROM requests WHERE message_hash = (SELECT message FROM input)
  AND (SELECT action FROM input) IN ('claim', 'status', 'begin', 'confirm',
    'retry-stage', 'block', 'retry', 'complete');
SELECT 'not_found' FROM input WHERE action = 'status'
  AND NOT EXISTS (SELECT 1 FROM requests WHERE message_hash = input.message);
-- Validate persisted fields before either adapter exposes any listing rows.
INSERT INTO operation_assertion
SELECT CASE WHEN NOT EXISTS (
  SELECT 1 FROM requests WHERE status IN ('active', 'blocked') AND NOT (
    length(reference) = 32 AND reference NOT GLOB '*[^0-9a-f]*'
    AND instr(reference, char(0)) = 0
    AND estimate_state IN ('pending', 'started', 'done')
    AND draft_state IN ('pending', 'started', 'done')
    AND teams_state IN ('pending', 'started', 'done')
    AND reason IN ('', 'unreadable_requirements', 'permission_restriction',
      'ambiguous_recipient', 'uncertain_outcome', 'delivery_failed', 'other')
    AND typeof(updated_at) = 'integer' AND updated_at >= 0
  )) THEN 1 ELSE 0 END FROM input WHERE action = 'list-open';
SELECT reference, status, estimate_state, draft_state, teams_state, reason, updated_at
FROM requests WHERE status IN ('active', 'blocked')
  AND (SELECT action FROM input) = 'list-open'
ORDER BY updated_at, reference;
SELECT source_hash, state, intent_hash, saved_id_hash, updated_at
FROM estimate_artifacts WHERE message_hash = (SELECT message FROM input)
  AND ((SELECT action FROM input) = 'artifact-list' OR
    ((SELECT action FROM input) IN ('artifact-begin', 'artifact-status', 'artifact-confirm')
      AND source_hash = (SELECT source FROM input)))
ORDER BY source_hash;
SELECT 'not_found' FROM input WHERE action = 'artifact-status'
  AND NOT EXISTS (SELECT 1 FROM estimate_artifacts
    WHERE message_hash = input.message AND source_hash = input.source);
COMMIT;
