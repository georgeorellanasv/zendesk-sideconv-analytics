# Classification Rules

_Defined collaboratively with George in Phase 2.5 based on real data from discover scripts._

## Categories

_To be populated after Phase 2.5 exploratory discovery._

Planned categories (subject to revision after seeing real subjects):

### Outbound (Ria → external)
- `rfi_outbound` — Generic Request for Information to partner
- `proof_of_payment_request` — Requesting proof/comprobante of payment
- `transaction_trace` — Requesting trace/investigation of a transaction
- `cancellation_request` — Requesting cancellation of a transaction
- `refund_request` — Requesting refund processing
- `recall_request` — Requesting funds recall
- `compliance_inquiry` — Compliance/AML inquiry to partner
- `status_update_request` — Requesting status update

### Inbound (external → Ria)
- `rfi_inbound` — Partner requests information from Ria
- `compliance_request_from_partner` — Partner requests compliance info from Ria
- `acknowledgment` — Partner acknowledges or provides an update

### Internal
- `internal_collaboration` — Coordination between Ria teams

### Catch-all
- `other` — Does not match any clear category

## Confidence Levels

- `high` — Subject clearly matches a single category keyword
- `medium` — Partial match or inferred from context
- `low` — Default / no match (classified as `other`)

## Domain → Correspondent Mapping

_To be populated after Phase 2.5 based on `external_domains.csv`._

## Ria Internal Domains

_To be populated after Phase 2.5 based on user confirmation._

Known at project start:
- `riamoneytransfer.com`
- `dandelionpayments.com`
- `euronet.com`
