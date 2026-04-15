# Data Dictionary

_Populated in Phase 2.5 after exploratory discovery._

## Table: tickets

| Column | Type | Description |
|--------|------|-------------|
| ticket_id | INTEGER PK | Zendesk ticket ID |
| subject | TEXT | Ticket subject |
| status | TEXT | open / pending / hold / solved / closed |
| reason_raw | TEXT | Raw value from "Reason for Contact" custom field |
| reason_l1 | TEXT | Derived: first segment of reason_raw (e.g. "Order") |
| reason_l2 | TEXT | Derived: second segment of reason_raw (e.g. "Refund") |
| correspondent_full | TEXT | Raw value from Correspondent custom field |
| correspondent_name | TEXT | Parsed: name portion (e.g. "Banorte") |
| correspondent_code | TEXT | Parsed: code in parentheses (e.g. "Unitelier") |
| ... | | _To be completed after Phase 1_ |

## Table: side_conversations

| Column | Type | Description |
|--------|------|-------------|
| side_conversation_id | TEXT PK | UUID assigned by Zendesk |
| ticket_id | INTEGER FK | Parent ticket |
| sc_direction | TEXT | ria_to_external / external_to_ria / internal |
| sc_reason_classification | TEXT | Category (defined in Phase 2.5) |
| sc_reason_confidence | TEXT | high / medium / low |
| ... | | _To be completed after Phase 2.5_ |

## Table: side_conversation_events

_To be completed after Phase 2._

## Table: extraction_log

_To be completed after Phase 3._
