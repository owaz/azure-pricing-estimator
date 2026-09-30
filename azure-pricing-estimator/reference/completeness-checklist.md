# Completeness checklist

Mandatory for every workbook/environment in azure-pricing-estimator v2.3.

Walk BOTH lists and the closed dependency list for EACH environment. Keep quantities, assumptions, costs and source provenance separate. Each included line still needs the regional availability gate and commercial defaults. GA is the default; evidenced previews require explicit request-scoped opt-in, including any preview dependency.

## A. ALWAYS ADD, even if not listed; disclose the assumption

| Component | Inclusion and sizing |
|---|---|
| AKS system node pool | For each requested AKS cluster, if no qualifying system pool is listed, add a small current-GA general-purpose system pool with the minimum node count and capabilities currently required by AKS. Reuse a listed qualifying system pool rather than duplicate it. Verify the current minimum and supported OS/SKU through Learn at run time; do not hard-code a SKU or node minimum from this reference. Choose the smallest suitable GA D-series SKU in the configured region meeting those constraints. Disclose SKU, count, hours and reason. |
| AKS control-plane tier | Production -> Standard tier (Uptime SLA). Non-production -> Free tier unless HA is explicitly stated, in which case use Standard. The SLA is for the Kubernetes API server, not the whole application. Apply the scoped zone-redundancy rule separately. Do not substitute Premium without a requirement. |
| AKS load balancer | One Standard Load Balancer per cluster. If already listed for that cluster, count it once; do not add a second line. Disclose its assumed rule/data-processing usage if absent. Do not add other platform components by analogy. |
| Internet bandwidth/egress | Add internet egress in every environment wherever possible. Use supplied GB/month; otherwise use `DEFAULT_EGRESS_GB_PER_MONTH_PER_INTERNET_FACING_WORKLOAD` from commercial-defaults.md. Disclose workload count, monthly GB and any one-workload placeholder. Apply verified free allowances/tiering once, not once per VM. If the source establishes zero egress, retain a disclosed zero-usage allowance. If no supported meter exists, surface the limitation rather than silently omit it. Add explicitly requested bandwidth items; ExpressRoute/VPN data is excluded from this automatic allowance and handled only with explicit scoped requirements under B. |

For missing inputs on an included meter (such as LB processing/rules), use disclosed workload-based planning values and current service minimums; follow clarification-matrix.md instead of pausing for ordinary sizing. Never call assumed usage customer-supplied.

## Explicit monitoring only

Azure Monitor / Log Analytics is NOT an always-add component. Add it only if the source/invoking user explicitly requests it as in-scope work, not merely because VMs, AKS nodes, logs or observability best practices exist. With an explicit request and missing ingestion volume, use `DEFAULT_REQUESTED_LOG_INGESTION_GB_PER_VM_PER_MONTH` or `DEFAULT_REQUESTED_LOG_INGESTION_GB_WITHOUT_VM_COUNT`. Add ingestion only unless other monitoring features are expressly requested; no automatic Defender/Sentinel/paid retention/alerts. With no request, add no monitoring line, volume, placeholder or charge.

## B. LANDING-ZONE COMPONENTS: add ONLY if explicitly named

Applies to Azure Bastion, VPN Gateway, ExpressRoute Gateway and circuit, Azure Firewall, NAT Gateway, Key Vault, DDoS Protection, Defender for Cloud, Backup vault/storage, Site Recovery, Azure DNS, Private Link/Private Endpoints, Application Gateway/WAF, standalone public IPs beyond what a requested service needs, and similar shared platform services.

Apply this decision rule literally:

- IF the source (selected email body, BOQ, PDF, workbook, or the user's prompt) names the component, THEN add it to that environment's estimate with the stated quantity/SKU, or disclosed estimated sizing under clarification-matrix.md if absent. "Names" means a requested scope item, not an example, explicit exclusion or mere mention in a quoted history.
- IF the source does NOT name the component, THEN do NOT add it. This is a scope boundary, not evidence the customer already has a landing zone. If the architecture clearly depends on it, write "Consider adding: <item> — <reason>" under "Not priced — consider" in the user review notes/authorized Teams self-chat. Disclose a material prerequisite or incompatibility for a priced resource in customer assumptions without adding an unrequested priced component.
- Never infer a priced component from "secure", "connected to on-prem", "private" or similar general language. These justify a consider item only.
- A generic HA requirement does not authorize adding Backup, Site Recovery or another regional environment. Price zone redundancy only for its stated scope.
- Do not add an ExpressRoute Gateway merely because a circuit is named, or a circuit because a gateway is named. Standalone public IPs beyond what a requested service requires are explicit-only; a strictly mandatory service-required IP may be configured as part of that service after verifying the requirement. Never use this exception to add optional NAT, Key Vault or other platform services.
- Keep unrequested B-list recommendations in user-only review notes, not a customer upsell list. Requested components remain in the Excel BOQ and calculator scope. Material sizing assumptions, prerequisites or compatibility limitations for priced resources must appear in customer-facing assumptions when needed, including relevant storage/Backup/Site Recovery constraints. Never hide a material limitation to avoid naming a component.

## C. Implied dependencies of a requested service: closed list

Add and disclose ONLY these dependencies; do not expand the list:

| Requested service | Allowed dependency |
|---|---|
| VM | One Premium SSD OS disk per VM fitting the verified image/source requirement. If no OS is supplied, Ubuntu Linux. If no data-disk requirement is mentioned, OS disk only; explicitly requested unsized data disks use disclosed planning sizing. |
| App Service without a plan | App Service plan; select a fitting regional GA plan, using disclosed baseline tier/quantity where missing. Do not duplicate a supplied shared plan within the same environment. |
| SQL Managed Instance | Enforce the current documented minimum vCores for the requested tier/hardware. Record upward rounding; do not invent a universal minimum or extra instance. |
| AKS | System pool, control-plane tier and one Standard Load Balancer per cluster exactly as section A. |

Check explicit line items already cover an allowed dependency before adding it; do not count the same resource twice. No resource or allowance is shared/summed across environments without a source-defined shared environment of its own.

Runtime sources: [AKS system pools](https://learn.microsoft.com/en-us/azure/aks/use-system-pools), [AKS pricing tiers and SLA scope](https://learn.microsoft.com/en-us/azure/aks/free-standard-pricing-tiers). Reverify service minimums, supported SKUs and regional GA when invoked.
