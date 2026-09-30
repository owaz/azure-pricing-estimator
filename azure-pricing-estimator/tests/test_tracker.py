import hashlib
import json
import os
import pathlib
import shutil
import sqlite3
import subprocess
import tempfile
import unittest


SCRIPTS = pathlib.Path(__file__).resolve().parents[1] / "scripts"
ADAPTER = os.environ.get("TRACKER_TEST_ADAPTER", "sh")
POWERSHELL = shutil.which("pwsh") or shutil.which("powershell.exe")
ACCOUNT = "tenant:dummy-user"
MESSAGE = "<dummy-message@example.invalid>"


class TrackerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="pricing-tracker-test-", dir=pathlib.Path.cwd())
        folder = "state space # %" if os.name == "nt" else "state space ? # %"
        self.root = pathlib.Path(self.temp.name) / folder
        self.owner = self.run_tracker("init")[0].split("|")[2]
        self.db = self.root / hashlib.sha256(ACCOUNT.encode()).hexdigest() / "tracker.sqlite3"

    def tearDown(self):
        self.temp.cleanup()

    def run_tracker(self, action, account=ACCOUNT, message=None, owner=None,
                    stage=None, receipt=None, reason=None, source=None, success=True, scripts=SCRIPTS):
        values = {"action": action, "account": account, "state-root": str(self.root)}
        values.update({k: v for k, v in {
            "message": message, "owner": owner, "stage": stage,
            "receipt": receipt, "reason": reason, "source": source,
        }.items() if v is not None})
        if ADAPTER == "pwsh":
            command = [POWERSHELL, "-NoProfile", "-NonInteractive", "-File", str(scripts / "tracker.ps1")]
            names = {"state-root": "StateRoot"}
            for key, value in values.items():
                command.extend(["-" + names.get(key, key.capitalize()), value])
        else:
            command = ["sh", str(scripts / "tracker.sh")]
            for key, value in values.items():
                command.extend(["--" + key, value])
        result = subprocess.run(command, capture_output=True, text=True, timeout=40)
        if success:
            self.assertEqual(result.returncode, 0, result.stderr)
        else:
            self.assertNotEqual(result.returncode, 0, result.stdout)
            self.assertFalse(result.stdout.strip(), "Failed writes must not return success receipts")
        return result.stdout.splitlines()

    def acquire(self, owner=None):
        return self.run_tracker("acquire", owner=owner or self.owner)[0]

    def operation(self, action, **kwargs):
        return self.run_tracker(action, message=MESSAGE, owner=self.owner, **kwargs)

    def expire_lock(self):
        with sqlite3.connect(self.db) as connection:
            connection.execute("UPDATE run_lock SET expires_at=0")

    def start_estimate(self, message=MESSAGE):
        self.run_tracker("claim", message=message, owner=self.owner)
        self.run_tracker("begin", message=message, owner=self.owner, stage="estimate")

    def make_legacy_tracker(self):
        with sqlite3.connect(self.db) as connection:
            self.assertEqual(connection.execute("SELECT count(*) FROM estimate_artifacts").fetchone(), (0,))
            connection.execute("DROP TABLE estimate_artifacts")
        self.db.with_name("initialized-artifacts-v1").unlink()

    def legacy_schema(self):
        schema = (SCRIPTS / "schema.sql").read_text(encoding="utf-8")
        return schema.split("-- The adapter's extension marker", 1)[0] + schema[schema.index("PRAGMA application_id"):]

    def test_initialize_reopen_complete_and_skip(self):
        self.assertTrue(self.acquire().startswith("acquired|"))
        initial = self.operation("claim")[0].split("|")
        self.assertEqual(initial[0], "ready")
        self.assertEqual(len(initial[1]), 32)
        for stage in ("estimate", "draft", "teams"):
            self.operation("begin", stage=stage)
            self.operation("confirm", stage=stage, receipt="dummy-" + stage)
        self.assertTrue(self.operation("complete")[0].startswith("skip_completed|"))
        self.run_tracker("release", owner=self.owner)
        new_owner = self.run_tracker("init")[0].split("|")[2]
        self.assertNotEqual(new_owner, self.owner)
        self.acquire(new_owner)
        self.owner = new_owner
        final = self.operation("claim")[0].split("|")
        self.assertEqual(final[0], "skip_completed")
        self.assertEqual(final[1], initial[1])

    def test_lock_conflict_and_stale_owner_fencing(self):
        self.acquire()
        contender = "a" * 32 if self.owner != "a" * 32 else "b" * 32
        self.assertTrue(self.acquire(contender).startswith("busy|"))
        self.run_tracker("claim", message=MESSAGE, owner=contender, success=False)
        self.expire_lock()
        self.assertTrue(self.acquire(contender).startswith("acquired|"))
        self.operation("claim", success=False)
        self.run_tracker("release", owner=self.owner)
        self.assertTrue(self.acquire().startswith("busy|"))

    def test_stage_order_and_interrupted_side_effect(self):
        self.acquire()
        self.operation("claim")
        self.operation("complete", success=False)
        self.operation("begin", stage="draft", success=False)
        self.operation("confirm", stage="estimate", receipt="dummy", success=False)
        self.operation("begin", stage="estimate")
        self.assertTrue(self.operation("claim")[0].startswith("reconcile|"))
        self.operation("begin", stage="estimate", success=False)
        self.operation("retry-stage", stage="estimate")
        self.operation("begin", stage="estimate")
        self.operation("confirm", stage="estimate", receipt="found-existing-artifact")
        self.operation("begin", stage="estimate", success=False)

    def test_blocked_is_not_completed_and_followup_is_new(self):
        self.acquire()
        self.operation("claim")
        self.operation("block", reason="unreadable_requirements")
        self.assertTrue(self.operation("claim")[0].startswith("skip_blocked|"))
        self.operation("begin", stage="estimate", success=False)
        self.operation("complete", success=False)
        self.assertTrue(self.run_tracker("claim", message="<followup@example.invalid>",
                                        owner=self.owner)[0].startswith("ready|"))
        self.operation("retry")
        self.assertTrue(self.operation("claim")[0].startswith("ready|"))

    def test_accounts_and_identity_normalization(self):
        normalized = self.run_tracker("init", account="  TENANT:DUMMY-USER  ")[0]
        self.assertTrue(normalized.startswith("init|1|"))
        self.assertEqual(len(list(self.root.glob("*/tracker.sqlite3"))), 1)
        self.run_tracker("init", account="tenant:another-user")
        self.assertEqual(len(list(self.root.glob("*/tracker.sqlite3"))), 2)

    def test_inputs_are_hashed_not_executed_or_stored(self):
        self.acquire()
        unusual = "<a'\"; DROP TABLE requests; --\n\u00e9@example.invalid>"
        self.run_tracker("claim", message=unusual, owner=self.owner)
        with sqlite3.connect(self.db) as connection:
            stored = connection.execute("SELECT message_hash FROM requests").fetchone()[0]
            self.assertEqual(stored, hashlib.sha256(unusual.encode()).hexdigest())
        self.assertNotIn(unusual.encode(), self.db.read_bytes())
        self.run_tracker("claim", message=MESSAGE, owner="' OR 1=1--", success=False)
        self.run_tracker("confirm", message=MESSAGE, owner=self.owner, stage="invalid",
                         receipt="dummy", success=False)

    def test_missing_corrupt_and_newer_databases_fail_closed(self):
        self.db.unlink()
        self.run_tracker("init", success=False)
        self.assertFalse(self.db.exists())
        self.run_tracker("status", message=MESSAGE, success=False)
        self.db.write_bytes(b"not a database")
        self.run_tracker("init", success=False)
        self.db.unlink()
        with sqlite3.connect(self.db) as connection:
            connection.execute("PRAGMA application_id=1095783252")
            connection.execute("PRAGMA user_version=2")
        self.run_tracker("init", success=False)

    def test_heartbeat_and_missing_message(self):
        self.acquire()
        self.run_tracker("heartbeat", owner=self.owner)
        self.assertEqual(self.run_tracker("status", message=MESSAGE), ["not_found"])
        self.operation("begin", stage="estimate", success=False)

    def test_list_open_empty_does_not_emit_a_blank_line_or_mutate_state(self):
        self.acquire()
        before = self.db.read_bytes()
        self.assertEqual(self.run_tracker("list-open", owner=self.owner), [])
        self.assertEqual(self.db.read_bytes(), before)
        self.assertEqual(self.run_tracker("list-open", owner=self.owner, message=MESSAGE), [])
        self.assertEqual(self.db.read_bytes(), before)

    def test_list_open_requires_owner_and_live_account_lease(self):
        self.run_tracker("list-open", success=False)
        self.run_tracker("list-open", owner="invalid", success=False)
        self.run_tracker("list-open", owner=self.owner, success=False)
        self.acquire()
        self.operation("claim")
        contender = "a" * 32 if self.owner != "a" * 32 else "b" * 32
        before = self.db.read_bytes()
        self.run_tracker("list-open", owner=contender, success=False)
        self.assertEqual(self.db.read_bytes(), before)
        other_account = "tenant:unacquired-listing"
        self.run_tracker("init", account=other_account)
        self.run_tracker("list-open", account=other_account, owner=self.owner, success=False)
        self.expire_lock()
        before = self.db.read_bytes()
        self.run_tracker("list-open", owner=self.owner, success=False)
        self.assertEqual(self.db.read_bytes(), before)
        self.acquire(contender)
        self.run_tracker("list-open", owner=self.owner, success=False)
        self.assertEqual(len(self.run_tracker("list-open", owner=contender)), 1)
        self.run_tracker("release", owner=contender)
        self.run_tracker("list-open", owner=contender, success=False)

    def test_list_open_exact_rows_order_hash_only_and_unchanged_schema(self):
        self.acquire()
        pending = self.operation("claim")[0].split("|")[1]
        messages = {
            "blocked": "<blocked-private-customer@example.invalid>",
            "started": "<started-private-customer@example.invalid>",
            "completed": "<completed-private-customer@example.invalid>",
        }
        references = {}
        for name, message in messages.items():
            references[name] = self.run_tracker("claim", message=message, owner=self.owner)[0].split("|")[1]
            for stage in ("estimate", "draft", "teams"):
                self.run_tracker("begin", message=message, owner=self.owner, stage=stage)
                if (name, stage) in (("blocked", "draft"), ("started", "teams")):
                    break
                self.run_tracker("confirm", message=message, owner=self.owner, stage=stage,
                                 receipt="private-" + name + "-" + stage)
            if name == "blocked":
                self.run_tracker("block", message=message, owner=self.owner, reason="uncertain_outcome")
            elif name == "completed":
                self.run_tracker("complete", message=message, owner=self.owner)
        with sqlite3.connect(self.db) as connection:
            connection.execute("UPDATE requests SET updated_at=1700000000")
            connection.execute("UPDATE requests SET updated_at=1700000001 WHERE reference=?", (pending,))
            schema = connection.execute("SELECT type, name, sql FROM sqlite_master ORDER BY name").fetchall()
            request_rows = connection.execute("SELECT * FROM requests ORDER BY reference").fetchall()
            lock = connection.execute("SELECT * FROM run_lock").fetchall()
        before = self.db.read_bytes()
        rows = self.run_tracker("list-open", owner=self.owner)
        expected = [
            [pending, "active", "pending", "pending", "pending", "", "1700000001"],
            [references["blocked"], "blocked", "done", "started", "pending", "uncertain_outcome", "1700000000"],
            [references["started"], "active", "done", "done", "started", "", "1700000000"],
        ]
        expected.sort(key=lambda row: (int(row[6]), row[0]))
        self.assertEqual(rows, ["|".join(row) for row in expected])
        self.assertEqual(self.run_tracker("list-open", owner=self.owner), rows)
        for row in rows:
            self.assertRegex(row, r"^[A-Za-z0-9_.:|-]+$")
            self.assertEqual(len(row.split("|")), 7)
            self.assertNotIn(references["completed"], row)
        self.assertEqual(self.db.read_bytes(), before)
        with sqlite3.connect(self.db) as connection:
            self.assertEqual(connection.execute("SELECT type, name, sql FROM sqlite_master ORDER BY name").fetchall(),
                             schema)
            self.assertEqual(connection.execute("SELECT * FROM requests ORDER BY reference").fetchall(), request_rows)
            self.assertEqual(connection.execute("SELECT * FROM run_lock").fetchall(), lock)
            self.assertEqual(connection.execute("PRAGMA user_version").fetchone(), (1,))
            self.assertEqual(connection.execute("PRAGMA application_id").fetchone(), (1095783252,))
            hashes = {row[0] for row in connection.execute("SELECT message_hash FROM requests")}
        self.assertEqual(hashes, {hashlib.sha256(message.encode()).hexdigest()
                                  for message in [MESSAGE, *messages.values()]})
        for private in [ACCOUNT, MESSAGE, *messages.values(), "private-blocked-estimate"]:
            self.assertNotIn(private, "\n".join(rows))
            self.assertNotIn(private.encode(), self.db.read_bytes())
        self.assertEqual(hashlib.sha256(self.legacy_schema().encode()).hexdigest(),
                         "744aa3927ed64ddef2d1100f20cd4f017bee9288b9d10a7affda4127897c52ca")
        self.assertEqual(hashlib.sha256((SCRIPTS / "NativeSqlite.cs").read_bytes()).hexdigest(),
                         "88f837fdf7f40366e389f0b4c959dfe2508e286f9bfb1ce2198451a75a6286a8")

    def test_list_open_rejects_unsafe_fields_without_partial_output(self):
        self.acquire()
        reference = self.operation("claim")[0].split("|")[1]
        self.run_tracker("claim", message="<safe-listing-row@example.invalid>", owner=self.owner)
        with sqlite3.connect(self.db) as connection:
            connection.execute("UPDATE requests SET updated_at=1")
            connection.execute("UPDATE requests SET updated_at=2 WHERE reference=?", (reference,))
            original = connection.execute(
                "SELECT reference, estimate_state, draft_state, teams_state, reason, updated_at "
                "FROM requests WHERE reference=?", (reference,)).fetchone()
        invalid = [
            ("reference", "z" * 32),
            ("reference", reference + "\x00hidden"),
            ("reference", "private|reference"),
            ("estimate_state", "pending\nprivate"),
            ("draft_state", "unsafe"),
            ("teams_state", "\u00e9"),
            ("reason", "customer@example.invalid"),
            ("reason", "other\x00hidden"),
            ("reason", "other|2\n" + "a" * 32 + "|active|pending|pending|pending||2"),
            ("updated_at", "2026-09-16T00:00:00Z"),
            ("updated_at", -1),
        ]
        for column, value in invalid:
            with self.subTest(column=column, value=value):
                with sqlite3.connect(self.db) as connection:
                    connection.execute("PRAGMA ignore_check_constraints=ON")
                    connection.execute(f"UPDATE requests SET {column}=? WHERE message_hash=?",
                                       (value, hashlib.sha256(MESSAGE.encode()).hexdigest()))
                before = self.db.read_bytes()
                self.run_tracker("list-open", owner=self.owner, success=False)
                self.assertEqual(self.db.read_bytes(), before)
                with sqlite3.connect(self.db) as connection:
                    connection.execute(
                        "UPDATE requests SET reference=?, estimate_state=?, draft_state=?, "
                        "teams_state=?, reason=?, updated_at=? WHERE message_hash=?",
                        (*original, hashlib.sha256(MESSAGE.encode()).hexdigest()))

    def test_manual_and_revision_identities_keep_original_and_stable_receipts(self):
        self.acquire()
        manual = "manual:12345678-1234-4234-8234-123456789abc"
        original_reference = self.run_tracker("claim", message=manual, owner=self.owner)[0].split("|")[1]
        shared_draft = "dummy-existing-draft-receipt"
        for stage in ("estimate", "draft", "teams"):
            self.run_tracker("begin", message=manual, owner=self.owner, stage=stage)
            self.run_tracker("confirm", message=manual, owner=self.owner, stage=stage,
                             receipt=shared_draft if stage == "draft" else "original-" + stage)
        self.run_tracker("complete", message=manual, owner=self.owner)
        with sqlite3.connect(self.db) as connection:
            original = connection.execute("SELECT * FROM requests WHERE reference=?", (original_reference,)).fetchone()
        identities = [manual]
        references = {original_reference}
        for revision in (1, 2):
            identity = f"revise:{original_reference}:{revision}"
            identities.append(identity)
            claimed = self.run_tracker("claim", message=identity, owner=self.owner)[0]
            self.assertEqual(self.run_tracker("claim", message=identity, owner=self.owner), [claimed])
            reference = claimed.split("|")[1]
            self.assertNotIn(reference, references)
            references.add(reference)
            for stage in ("estimate", "draft"):
                self.run_tracker("begin", message=identity, owner=self.owner, stage=stage)
                self.run_tracker("confirm", message=identity, owner=self.owner, stage=stage,
                                 receipt=shared_draft if stage == "draft" else "revision-" + str(revision))
            self.run_tracker("block", message=identity, owner=self.owner, reason="uncertain_outcome")
            self.run_tracker("retry", message=identity, owner=self.owner)
            retried = self.run_tracker("claim", message=identity, owner=self.owner)[0].split("|")
            self.assertEqual(retried[1:6], [reference, "active", "done", "done", "pending"])
        self.assertEqual(len(self.run_tracker("list-open", owner=self.owner)), 2)
        with sqlite3.connect(self.db) as connection:
            self.assertEqual(connection.execute("SELECT * FROM requests WHERE reference=?", (original_reference,)).fetchone(),
                             original)
            self.assertEqual(connection.execute("SELECT count(*) FROM requests").fetchone(), (3,))
            hashes = {row[0] for row in connection.execute("SELECT message_hash FROM requests")}
            draft_hashes = {row[0] for row in connection.execute("SELECT draft_receipt FROM requests")}
        self.assertEqual(hashes, {hashlib.sha256(identity.encode()).hexdigest() for identity in identities})
        self.assertEqual(draft_hashes, {hashlib.sha256(shared_draft.encode()).hexdigest()})
        for private in [*identities, shared_draft]:
            self.assertNotIn(private.encode(), self.db.read_bytes())
        self.assertTrue(self.run_tracker("claim", message=manual, owner=self.owner)[0].startswith("skip_completed|"))

    def test_artifact_empty_reads_require_known_request_source_and_lease(self):
        source = "stable-workbook-id/production"
        self.run_tracker("artifact-status", message=MESSAGE, source=source, success=False)
        self.operation("artifact-list", success=False)
        self.acquire()
        for action in ("artifact-begin", "artifact-status", "artifact-confirm", "artifact-list"):
            with self.subTest(action=action):
                self.operation(action, source=None if action == "artifact-list" else source,
                               receipt="dummy-receipt", success=False)
        self.operation("claim")
        before = self.db.read_bytes()
        self.assertEqual(self.operation("artifact-list"), [])
        self.assertEqual(self.operation("artifact-status", source=source), ["not_found"])
        self.assertEqual(self.db.read_bytes(), before)
        self.operation("artifact-status", success=False)
        self.operation("artifact-list", source=source, success=False)
        self.operation("status", source=source, success=False)
        self.operation("artifact-begin", source=source, receipt="intent", success=False)
        self.operation("begin", stage="estimate")
        self.operation("artifact-begin", source=source, success=False)
        self.operation("artifact-confirm", source=source, receipt="saved-id", success=False)
        self.operation("artifact-begin", source=source, receipt="intent")
        contender = "a" * 32 if self.owner != "a" * 32 else "b" * 32
        before = self.db.read_bytes()
        for action in ("artifact-begin", "artifact-status", "artifact-confirm", "artifact-list"):
            self.run_tracker(action, message=MESSAGE, owner=contender,
                             source=None if action == "artifact-list" else source,
                             receipt="intent", success=False)
        self.assertEqual(self.db.read_bytes(), before)
        self.expire_lock()
        before = self.db.read_bytes()
        for action in ("artifact-begin", "artifact-status", "artifact-confirm", "artifact-list"):
            self.operation(action, source=None if action == "artifact-list" else source,
                           receipt="intent", success=False)
        self.assertEqual(self.db.read_bytes(), before)
        self.acquire(contender)
        self.operation("artifact-status", source=source, success=False)
        self.assertEqual(len(self.run_tracker("artifact-list", message=MESSAGE, owner=contender)), 1)

    def test_artifact_interrupted_save_and_confirm_are_stable_without_recreation(self):
        self.acquire()
        self.start_estimate()
        source = "stable-workbook-id/production"
        intent = '{"name":"Customer Production","config":{"region":"eastus","vm":2}}'
        saved_id = "SavedEstimate:CaseSensitive/opaque+ID_123"
        started = self.operation("artifact-begin", source=source, receipt=intent)[0].split("|")
        self.assertEqual(started[:4], [hashlib.sha256(source.encode()).hexdigest(), "started",
                                       hashlib.sha256(intent.encode()).hexdigest(), ""])
        with sqlite3.connect(self.db) as connection:
            connection.execute("UPDATE estimate_artifacts SET updated_at=1")
        started[4] = "1"
        before = self.db.read_bytes()
        self.assertEqual(self.operation("artifact-begin", source=source, receipt=intent), ["|".join(started)])
        self.assertEqual(self.operation("artifact-status", source=source), ["|".join(started)])
        self.operation("artifact-begin", source=source, receipt=intent + " ", success=False)
        self.assertEqual(self.db.read_bytes(), before)
        self.assertTrue(self.operation("claim")[0].startswith("reconcile|"))
        self.operation("retry-stage", stage="estimate")
        self.operation("begin", stage="estimate")
        self.assertEqual(self.operation("artifact-begin", source=source, receipt=intent), ["|".join(started)])
        done = self.operation("artifact-confirm", source=source, receipt=saved_id)
        self.assertEqual(done[0].split("|")[:4], [started[0], "done", started[2],
                                                 hashlib.sha256(saved_id.encode()).hexdigest()])
        before = self.db.read_bytes()
        self.assertEqual(self.operation("artifact-confirm", source=source, receipt=saved_id), done)
        self.assertEqual(self.operation("artifact-begin", source=source, receipt=intent), done)
        self.operation("artifact-confirm", source=source, receipt=saved_id.lower(), success=False)
        self.operation("artifact-begin", source=source, receipt="different-intent", success=False)
        self.assertEqual(self.db.read_bytes(), before)
        with sqlite3.connect(self.db) as connection:
            self.assertEqual(connection.execute("SELECT count(*) FROM estimate_artifacts").fetchone(), (1,))

    def test_artifact_per_source_completion_gate_privacy_and_exact_listing(self):
        self.acquire()
        self.start_estimate()
        sources = ("workbook-production/\u00e9'\";--", "workbook-nonproduction")
        intents = ("Customer production\nnormalized-config-1", "Customer nonproduction\nnormalized-config-2")
        saved_ids = ("OpaqueProductionID:AbC", "OpaqueNonProductionID:XyZ")
        for source, intent in zip(sources, intents):
            self.operation("artifact-begin", source=source, receipt=intent)
        self.operation("artifact-confirm", source=sources[0], receipt=saved_ids[0])
        self.operation("confirm", stage="estimate", receipt="complete-manifest", success=False)
        with sqlite3.connect(self.db) as connection:
            connection.execute("UPDATE estimate_artifacts SET updated_at=1700000000")
            request = connection.execute("SELECT * FROM requests").fetchall()
        rows = self.operation("artifact-list")
        expected = sorted([
            "|".join([hashlib.sha256(source.encode()).hexdigest(), state,
                      hashlib.sha256(intent.encode()).hexdigest(),
                      hashlib.sha256(saved_id.encode()).hexdigest() if saved_id else "", "1700000000"])
            for source, intent, saved_id, state in zip(sources, intents, (saved_ids[0], ""), ("done", "started"))
        ])
        self.assertEqual(rows, expected)
        before = self.db.read_bytes()
        self.assertEqual(self.operation("artifact-list"), rows)
        self.assertEqual(self.db.read_bytes(), before)
        for row in rows:
            self.assertRegex(row, r"^[a-z0-9|]+$")
            self.assertEqual(len(row.split("|")), 5)
        for private in [*sources, *intents, saved_ids[0]]:
            self.assertNotIn(private.encode(), self.db.read_bytes())
            self.assertNotIn(private, "\n".join(rows))
        self.operation("artifact-confirm", source=sources[1], receipt=saved_ids[1])
        with sqlite3.connect(self.db) as connection:
            self.assertEqual(connection.execute("SELECT * FROM requests").fetchall(), request)
        self.operation("confirm", stage="estimate", receipt="complete-manifest")
        for action, receipt in (("artifact-begin", intents[0]), ("artifact-confirm", saved_ids[0])):
            self.operation(action, source=sources[0], receipt=receipt, success=False)
        for stage in ("draft", "teams"):
            self.operation("begin", stage=stage)
            self.operation("confirm", stage=stage, receipt=stage + "-receipt")
        self.operation("complete")
        before = self.db.read_bytes()
        self.operation("artifact-begin", source="new-source", receipt="new-intent", success=False)
        self.operation("artifact-confirm", source=sources[0], receipt=saved_ids[0], success=False)
        self.assertEqual(len(self.operation("artifact-list")), 2)
        self.assertEqual(self.db.read_bytes(), before)

    def test_artifact_saved_ids_are_unique_across_sources_and_revision_requests(self):
        self.acquire()
        self.start_estimate()
        self.operation("artifact-begin", source="prod", receipt="production-intent")
        self.operation("artifact-begin", source="nonprod", receipt="nonproduction-intent")
        self.operation("artifact-confirm", source="prod", receipt="Immutable-ID")
        self.operation("artifact-confirm", source="nonprod", receipt="Immutable-ID", success=False)
        original = self.operation("artifact-status", source="prod")
        reference = self.operation("status")[0].split("|")[1]
        revision = f"revise:{reference}:1"
        self.start_estimate(revision)
        self.run_tracker("artifact-begin", message=revision, owner=self.owner, source="prod",
                         receipt="revision-production-intent")
        self.run_tracker("artifact-confirm", message=revision, owner=self.owner, source="prod",
                         receipt="Immutable-ID", success=False)
        self.run_tracker("artifact-confirm", message=revision, owner=self.owner, source="prod",
                         receipt="Revision-Immutable-ID")
        self.assertEqual(self.operation("artifact-status", source="prod"), original)
        self.assertEqual(len(self.operation("artifact-list")), 2)
        self.assertEqual(len(self.run_tracker("artifact-list", message=revision, owner=self.owner)), 1)
        self.operation("block", reason="uncertain_outcome")
        self.operation("artifact-begin", source="prod", receipt="production-intent", success=False)
        self.operation("artifact-confirm", source="prod", receipt="Immutable-ID", success=False)
        self.assertEqual(self.operation("artifact-status", source="prod"), original)
        self.operation("retry")
        self.assertEqual(self.operation("artifact-confirm", source="prod", receipt="Immutable-ID"), original)

    def test_artifact_saved_identity_rejects_rotating_share_urls(self):
        self.acquire()
        self.start_estimate()
        self.operation("artifact-begin", source="prod", receipt="production-intent")
        self.operation("artifact-confirm", source="prod", receipt="ActualSavedEstimateID")
        checkpoint = self.operation("artifact-status", source="prod")
        before = self.db.read_bytes()
        urls = ["https://example.invalid/share/token-one", "https://example.invalid/share/token-two",
                "  HTTPS://example.invalid/share/token-three  ", "//example.invalid/share",
                "www.example.invalid/share", "https:example.invalid/share", "custom://share/link", "   "]
        for url in urls:
            with self.subTest(url=url):
                self.operation("artifact-confirm", source="prod", receipt=url, success=False)
        self.assertEqual(self.operation("artifact-confirm", source="prod", receipt="ActualSavedEstimateID"), checkpoint)
        self.assertEqual(self.db.read_bytes(), before)
        for url in urls[:-1]:
            self.assertNotIn(url.encode(), self.db.read_bytes())

    def test_artifact_malformed_persisted_fields_fail_without_partial_output(self):
        self.acquire()
        self.start_estimate()
        self.operation("artifact-begin", source="safe", receipt="safe-intent")
        self.operation("artifact-begin", source="other", receipt="other-intent")
        self.operation("artifact-confirm", source="other", receipt="other-saved-id")
        with sqlite3.connect(self.db) as connection:
            original = connection.execute(
                "SELECT rowid, source_hash, state, intent_hash, saved_id_hash, updated_at "
                "FROM estimate_artifacts WHERE source_hash=?", (hashlib.sha256(b"other").hexdigest(),)).fetchone()
        invalid = [
            ("source_hash", "a" * 64 + "\x00hidden"),
            ("source_hash", "private|source"),
            ("source_hash", b"\xff"),
            ("intent_hash", "b" * 64 + "\x00hidden"),
            ("state", "done\nprivate"),
            ("saved_id_hash", "https://example.invalid/private"),
            ("saved_id_hash", "b" * 64 + "\x00hidden"),
            ("updated_at", "private timestamp"),
            ("updated_at", -1),
        ]
        for column, value in invalid:
            with self.subTest(column=column, value=value):
                with sqlite3.connect(self.db) as connection:
                    connection.execute("PRAGMA ignore_check_constraints=ON")
                    connection.execute(f"UPDATE estimate_artifacts SET {column}=? WHERE rowid=?", (value, original[0]))
                before = self.db.read_bytes()
                self.operation("artifact-list", success=False)
                self.operation("artifact-status", source="safe", success=False)
                self.operation("confirm", stage="estimate", receipt="manifest", success=False)
                self.assertEqual(self.db.read_bytes(), before)
                with sqlite3.connect(self.db) as connection:
                    connection.execute(
                        "UPDATE estimate_artifacts SET source_hash=?, state=?, intent_hash=?, saved_id_hash=?, "
                        "updated_at=? WHERE rowid=?", (*original[1:], original[0]))

    @unittest.skipUnless(ADAPTER == "pwsh", "PowerShell adapter output guard")
    def test_powershell_artifact_result_shape_is_checked_for_every_action(self):
        self.acquire()
        self.start_estimate()
        self.operation("artifact-begin", source="prod", receipt="production-intent")
        self.operation("artifact-confirm", source="prod", receipt="SavedEstimateID")
        scripts = pathlib.Path(self.temp.name) / "malformed-output-adapter"
        shutil.copytree(SCRIPTS, scripts)
        sql_path = scripts / "tracker.sql"
        sql = sql_path.read_text(encoding="utf-8")
        selector = "SELECT source_hash, state, intent_hash, saved_id_hash, updated_at"
        self.assertEqual(sql.count(selector), 1)
        sql_path.write_text(sql.replace(selector,
            "SELECT 'invalid-source-hash', state, intent_hash, saved_id_hash, updated_at"),
            encoding="utf-8")
        before = self.db.read_bytes()
        for action, receipt in (
            ("artifact-begin", "production-intent"),
            ("artifact-status", None),
            ("artifact-confirm", "SavedEstimateID"),
            ("artifact-list", None),
        ):
            with self.subTest(action=action):
                self.operation(action, source=None if action == "artifact-list" else "prod",
                               receipt=receipt, scripts=scripts, success=False)
                self.assertEqual(self.db.read_bytes(), before)

    def test_artifact_v1_migration_preserves_history_and_legacy_schema(self):
        self.acquire()
        self.operation("claim")
        for stage in ("estimate", "draft", "teams"):
            self.operation("begin", stage=stage)
            self.operation("confirm", stage=stage, receipt="legacy-" + stage)
        self.operation("complete")
        self.run_tracker("claim", message="<legacy-blocked@example.invalid>", owner=self.owner)
        self.run_tracker("block", message="<legacy-blocked@example.invalid>", owner=self.owner, reason="other")
        self.run_tracker("release", owner=self.owner)
        self.make_legacy_tracker()
        with sqlite3.connect(self.db) as connection:
            requests = connection.execute("SELECT * FROM requests ORDER BY reference").fetchall()
            definitions = connection.execute(
                "SELECT name, sql FROM sqlite_master WHERE name IN ('requests', 'run_lock') ORDER BY name").fetchall()
            locks = connection.execute("SELECT * FROM run_lock").fetchall()
        self.owner = self.run_tracker("init")[0].split("|")[2]
        with sqlite3.connect(self.db) as connection:
            self.assertEqual(connection.execute("SELECT * FROM requests ORDER BY reference").fetchall(), requests)
            self.assertEqual(connection.execute("SELECT * FROM run_lock").fetchall(), locks)
            self.assertEqual(connection.execute(
                "SELECT name, sql FROM sqlite_master WHERE name IN ('requests', 'run_lock') ORDER BY name").fetchall(),
                definitions)
            self.assertEqual(connection.execute("SELECT count(*) FROM estimate_artifacts").fetchone(), (0,))
            self.assertEqual(connection.execute("PRAGMA user_version").fetchone(), (1,))
            self.assertEqual(connection.execute("PRAGMA application_id").fetchone(), (1095783252,))
        self.assertTrue(self.db.with_name("initialized-artifacts-v1").is_file())
        self.acquire()
        self.assertTrue(self.operation("claim")[0].startswith("skip_completed|"))
        self.assertEqual(self.operation("artifact-list"), [])
        self.assertEqual(self.operation("artifact-status", source="legacy-source"), ["not_found"])
        with sqlite3.connect(":memory:") as legacy:
            legacy.executescript(self.legacy_schema())
            self.assertEqual(legacy.execute(
                "SELECT name, sql FROM sqlite_master WHERE name IN ('requests', 'run_lock') ORDER BY name").fetchall(),
                definitions)

    def test_artifact_v1_upgrade_respects_live_and_expired_leases(self):
        self.acquire()
        self.operation("claim")
        self.make_legacy_tracker()
        before = self.db.read_bytes()
        self.run_tracker("init", success=False)
        contender = "a" * 32 if self.owner != "a" * 32 else "b" * 32
        self.run_tracker("init", owner=contender, success=False)
        self.assertEqual(self.db.read_bytes(), before)
        self.assertFalse(self.db.with_name("initialized-artifacts-v1").exists())
        with sqlite3.connect(self.db) as connection:
            requests = connection.execute("SELECT * FROM requests").fetchall()
            lock = connection.execute("SELECT * FROM run_lock").fetchall()
        self.run_tracker("init", owner=self.owner)
        with sqlite3.connect(self.db) as connection:
            self.assertEqual(connection.execute("SELECT * FROM requests").fetchall(), requests)
            self.assertEqual(connection.execute("SELECT * FROM run_lock").fetchall(), lock)
        self.make_legacy_tracker()
        self.expire_lock()
        self.run_tracker("init")
        with sqlite3.connect(self.db) as connection:
            self.assertEqual(connection.execute("SELECT * FROM requests").fetchall(), requests)
            self.assertEqual(connection.execute("SELECT expires_at FROM run_lock").fetchone(), (0,))

    def test_artifact_missing_extension_or_invalid_marker_fails_closed(self):
        self.acquire()
        self.start_estimate()
        self.operation("artifact-begin", source="prod", receipt="production-intent")
        marker = self.db.with_name("initialized-artifacts-v1")
        marker.write_bytes(b"invalid")
        self.run_tracker("init", success=False)
        self.operation("artifact-list", success=False)
        marker.write_bytes(b"")
        with sqlite3.connect(self.db) as connection:
            connection.execute("DROP TABLE estimate_artifacts")
        before = self.db.read_bytes()
        self.run_tracker("init", owner=self.owner, success=False)
        self.operation("artifact-list", success=False)
        self.operation("status", success=False)
        self.assertEqual(self.db.read_bytes(), before)
        with sqlite3.connect(self.db) as connection:
            self.assertEqual(connection.execute(
                "SELECT count(*) FROM sqlite_master WHERE name='estimate_artifacts'").fetchone(), (0,))

    def test_completed_history_cannot_be_reset_or_blocked(self):
        self.acquire()
        self.operation("claim")
        for stage in ("estimate", "draft", "teams"):
            self.operation("begin", stage=stage)
            self.operation("confirm", stage=stage, receipt="artifact-" + stage)
        self.operation("complete")
        self.operation("retry", success=False)
        self.operation("block", reason="other", success=False)
        self.operation("retry-stage", stage="estimate", success=False)
        self.assertTrue(self.operation("status")[0].startswith("skip_completed|"))

    def test_normal_commands_do_not_create_unknown_requests(self):
        self.acquire()
        self.operation("block", reason="other", success=False)
        self.operation("retry", success=False)
        self.operation("confirm", stage="estimate", receipt="dummy", success=False)
        with sqlite3.connect(self.db) as connection:
            self.assertEqual(connection.execute("SELECT count(*) FROM requests").fetchone()[0], 0)

    def test_invalid_marker_does_not_report_success(self):
        marker = self.db.with_name("initialized-v1")
        marker.write_bytes(b"invalid-marker")
        self.run_tracker("init", success=False)
        marker.unlink()
        marker.mkdir()
        self.run_tracker("init", success=False)

    def test_separate_workbook_links_checkpoint_as_complete_manifest(self):
        self.acquire()
        self.operation("claim")
        self.operation("begin", stage="estimate")
        pairs = [
            ["attachment-prod", "https://example.invalid/estimates/production"],
            ["attachment-nonprod", "https://example.invalid/estimates/non-production"],
        ]
        manifest = json.dumps(sorted(pairs), separators=(",", ":"), ensure_ascii=False)
        self.assertTrue(self.operation("status")[0].startswith("reconcile|"))
        self.operation("confirm", stage="estimate", receipt=manifest)
        row = self.operation("status")[0].split("|")
        self.assertEqual(row[3:6], ["done", "pending", "pending"])
        self.assertEqual(row[6], hashlib.sha256(manifest.encode()).hexdigest())
        self.assertNotEqual(row[6], hashlib.sha256(pairs[0][1].encode()).hexdigest())
        self.assertNotEqual(row[6], hashlib.sha256(pairs[1][1].encode()).hexdigest())
        self.assertNotIn(manifest.encode(), self.db.read_bytes())
        self.operation("complete", success=False)

    def test_symlink_is_rejected(self):
        alternate = self.db.with_name("elsewhere.sqlite3")
        self.db.rename(alternate)
        try:
            self.db.symlink_to(alternate)
        except OSError as error:
            if os.name == "nt" and error.winerror == 1314:
                self.skipTest("Windows symbolic-link creation requires additional privileges")
            raise
        self.run_tracker("init", success=False)
        self.run_tracker("status", message=MESSAGE, success=False)

    def test_packaged_resources_required(self):
        with tempfile.TemporaryDirectory(prefix="pricing-adapter-only-", dir=pathlib.Path.cwd()) as directory:
            filename = "tracker.ps1" if ADAPTER == "pwsh" else "tracker.sh"
            target = pathlib.Path(directory) / filename
            shutil.copyfile(SCRIPTS / filename, target)
            if ADAPTER == "pwsh":
                native = SCRIPTS / "NativeSqlite.cs"
                if native.exists():
                    shutil.copyfile(native, pathlib.Path(directory) / native.name)
                command = [POWERSHELL, "-NoProfile", "-NonInteractive", "-File", str(target),
                           "-Action", "init", "-Account", ACCOUNT, "-StateRoot", str(self.root)]
            else:
                command = ["sh", str(target), "--action", "init", "--account", ACCOUNT,
                           "--state-root", str(self.root)]
            result = subprocess.run(command, capture_output=True, text=True, timeout=40)
            self.assertNotEqual(result.returncode, 0)


if __name__ == "__main__":
    unittest.main()
