# Commercial defaults

Commercial policy for azure-pricing-estimator v2.3. These are estimate assumptions, not evidence of customer entitlement or Azure availability.

## Defaults and run-local overrides

| Item | Rule |
|---|---|
| Pricing model | Pay-as-you-go (PAYG). Reservation or Savings Plan ONLY when the user's invocation explicitly asks; apply only to eligible requested scope. Never add unprompted comparisons. A source document mentioning a term does not change the default; record that distinction in Teams rather than interrupting for clarification. |
| Payment cadence | No upfront payment. Any explicitly requested reservation/Savings Plan MUST use monthly payments, never upfront, even if the source requests upfront payment. A monthly payment schedule still carries the chosen contractual term; never call it commitment-free or cancel-anytime. This skill estimates only and never purchases a plan. |
| Currency | USD only, even if the prompt or source requests another currency. |
| Price list | Public retail. After calculator login VERIFY Licensing Program/price-list settings are retail, with no EA/CSP/MCA negotiated billing-account price sheet. PAYG is a purchase model, not proof of retail prices. If retail cannot be set and verified, stop and tell the user. Recheck each estimate. |
| Azure Hybrid Benefit | Apply only to supported workloads with confirmed eligibility and sufficient eligible licence coverage for this request. Record the confirmation's source, scope and date in authorized review notes, not the hash-only tracker or a reusable eligibility flag. Unknown, absent, stale or contradicted eligibility means licence-included pricing where applicable, with disclosure rather than a blocking sizing question. Honor an explicit licence-included requirement. Preserve the requested OS and use its actual licensing control, never a Linux VM to imitate Windows AHB. Unsupported services receive no invented benefit. An estimate is not a legal entitlement determination or deployment authorization. |
| Missing VM OS | Ubuntu Linux, current supported GA image compatible with the workload; no paid Ubuntu support add-on by default. Generic "Linux" also uses Ubuntu unless a distribution is specified. Preserve explicitly requested Windows or another OS. |
| Missing VM data disks | OS disk only when no data-disk requirement is mentioned. One fitting Premium SSD OS disk per VM; do not infer data disks, snapshots or extra capacity from the workload type. Explicitly requested but unsized data disks use disclosed planning sizing from clarification-matrix.md. PaaS database storage is not a VM data disk and must still be estimated. |
| Monitoring | Do NOT add Azure Monitor / Log Analytics unless explicitly requested. VM/node count alone never triggers monitoring. |
| Hours | 730 h/month unless the user supplies another usage assumption. |
| Support | No paid support plan. List support plan under exclusions; retain only any unavoidable no-charge calculator Basic support entry. |
| Taxes | Excluded. State "excludes VAT". |
| Non-production | The same public retail PAYG price list as production; no environment-based discount program or output line. |
| Region | Confirm the profile region on first run; suggest UAE North. Apply availability-gate.md before every line. Any change requires explicit user approval, residency review and per-environment disclosure. GA default, explicit request-scoped preview opt-in only. |
| HA | Single zone / non-zone-redundant wherever this affects cost. Explicit HA, highly available, zone-redundant or 99.99% requirements select zone redundancy for that workload/environment ONLY. The user's explicit HA override governs its stated scope. Verify regional support; do not promise that zone redundancy alone meets an application SLA. Disclose per environment. |
| Storage | Premium SSD v2 for data/database/managed data disks. Premium SSD for VM OS disks because v2 cannot be an OS disk. Never relabel Blob, Azure Files or service-managed storage as v2 or add duplicate managed disks to PaaS. If the requested service/calculator cannot support v2 where this policy would apply, disclose the limitation and ask which alternative to use. Never silently fall back. |
| Storage disclosure | Verify current compatibility and disclose material Premium SSD v2 zonal-placement, availability-set, host-caching, Backup or Site Recovery limitations in review notes and customer-facing assumptions. Include only applicable caveats; incompatibility requires an approved alternative, not silent fallback. |
| Build date | Record the invocation's current local build date; do not reuse this file's authoring date. |

Required licensing text whenever AHB is applied:

> Azure Hybrid Benefit has been applied to the identified eligible workloads based on confirmed licence eligibility and coverage; eligible licences with active Software Assurance (or equivalent subscription licences) are required.

Use that exact sentence only when AHB is actually applied, and identify its workload scope. For eligible but unconfirmed or explicitly licence-included lines say: "Azure Hybrid Benefit has not been applied to these workloads; licence-included pricing is used where applicable." For entirely ineligible scopes say: "No lines in this scope are AHB-eligible; no AHB discount was taken." Mixed scopes must distinguish both bases. Never invent a toggle or licence price. Keep applicable English disclaimers verbatim even when the surrounding draft is in another language.

## Tunable planning constants

These numbers are intentionally rough assumptions, NOT measured usage, vendor sizing guidance, or quoted prices. Prompt-specific usage overrides never edit these constants.

| Constant | Default | Use |
|---|---:|---|
| DEFAULT_EGRESS_GB_PER_MONTH_PER_INTERNET_FACING_WORKLOAD | 100 | Monthly internet egress GB for each known internet-facing workload when the customer supplied no traffic figure. |
| DEFAULT_REQUESTED_LOG_INGESTION_GB_PER_VM_PER_MONTH | 5 | ONLY after Monitor/Log Analytics ingestion is explicitly requested but volume is missing: GB/month per VM/node, counted once. Never an inclusion trigger. |
| DEFAULT_REQUESTED_LOG_INGESTION_GB_WITHOUT_VM_COUNT | 5 | ONLY for explicitly requested ingestion with no defensible VM/node count: GB/month per environment. |

For unknown internet-facing workload count, assume one egress allowance per environment and label it as a planning placeholder, not a newly added workload. If the source explicitly establishes zero internet egress, retain a zero-usage bandwidth allowance and explain why. Do not double-count supplied traffic or multiply an already environment-total figure by the VM count.

## Totals and retail spot-check method

- Capture recurring monthly and upfront USD separately; upfront MUST be zero. PAYG annual and monthly-paid term annualisation = monthly x 12. For a requested N-month usage horizon also show monthly x N, clearly separated from a contractual reservation/Savings Plan term. An amortised display is not proof that payment is monthly: verify the actual payment selector. If monthly payment cannot be selected/evidenced for an eligible requested term, use PAYG for that scope and disclose "requested term not priced: monthly payment unavailable" rather than invent a zero-upfront option or stop for ordinary clarification.
- Select the three largest line-level annualised costs (all if fewer than three). Reconstruct each line's cost from all contributing retail meters, including any distinct compute/software/storage/performance components already inside it. This comparison does not authorize adding new estimate components.
- Query the unauthenticated [Azure Retail Prices API](https://prices.azure.com/api/retail/prices) with `armRegionName` equal to the verified ARM name of each line's actual region, exact service, product, `armSkuName`/SKU and meter (URL-encode the filter). Do not derive the ARM name by merely removing spaces. Request USD; filter `priceType eq 'Consumption'` for PAYG and exclude Spot/Low Priority and all nonstandard consumption price lists. Follow `NextPageLink` until the required exact matches are found; do not pick the first similarly named meter.
- Match current effective price, primary meter, OS, edition, licensing/AHB, unitOfMeasure, tierMinimumUnits, quantity and hours. For AHB match eligible base compute plus any still-payable licensing, not the licence-included Windows/SQL price. Never equate "AHB" to free software for every service.
- Apply documented billing units and allowances when comparing like-for-like calculator totals. If billing scope/remaining allowance is unspecified or separate estimates repeat a shared allowance, retain native calculator inputs and totals and disclose that independently exported estimates may repeat credits. Do not create adjusted budget totals, an Egress Adjustment sheet or a companion correction workbook. Do not inflate usage to manufacture charges. Compare each estimate using its actual calculator allowance basis; unresolved arithmetic/meter mismatches still block. Bandwidth may use zone/global meters: verify documented scope, not an invented regional meter.
- Only for an explicit reservation request, match `priceType eq 'Reservation'` and `reservationTerm`; an API term price is not an upfront-payment instruction. Verify monthly payment support and divide term amount by documented term months for comparison with monthly payments. Add undiscounted components where applicable. Only for an explicit Savings Plan request, use documented `2023-01-01-preview` API `savingsPlan` term/rate and monthly-payment setting; this API version does not authorize preview Azure SKUs. A missing requested term length defaults to one year, disclosed, without making an actual commitment.
- Compare like-for-like amounts before rounding: absolute(calculator - reconstructed API) / absolute(API) x 100. Both zero = 0%; API zero with nonzero calculator = mismatch. Difference >2% requires rechecking calculator settings/meters. An unresolved difference, API error or unmatched required meter blocks with `uncertain_outcome`; never confirm an estimate with an unresolved check.
- Record checked product/meter, units, matched rate, reconstructed amount, calculator amount, delta, source URL and check date in the conversation's verification detail. No customer names, source content or identifiers belong in public API query strings.

## Retail control and output boundaries

After calculator sign-in, inspect the Licensing Program selector AND the displayed price basis. Select its public retail/PAYG option, not an EA/CSP/negotiated billing-account price sheet. UI labels may change; a PAYG purchase-model toggle alone does not establish public retail. If the selector or public basis cannot be verified, `block` with `other` and tell the user.

Every estimate and both outputs disclose USD, usage hours, retail pricing, actual region, actual scoped HA, actual OS/OS-only disk basis, applicable licensing basis, support-plan exclusion, VAT exclusion, zero upfront payment and build date. Preview status and material limitations appear in user review notes and customer-facing assumptions, not an added Excel release-status section. No APE/WB/internal tracking markers in any calculator item, name, description or link. Copy generated share URLs unmodified; rotating URLs are delivery artifacts, not saved-estimate identities. Do not add currency conversions, discount-program lines, AHB comparisons, or unrequested reservation/Savings Plan lines.

Disclose only applicable, material PV2 constraints, including operational implications when they affect the estimate's viability. Do not suppress them merely because they mention Backup, Site Recovery or another platform component.

Authoring sources verified through Learn MCP on 2026-09-16: [Calculator controls and licensing programs](https://learn.microsoft.com/en-us/azure/cost-management-billing/costs/pricing-calculator), [Retail API fields, filtering, pagination and terms](https://learn.microsoft.com/en-us/rest/api/cost-management/retail-prices/azure-retail-prices). These references contain no quoted prices; verify actual prices and product availability at run time.

Monthly-payment/term distinction verified through Learn MCP on 2026-09-16: [Reservations](https://learn.microsoft.com/en-us/azure/cost-management-billing/reservations/save-compute-costs-reservations), [Savings plans](https://learn.microsoft.com/en-us/azure/cost-management-billing/savings-plan/savings-plan-compute-overview). Monthly payments do not remove the contractual term.

Shareable-edition references checked on 2026-09-30: [Windows Server AHB eligibility and licence coverage](https://learn.microsoft.com/windows-server/get-started/azure-hybrid-benefit), [Premium SSD v2 regional support and current limitations](https://learn.microsoft.com/azure/virtual-machines/disks-deploy-premium-v2). Recheck the specific service's licensing terms and storage constraints at run time; Windows Server terms do not establish eligibility for SQL Server or other products.
