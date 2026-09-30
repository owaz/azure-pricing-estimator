# Estimated assumptions and sizing

Default to finishing an indicative estimate with explicitly documented assumptions, not interrupting for ordinary missing sizing. Apply this to full BOQs and quick price questions. The assumptions below are planning conventions disclosed by this skill, NOT customer facts, Azure minimums or promises of suitability. All regional GA defaults remain subject to availability-gate.md; only explicit request-scoped opt-in permits evidenced regional preview candidates.

## Estimate and disclose; do not ask for ordinary inputs

Use explicit source values first. Otherwise use workload evidence, then the planning defaults below. Record original gap, chosen value, rationale, cost impact and environment in Teams "Assumptions by environment". Put material customer-appropriate assumptions in the draft/Excel too; do not hide them internally. Leave follow-up items as nonblocking notes, not a request for input before work can proceed.

| Missing/ambiguous input | Estimating rule |
|---|---|
| VM OS | Always Ubuntu Linux, current supported GA image compatible with the workload, without a paid OS-support add-on. Generic Linux means Ubuntu unless a distribution is named. Preserve explicitly requested Windows/RHEL/SUSE/etc. |
| OS disk | One smallest Premium SSD tier fitting the verified OS image per VM. If the image's actual minimum is unknown, choose a conservative 128 GiB planning OS disk, verify the image fits and disclose it; this is not a universal Azure default. |
| No VM data-disk requirement mentioned | OS disk only. Do not add data disks for an inferred database/data workload. Explicit "no data disks" is respected. |
| Data disk explicitly requested but unsized | One 128 GiB Premium SSD v2 disk per requested VM, or the smallest supported capacity meeting known data/performance evidence if greater. Disclose provisional count/capacity and verify region/service support. Do not invent IOPS or MB/s evidence. |
| PaaS storage requested but unsized | Use the smallest supported storage allocation meeting known requirements; if none given, 128 GiB as a planning starting point rounded up to the verified service minimum. Never omit required PaaS storage by applying the VM OS-only rule. |
| Resource quantity | One per explicitly requested resource/workload when no count is given; apply a larger documented service minimum when required. Do not turn generic architecture adjectives into new services. |
| VM vCPU/RAM | Use workload evidence; if absent, a disclosed 2-vCPU/8-GiB planning starting point, rounded up to a suitable supported regional GA size. Specialized GPU/HPC requests retain explicit accelerator/type requirements and use the smallest compatible GA size, not a generic D-series substitute. |
| Database engine | Preserve known compatibility (for example SQL Server from explicit SQL Server features). If entirely unspecified, use PostgreSQL Flexible Server as a labelled planning choice, subject to regional GA; do not claim compatibility was confirmed. |
| SQL Server/Oracle/RHEL edition | Use supplied features and verified supported licensing/tier evidence. SQL Server defaults to Standard unless stated features require Enterprise; preserve explicit edition. Oracle/RHEL use the smallest documented suitable edition/plan; no guessed licence price. If no reliable retail price exists, report a price-evidence blocker rather than make one up. |
| Environment label | A single unlabelled scope becomes "Environment 1 (assumed)"; production status is not inferred from size. Keep explicit prod/staging/dev scopes separate. Contradictory mixed-environment allocation is not permission to arbitrarily merge/split resources; flag a genuine source-integrity blocker. |
| Customer/project name | Use a neutral label ("Customer", "Azure estimate") if absent; never invent a real identity or recipient. |
| Hours / duration | 730 h/month. Use stated duration as the usage horizon, not automatically a reservation term. If timing is unclear, assume listed quantities operate throughout the stated horizon and disclose that assumption. |
| HA / storage tier | Single zone/non-zone-redundant by default; explicit HA/99.99% affects that scope only. Hot for Blob unless specified. Do not relabel Blob/PaaS storage as managed disks. |
| Egress / shared free allowances | Use commercial-defaults.md. Unknown billing scope or available credit is a disclosed limitation, not a question. Preserve native calculator totals; disclose repeated/unverified allowances without adjusted budget totals or distorted usage. |
| Monitoring | Omit Azure Monitor/Log Analytics entirely unless explicitly requested. Only then may missing ingestion use the requested-monitoring constants; disclose. |
| Windows version / AHB | Current supported GA Windows version once Windows is explicitly requested. Apply supported AHB only with confirmed request-scoped eligibility and sufficient licence coverage; otherwise licence-included pricing where applicable. Honor explicit licence-included requests. Disclose the actual basis; never guess eligibility or a licence price. |
| VM family | Current GA D-series; E-series for explicitly database/in-memory VMs, preserving workload compatibility. Explicit specialized families/accelerators take precedence. |
| AKS system pool / App Service plan / SQL MI | Use the smallest qualifying regional GA service-required configuration; disclose pool/plan count and service-minimum rounding. |
| Explicit platform component without SKU/count | One appropriately supported baseline SKU satisfying supplied features, with documented service minimums. Disclose the assumption internally; do not add an unrequested component. |
| Requested reservation/Savings Plan without term | One year, monthly payment only, zero upfront. Disclose the full contractual term; do not purchase anything. PAYG remains default when no term product was explicitly requested by the invoking user. |

These defaults authorize estimated sizing, not silent architecture rewrites, fabricated product availability or licence eligibility. An explicitly incompatible requirement must not be overwritten by a default.

## Non-assumable safety/evidence blockers

Still stop the affected operation for unreadable/protected requirements, unknown recipient/source identity, contradictory unsplittable environments, no verified product/SKU regional support or retail price, unauthorized preview scope, failed retail selection, unresolved >2% price discrepancy, loss of lease, corruption or uncertain external writes. Do not fabricate completion. Preserve completed work and report the exact blocker privately.

Permissions, sensitivity labels, sharing approval, changes from the configured region, restricted-region access and unsupported PV2 alternatives retain their explicit approval gates. Ordinary sizing does not trigger `m_ask_user`; use it only for a genuine non-assumable decision or required send/share approval. Never infer the user's authorization to send customer email from "finish the task"; customer email stays a draft.

## Spec-to-SKU and units

- Normalize specs first; choose the smallest verified regional GA SKU meeting BOTH vCPU and RAM, plus required accelerator, architecture, OS and performance capabilities. Never round below supplied requirements; record family choice and upward rounding.
- GB = 10^9 bytes, GiB = 2^30 bytes, TB = 10^12 bytes, TiB = 2^40 bytes. Convert to actual calculator units; do not silently treat TB as 1024 GB. Preserve original -> normalized -> billed values.
- If a source unit convention is ambiguous, use and disclose a consistent decimal GB/TB or explicit binary GiB/TiB convention rather than ask.
- IOPS and MB/s are different measurements; do not convert without an I/O size. Distinguish capacity, provisioned performance and monthly transfer.
- An availability/SLA percentage is not billable hours. Explicit "99.99%" invokes scoped HA, not 730 multiplied by 99.99%.
- Ignore totals, subtotal, hidden and filtered-out rows; retain stable source/environment provenance. Visibility that cannot be established is an extraction problem, not a guessed inclusion decision.
