import hashlib
import json
import pathlib
import re
import shutil
import subprocess
import tempfile
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
RESOURCES = {
    "scripts/tracker.sh", "scripts/tracker.ps1", "scripts/NativeSqlite.cs",
    "scripts/schema.sql", "scripts/tracker.sql",
}


class DistributionTests(unittest.TestCase):
    def test_v2_structure_triggers_and_disclosure_contract(self):
        skill = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        references = {
            "commercial-defaults.md", "completeness-checklist.md",
            "modernization-map.md", "clarification-matrix.md",
            "availability-gate.md", "output-templates.md",
            "tracker-operations.md",
        }
        self.assertEqual({path.name for path in (ROOT / "reference").glob("*.md")}, references)
        for name in references:
            self.assertIn(name, skill)
        frontmatter = skill.split("---", 2)[1]
        for trigger in (
            "price this", "Azure estimate", "BOQ", "pricing calculator",
            "cost estimate for <customer>", "revise APE:",
            "Run /azure-pricing-estimator for all eligible requests",
        ):
            self.assertIn(trigger, frontmatter)
        templates = (ROOT / "reference/output-templates.md").read_text(encoding="utf-8")
        teams = templates.split("```text\n", 1)[1].split("```", 1)[0]
        customer = templates.split("```html\n", 1)[1].split("```", 1)[0]
        disclaimer = (
            "Azure Hybrid Benefit has been applied to the identified eligible workloads based on "
            "confirmed licence eligibility and coverage; eligible licences with active Software "
            "Assurance (or equivalent subscription licences) are required."
        )
        defaults = (ROOT / "reference/commercial-defaults.md").read_text(encoding="utf-8")
        for text in (skill, defaults, templates):
            self.assertIn(disclaimer, text)
        for text in (skill, defaults, teams, customer):
            for required in ("USD", "retail", "730", "Premium SSD",
                             "Support plan", "VAT"):
                self.assertIn(required.lower(), text.lower())
            self.assertIn("region", text.lower())
        for text in (teams, customer):
            self.assertIn("applicable exact licensing text", text)
            self.assertNotIn("AHB applied", text)
        for text in (teams, customer):
            for forbidden in ("AED", "Dev/Test", "DevTest", "without AHB", "Savings Plan", "reservation"):
                self.assertNotIn(forbidden.lower(), text.lower())
            for required in ("Monthly", "Annual", "Excel BOQ", "Prices as of"):
                self.assertIn(required.lower(), text.lower())
        self.assertIn("Upfront USD", teams)
        self.assertIn("Not priced — consider", teams)
        self.assertIn("Superseded", teams)
        self.assertIn("<table>", customer)
        self.assertNotIn("|", customer)
        self.assertIn(
            "Please let us know if any clarity is required, and we'd be happy to set up a "
            "follow-up call to walk through the estimate.", customer,
        )
        self.assertIn("not a binding quote", customer)
        for forbidden in ("Not priced", "Superseded", "Not added"):
            self.assertNotIn(forbidden.lower(), customer.lower())
        self.assertIn("material storage compatibility constraints", customer)

    def test_v2_workflow_and_runtime_evidence_contract(self):
        skill = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        operations = (ROOT / "reference/tracker-operations.md").read_text(encoding="utf-8")
        for required in (
            "48 hours", "receivedDateTime", "full_boq", "quick_price_question",
            "not_a_request", "manual:<uuid4>", "revise APE:", "Environment column",
            "filtered-out", "actual To/CC", "immutable saved-estimate ID", "uncertain_outcome",
            "BEFORE EACH WORKBOOK BUILD", "17:00", "list-open", "saveAsDraft:true",
        ):
            self.assertIn(required, skill)
        for required in (
            "revise:<ref>:<n>", "SAME", "same draft ID", "O_EXCL", "CreateNew",
            "digest:<configured-timezone YYYY-MM-DD>", "started", "done", "empty",
            "without schema changes", "uncertain_outcome",
        ):
            self.assertIn(required.lower(), operations.lower())
        modernization = (ROOT / "reference/modernization-map.md").read_text(encoding="utf-8")
        rows = [line for line in modernization.splitlines() if line.startswith("| ") and line.endswith("| Y | Y |")]
        self.assertGreaterEqual(len(rows), 26)
        for row in rows:
            self.assertIn("https://learn.microsoft.com/", row)
        self.assertIn("configured region", modernization)
        self.assertNotIn("UAE North", modernization)
        self.assertIn("Authoring verification", modernization)

    def test_clean_calculator_identity_ignores_rotating_share_urls(self):
        skill = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        operations = (ROOT / "reference/tracker-operations.md").read_text(encoding="utf-8")
        templates = (ROOT / "reference/output-templates.md").read_text(encoding="utf-8")
        for action in ("artifact-begin", "artifact-status", "artifact-confirm", "artifact-list"):
            self.assertIn(action, operations)
        for text in (skill, operations):
            self.assertIn("immutable saved-estimate ID", text)
            self.assertIn("service labels", text)
        self.assertIn("share URL can change every time", operations)
        self.assertIn("saved-estimates-v1:", operations)
        self.assertIn("source_hash|state|intent_hash|saved_id_hash|updated_at", operations)
        self.assertIn("NEVER a share URL", operations)
        self.assertIn("Legacy confirmed URL receipts remain byte-for-byte unchanged", operations)
        self.assertIn("No APE/WB", templates)
        self.assertIn("Copy generated links unchanged", templates)
        self.assertNotIn("DESCRIPTION ONLY", skill + operations)
        self.assertNotIn("in estimate DESCRIPTION", operations)
        self.assertIn("No APE/WB/internal markers in names, service labels, descriptions", skill)

    def test_assumptions_os_disks_monitor_payment_and_ahb_policy(self):
        skill = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        defaults = (ROOT / "reference/commercial-defaults.md").read_text(encoding="utf-8")
        matrix = (ROOT / "reference/clarification-matrix.md").read_text(encoding="utf-8")
        checklist = (ROOT / "reference/completeness-checklist.md").read_text(encoding="utf-8")
        templates = (ROOT / "reference/output-templates.md").read_text(encoding="utf-8")
        for text in (skill, defaults, matrix, checklist, templates):
            self.assertIn("Ubuntu Linux", text)
            self.assertIn("OS disk", text)
            self.assertIn("explicitly requested", text)
        always_add = checklist.split("## A. ALWAYS ADD", 1)[1].split("## Explicit monitoring only", 1)[0]
        self.assertNotIn("Azure Monitor", always_add)
        self.assertNotIn("Log Analytics", always_add)
        self.assertIn("no monitoring line, volume, placeholder or charge", checklist)
        self.assertIn("No VM data-disk requirement mentioned", matrix)
        self.assertIn("One per explicitly requested resource/workload", matrix)
        self.assertIn("not interrupting for ordinary missing sizing", matrix)
        self.assertIn("no response required before completion", templates)
        self.assertIn("EVERY gap, assumed value and rationale", templates)
        self.assertIn("monthly payments ONLY", skill)
        self.assertIn("monthly payments, never upfront", defaults)
        self.assertIn("Monthly payments do not remove the contractual term", defaults)
        self.assertIn("upfront MUST be zero", defaults)
        self.assertIn("Honor explicit licence-included requests", skill)
        self.assertIn("confirmed eligibility", defaults)
        self.assertIn("licence-included pricing where applicable", defaults)
        self.assertIn("Unknown, absent, stale or contradicted eligibility", defaults)
        self.assertIn("non-assumable", matrix)
        for obsolete in ("MUST-ASK condition", "Unknown VM OS", "No blanket sizing waiver",
                         "DEFAULT_LOG_INGESTION_GB_PER_VM_PER_MONTH",
                         "DEFAULT_LOG_INGESTION_GB_PER_ENVIRONMENT_WITHOUT_VM_COUNT"):
            self.assertNotIn(obsolete, skill + defaults + matrix + checklist)

    def test_portable_onboarding_and_private_profile(self):
        skill = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        operations = (ROOT / "reference/tracker-operations.md").read_text(encoding="utf-8")
        self.assertIn("Owais Ahmed - Solution Engineering UAE", skill)
        for field in ("profileVersion", "regionName", "armRegionName", "timeZone", "exportRoot"):
            self.assertIn(field, operations)
        for required in ("profile.json", "UAE North", "Asia/Dubai", "one decision at a time",
                         "0700", "0600", "atomically", "reconcile", "blanket preview opt-in"):
            self.assertIn(required, operations)
        for path in [ROOT / "SKILL.md", *sorted((ROOT / "reference").glob("*.md"))]:
            text = path.read_text(encoding="utf-8")
            self.assertNotRegex(text, r"/(?:Users|home)/[A-Za-z0-9_.-]+")
            self.assertNotIn("armRegionName eq 'uaenorth'", text)
            self.assertNotIn("17:00 Asia/Dubai", text)
            self.assertNotIn("digest:<Asia/Dubai", text)
        self.assertFalse(list(ROOT.rglob("profile.json")))

    def test_preview_gate_and_material_storage_disclosure(self):
        gate = (ROOT / "reference/availability-gate.md").read_text(encoding="utf-8")
        defaults = (ROOT / "reference/commercial-defaults.md").read_text(encoding="utf-8")
        templates = (ROOT / "reference/output-templates.md").read_text(encoding="utf-8")
        for required in ("GA is the default", "explicit opt-in", "regional support",
                         "Preview - not authorized", "Unknown support", "Top-three price checks"):
            self.assertIn(required, gate)
        for text in (gate, defaults):
            for limitation in ("zonal-placement", "availability-set", "host-caching",
                               "Backup", "Site Recovery"):
                self.assertIn(limitation, text)
        for text in (gate, defaults, templates):
            self.assertIn("material", text.lower())
            self.assertNotIn("Do NOT disclose", text)
            self.assertNotIn("prohibited operational implications", text)
        self.assertIn("never suppress", templates.lower())

    def test_consolidation_and_reply_all_contract(self):
        skill = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        operations = (ROOT / "reference/tracker-operations.md").read_text(encoding="utf-8")
        templates = (ROOT / "reference/output-templates.md").read_text(encoding="utf-8")
        for text in (skill, operations, templates):
            for required in ("replyAll:true", "saveAsDraft:true", "isHtml:true", "Summary"):
                self.assertIn(required, text)
        for required in ("31-character", "case-insensitive uniqueness", "formulas",
                         "dependencies", "styles", "hyperlinks", "native calculator totals",
                         "reopen", "ONE consolidated workbook", "original exports"):
            self.assertIn(required.lower(), templates.lower())
        for text in (operations, templates):
            self.assertNotIn("one actual attachment or usable OneDrive link per environment", text)
            self.assertNotIn("one actual export per environment", text)
            self.assertNotIn("only when the user explicitly requested a reply", text)

    def test_external_actions_require_exact_preview_and_confirmation(self):
        skill = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        for required in ("calculator save/share", "cloud upload", "file permission change",
                         "Teams send", "exact content/configuration", "explicit confirmation",
                         "private data", "unattended", "never send customer email"):
            self.assertIn(required.lower(), skill.lower())
        self.assertIn("profile or automation schedule is never send/share consent", skill)

    def test_package_excludes_runtime_files(self):
        expected = {"SKILL.md", "payload/tracker-payload.md",
                    "tests/test_distribution.py", "tests/test_tracker.py"} | RESOURCES
        expected |= {"reference/" + name for name in (
            "availability-gate.md", "clarification-matrix.md", "commercial-defaults.md",
            "completeness-checklist.md", "modernization-map.md", "output-templates.md",
            "tracker-operations.md",
        )}
        actual = {path.relative_to(ROOT).as_posix() for path in ROOT.rglob("*") if path.is_file()}
        self.assertEqual(actual, expected)
        self.assertFalse(any(path.is_symlink() for path in ROOT.rglob("*")))

    def test_text_only_import_preserves_helpers_and_shared_state(self):
        skill = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        self.assertLessEqual(len(skill.splitlines()), 250)
        self.assertIn("payload/tracker-payload.md", skill)
        payload = (ROOT / "payload/tracker-payload.md").read_text(encoding="utf-8")
        blocks = re.findall(
            r"Resource: (scripts/[A-Za-z0-9.]+)\nSHA-256: ([a-f0-9]{64})\n````text\n(.*?)````\n",
            payload, re.DOTALL,
        )
        self.assertEqual({relative for relative, _, _ in blocks}, RESOURCES)
        self.assertEqual(len(blocks), len(RESOURCES))
        operations = (ROOT / "reference/tracker-operations.md").read_text(encoding="utf-8")
        manifest = dict(re.findall(r"\| (scripts/[A-Za-z0-9.]+) \| ([a-f0-9]{64}) \|", operations))
        self.assertEqual(manifest, {relative: digest for relative, digest, _ in blocks})
        with tempfile.TemporaryDirectory(prefix="pricing-import-test-", dir=pathlib.Path.cwd()) as directory:
            imported = pathlib.Path(directory) / "imported-skill"
            for relative, expected_hash, text in blocks:
                data = text.encode("utf-8")
                self.assertEqual(hashlib.sha256(data).hexdigest(), expected_hash)
                self.assertEqual(data, (ROOT / relative).read_bytes())
                destination = imported / relative
                destination.parent.mkdir(parents=True, exist_ok=True)
                destination.write_bytes(data)
            state = pathlib.Path(directory) / "private-state"
            account = "dummy-import@example.invalid"
            message = "<dummy-import-message@example.invalid>"
            source = "attachment-id#Production \u00e9"
            intent = json.dumps(
                ["estimate-intent-v1", "Customer Production", source,
                 [["virtual-machines", [["os", "Ubuntu Linux"], ["quantity", "1"]]]]],
                separators=(",", ":"), ensure_ascii=False,
            )
            saved_id = "SavedEstimate:CaseSensitive/opaque+ID_123"
            powershell = shutil.which("pwsh") or shutil.which("powershell.exe")
            adapters = []
            if shutil.which("sh") and shutil.which("sqlite3") and shutil.which("shasum"):
                adapters.append((["sh", str(imported / "scripts/tracker.sh")],
                                 {"account": "--account", "root": "--state-root",
                                  "action": "--action", "owner": "--owner", "message": "--message",
                                  "source": "--source", "receipt": "--receipt", "stage": "--stage"}))
            if powershell:
                adapters.append(([powershell, "-NoProfile", "-NonInteractive", "-File",
                                  str(imported / "scripts/tracker.ps1")],
                                 {"account": "-Account", "root": "-StateRoot",
                                  "action": "-Action", "owner": "-Owner", "message": "-Message",
                                  "source": "-Source", "receipt": "-Receipt", "stage": "-Stage"}))
            self.assertTrue(adapters, "A supported validation adapter is required")
            reference = None
            checkpoint = None
            for prefix, names in adapters:
                base = prefix + [names["account"], account, names["root"], str(state)]

                def run(action, *extra):
                    result = subprocess.run(base + [names["action"], action, *extra],
                                            capture_output=True, text=True, timeout=40)
                    self.assertEqual(result.returncode, 0, result.stderr)
                    return result.stdout.strip()

                owner = run("init").split("|")[2]
                self.assertTrue(run("acquire", names["owner"], owner).startswith("acquired|"))
                current = run("claim", names["owner"], owner, names["message"], message).split("|")[1]
                if reference is not None:
                    self.assertEqual(current, reference, "Adapters must reuse the same account state")
                reference = current
                opened = run("list-open", names["owner"], owner).split("|")
                self.assertEqual(opened[:6], [reference, "active",
                    "pending" if checkpoint is None else "started", "pending", "pending", ""])
                self.assertEqual(len(opened), 7)
                self.assertRegex(opened[6], r"^[0-9]+$")
                request = [names["owner"], owner, names["message"], message]
                artifact = request + [names["source"], source]
                if checkpoint is None:
                    run("begin", *request, names["stage"], "estimate")
                    run("artifact-begin", *artifact, names["receipt"], intent)
                    checkpoint = run("artifact-confirm", *artifact, names["receipt"], saved_id)
                    self.assertEqual(checkpoint.split("|")[:4], [
                        hashlib.sha256(source.encode()).hexdigest(), "done",
                        hashlib.sha256(intent.encode()).hexdigest(),
                        hashlib.sha256(saved_id.encode()).hexdigest(),
                    ])
                self.assertEqual(run("artifact-status", *artifact), checkpoint)
                self.assertEqual(run("artifact-begin", *artifact, names["receipt"], intent), checkpoint)
                self.assertEqual(run("artifact-confirm", *artifact, names["receipt"], saved_id), checkpoint)
                self.assertEqual(run("artifact-list", *request), checkpoint)
                run("release", names["owner"], owner)
            self.assertFalse(list(imported.rglob("*.sqlite3")), "State must stay outside the skill")


if __name__ == "__main__":
    unittest.main()
