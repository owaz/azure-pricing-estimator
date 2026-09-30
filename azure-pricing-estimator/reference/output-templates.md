# Output templates

Use actual verified values and native calculator totals only. One row per workbook/environment; never aggregate production/non-production quantities. Preserve exact source provenance. Keep original Excel exports for each estimate, but deliver ONE consolidated workbook per request. No APE/WB/internal identifiers in calculator names/items/descriptions, exported calculator labels, links or hyperlink display text. Internal APE text in Teams and the Outlook footer remains separate from links.

## Consolidated workbook and Summary

Load `m_get_skill("xlsx")` before spreadsheet work. Consolidation is presentation of original calculator exports, never local repricing.

1. Save original exports unchanged under the approved export root and request folder. Inventory every source workbook and sheet, including formulas, styles, links, names, merged cells, hidden sheets and dependencies. Do not confuse source-requirements visibility filtering with export fidelity: preserve all calculator-export sheets, including supporting sheets.
2. Create ONE `.xlsx` with `Summary` first, then distinct source/environment tabs. Use source-defined Production/Staging/Development names where supplied; never infer production from size. For multiple sources with the same environment or multiple sheets per export, use deterministic readable source qualifiers. Respect Excel's 31-character limit, forbidden characters and case-insensitive uniqueness, including collisions with Summary. Keep an exact source-to-tab map.
3. Copy the real exported sheets, retaining values, formulas, number formats, styles, row/column layout, hyperlinks, merged ranges, relevant workbook names and calculation dependencies. Renaming sheets must update formula/name references correctly; do not use unsafe text substitution or silently create external links to local source paths. If the available workbook tooling cannot preserve a required feature, block rather than flatten to values or deliver several workbooks.
4. Build a formatted Summary with a title, build date, currency and one row per source/environment: source label, destination tabs, saved estimate name, actual region, monthly USD, upfront USD (zero), annualized USD (monthly x 12), requested usage-horizon total when applicable, and the verified calculator link. Use clear headers, sensible widths, wrapped text, frozen headings, consistent currency formats and readable print settings. Summary values must trace to verified native export totals. Do not combine resource quantities, add adjusted budget totals, an Egress Adjustment sheet or an Excel release-status section.
5. Reopen the finished file and compare every mapped export sheet's values/formulas, styles and hyperlinks with its original, accounting only for required sheet-name/reference remapping. Verify formula/name references, dependencies, Summary totals, all hyperlinks and source coverage; use the spreadsheet skill's supported recalculation/rendering checks. Do not claim cached totals prove formula fidelity. An unresolved difference or unsupported feature blocks delivery.
6. Keep original exports locally as permitted by rights, and attach/link ONLY the consolidated workbook in the Outlook draft and one authorized Teams message. Include ALL per-estimate calculator links. Neither a local path nor a calculator URL is an Excel attachment. Do not claim attachment/link success before verifying the actual saved artifact and recipient access.

## Licensing and release-status text

Use only the applicable licensing text in both outputs, identifying mixed workloads separately:

- AHB applied: "Azure Hybrid Benefit has been applied to the identified eligible workloads based on confirmed licence eligibility and coverage; eligible licences with active Software Assurance (or equivalent subscription licences) are required."
- AHB not applied to eligible workloads: "Azure Hybrid Benefit has not been applied to these workloads; licence-included pricing is used where applicable."
- No eligible lines: "No lines in this scope are AHB-eligible; no AHB discount was taken."

Never render an AHB-applied disclaimer for unconfirmed/ineligible workloads or leave template alternatives in finished output. Disclose actual GA/preview status and material preview deployment/support/capacity restrictions in user review notes and customer-facing assumptions, not a separate Excel status section. Material storage constraints must not be suppressed. Unknown availability is an unresolved blocker, not a preview label.

## Teams self-chat: completed full BOQ

```text
Azure pricing estimates ready — APE:<reference>
Source: <subject or manual identity> | <received/invocation date/time in configured timezone> | from <sender or invoking user>
Draft: <same-thread Reply All / new ad hoc draft> | To: <actual recipients> | CC: <actual recipients or none> | "<actual subject>" | saved unsent, review before sending | <consolidated Excel BOQ attached / linked>

| Environment | Source (workbook#sheet) | Estimate name | Monthly USD | Upfront USD | Annual USD | Link |
|---|---|---|---:|---:|---:|---|
| <environment> | <workbook#sheet or #Environment-column-value> | <saved estimate name> | <monthly> | <upfront> | <annualised> | <verified share link> |

Excel BOQ: <ONE actual consolidated workbook attachment or authorized usable OneDrive link>
Source-to-tab mapping: <each source/environment and all destination tabs; Summary first>
Commercial basis: PAYG | USD | Retail pricing | <actual licensing basis per workload> | 730 h/month | <actual region per environment> | Zero upfront payment | <single-zone / zone-redundant per env> | Prices as of <build date>
Licensing: <applicable exact licensing text from above, scoped to the workloads>
OS/storage basis: <supplied OS, or Ubuntu Linux assumed>; Premium SSD OS disks only when no data disks were requested. <If requested: Premium SSD v2 data disks or specifically approved unsupported-service alternative>
Scope by environment: ...
Assumptions by environment: <EVERY gap, assumed value and rationale: OS, OS-only/data-disk scope, counts, engine/edition, spec-to-SKU rounding, units, hours/horizon, HA, egress, repeated/unverified calculator allowances, AKS system pool/LB/tier, and ingestion ONLY if monitoring was explicitly requested>
Release status and limitations: <actual GA/authorized preview status, evidence, opt-in scope and material deployment/support/capacity caveats; relevant storage compatibility limitations>
Modernisation / substitutions: <legacy> → <current>, <environment and reason>
Not priced — consider (internal only): Consider adding: <item> — <reason>
Regional / calculator limitations: <affected environment/item, actual region and limitation or None>
Nonblocking follow-up notes: <ordinary missing inputs already estimated and disclosed; no response required before completion>
Attachment limitations: <actual limitations or None>
Not added — confirm if you want the end customer addressed directly: <external addresses found in an internal forward, or None>
Superseded: <earlier APE reference and estimate/draft labelled "superseded by APE:<new reference>", or None>
Exclusions: Support plan not included; excludes VAT and negotiated discounts.
Annual basis: monthly x 12. <Requested N-month usage horizon: monthly x N, if supplied>
This is an indicative estimate based on public retail pricing and is not a binding quote. Prices are subject to change and exclude VAT and any negotiated discounts.
```

Keep "Not priced — consider" even when "None". These items and internal recipient/supersession details are user-only. Replace defaults with actual hours, HA, approved region or explicitly requested purchase model. Requested terms MUST say "monthly payment; zero upfront" and disclose the contractual term, not claim no commitment. Add no unrequested term/comparison or currency-conversion lines. No automatic Monitor assumption line when it was not requested.

Copy generated links unchanged with plain "View estimate"/"Download Excel BOQ" link text. Regenerating a URL does not create a new estimate; use saved-ID tracking and avoid repeatedly invoking Share. Ordinary assumptions must reach the authorized Teams self-chat under normal send safeguards, not be hidden only in this conversation.

## Outlook customer draft: draft only

Subject: preserve the actual source thread subject for email-sourced Reply All drafts. For ad hoc drafts use `Azure pricing estimate - <customer/project>`.

Write in the language of the request; default English. Preserve the applicable English licensing text, indicative-quote disclaimer and closing (a translation may precede each if needed). Use a real HTML table, not pipe-delimited lines. Email sources MUST use `workiq_reply_to_email` with `replyAll:true`, `saveAsDraft:true`, `isHtml:true` on the exact source email, preserving its real To/CC and quoted thread. Only ad hoc requests use `workiq_create_draft` with `isHtml:true`. HTML-escape all source-derived names, subjects, filenames and text; permit only verified HTTPS links from the actual authorized service, never source-supplied scripts or arbitrary schemes.

```html
<p>Hello &lt;recipient name&gt;,</p>
<p>Thank you for sharing the requirements. Please find the Azure pricing estimates below.</p>
<table>
  <thead><tr><th>Environment</th><th>Source workbook</th><th>Estimate</th><th>Monthly (USD)</th><th>Annual (USD)</th><th>Link</th></tr></thead>
  <tbody>
    <tr><td>&lt;environment&gt;</td><td>&lt;workbook#sheet or #column value&gt;</td><td>&lt;saved name&gt;</td><td>&lt;monthly&gt;</td><td>&lt;annualised&gt;</td><td>&lt;verified estimate hyperlink&gt;</td></tr>
  </tbody>
</table>
<p>Excel BOQ attached: &lt;ONE consolidated workbook with Summary and all source/environment tabs&gt;.</p>
<p>Commercial basis: pay-as-you-go, USD, public retail pricing, &lt;actual region per environment&gt;, 730 h/month, zero upfront payment, prices as of &lt;build date&gt;. Licensing: &lt;applicable exact licensing text, scoped to the workloads&gt;. OS/storage basis: &lt;supplied OS or Ubuntu Linux assumed&gt;; Premium SSD OS disks only where no data disks were requested, with Premium SSD v2 only for requested eligible data disks. HA basis: &lt;single-zone / zone-redundant per environment&gt;.</p>
<p><strong>Key assumptions by environment:</strong> &lt;customer-appropriate assumed quantities/sizing, engine/edition, units, hours/horizon, egress, repeated/unverified calculator allowances, AKS system pool/LB/tier, OS disk and modernization assumptions; monitoring only if explicitly requested&gt;.</p>
<p><strong>Release status and material limitations:</strong> &lt;actual release status, authorized preview scope and deployment/support/capacity caveats where applicable; material storage compatibility constraints&gt;.</p>
<p><strong>Open questions / exclusions:</strong> Support plan not included; excludes VAT. &lt;Other customer-appropriate nonblocking questions/exclusions only&gt;.</p>
<p>This is an indicative estimate based on public retail pricing and is not a binding quote. Prices are subject to change and exclude VAT and any negotiated discounts.</p>
<p>Please let us know if any clarity is required, and we'd be happy to set up a follow-up call to walk through the estimate.</p>
<p>&lt;user's name&gt;</p>
<p>Reference: APE:&lt;reference&gt;</p>
```

Repeat table rows and environment assumptions. With an authorized OneDrive consolidated workbook replace "Excel BOQ attached" truthfully with "Excel BOQ linked" and its real hyperlink. Neither a local path nor a calculator share link is an Excel attachment. Upfront USD MUST be zero; do not disguise an upfront payment as monthly amortisation. If a term is explicitly requested, use monthly-payment wording and its full contractual term. For a shorter usage horizon add its total without implying the term can be cancelled early.

Customer draft boundaries:

- No unrequested B-list recommendations or internal architecture commentary in the draft. Requested priced components may be named when explaining material assumptions or limitations; never suppress relevant storage compatibility caveats. Keep exact provenance mapping in Teams and the BOQ.
- No internal-only recipient discoveries, supersession commentary about another draft, unrelated private data, hidden reasoning, or operational journal identities. Keep the APE footer.
- Every commercial assumption remains visible: purchase model/monthly payment with zero upfront, USD retail, actual licensing basis and applicable disclaimer, supplied/default Ubuntu OS, OS-only/no-data default, hours, no support/VAT, actual approved region, scoped HA and build date. Non-production uses the same retail basis. Do not claim an AHB discount for unsupported or unconfirmed workloads.
- Only the specified closing sentence; no additional request for approval, licence confirmation, purchase, meeting booking or another call to action. Open questions are neutral descriptions, not extra closing requests.
- An approved storage exception identifies the unsupported service/calculator and chosen alternative. Include material PV2 operational implications when applicable, rather than implying an incompatible design is supported.

## Blocked, uncertain and quick-question messages

Never use the ready template if any required environment, top-three check, link, export or draft is incomplete. State "Azure pricing request blocked — APE:<reference>", actual saved artifacts (if any), affected environment and exact blocker. Do not show zero for missing totals or create a customer draft pretending the collection is ready. Individual blocker notices are one-time, guarded as in tracker-operations.md; later unresolved requests appear only in the daily digest.

A `quick_price_question` gets only a concise authorized Teams self-chat answer: source, product/SKU and regional support/release-status evidence, verified retail USD rate/units, monthly calculation, date and all estimated assumptions. GA default and explicit preview opt-in still apply. Apply default Ubuntu/OS-only scope where relevant, explicit-only Monitor, eligibility-aware AHB and monthly-only/zero-upfront terms. Include applicable exact licensing text and support/VAT exclusions; label genuinely irrelevant fields not applicable. No saved estimate, Excel BOQ or customer draft. Estimate ordinary missing inputs under the matrix rather than asking; never invent prices. Use the guarded `quick:<internetMessageId>` operation (stable manual identity for ad hoc questions). Operational-only notices carry no pricing boilerplate.

For uncertain triage, self-chat only: "Pricing triage needs your decision: <source identity> — full BOQ, quick price question, or not a request?" Do not build until the user decides. Preview/confirmation and sensitivity rules still apply.

The daily digest is references and reason codes only, plus its operational date marker:

```text
Open Azure pricing requests — APE-DIGEST:<YYYY-MM-DD>
APE:<reference> — <reason code, or unfinished>
```

No subjects, names, addresses, requirements, links or individual re-notifications in a digest. When no requests are open, record that day's empty digest outcome and finish quietly.
