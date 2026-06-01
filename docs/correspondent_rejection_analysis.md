# Correspondent rejection analysis — methodology

This document describes the analytical pattern and visual language developed
for **dlocal** that we want to reuse for every correspondent (Uniteller, BDO,
Banorte, Transnetwork, etc.). It has two parts: the **analysis structure**
(what we measure and how) and the **design system** (how it looks).

## When to use this pattern

Apply this methodology when:

1. We receive a **rejection export** from a correspondent (one row per
   rejected / cancelled order, with sender country, destination country,
   bank, reason, date).
2. We want to cross-reference that operational reality against the **Care
   tickets** where that correspondent is tagged — i.e. the customers who
   complained vs. the rejections the correspondent handled silently.
3. A stakeholder has asked "where is this correspondent hurting us and what
   should we do about it?" — this pattern answers in seven ordered sections.

## Required inputs

### Rejection export (one per correspondent)
A spreadsheet with at minimum these columns (rename in the loader as needed):

| Column                | Meaning                                                        |
|-----------------------|----------------------------------------------------------------|
| `fOrderNo`            | Order ID in Ria's canonical format (`US854335909`)             |
| `fCountryFrom`        | Sender country (ISO-2)                                          |
| `fCountryTo`          | Destination country (ISO-2)                                     |
| `fBankName`           | Receiving bank name                                             |
| `Detalle Correspondent` | Machine-readable rejection reason (e.g. "Invalid Account.")   |
| `Nota Completa`       | Free-text notes — fallback when `Detalle` is empty              |
| `status`              | Cancel / Paid / etc.                                            |
| `fEnteredTime`        | Timestamp                                                       |

### Zendesk tickets
Already in `data/sideconv.db` via the normal extraction pipeline. We filter to
Care groups (`GROUP_IDS_CARE` in `.env`) and link by **order ID regex match**
against `subject` and `description`:

```python
ORDER_ID_RX = re.compile(r"\b([A-Z]{2}\d{6,})\b")
```

The shared loaders live in `src/dlocal_rejections.py` — rename when reusing
(see "Reuse playbook" below).

## The eight-section structure

Every correspondent report follows this order. Reasoning below.

| # | Section                                         | Purpose                                                                       |
|---|-------------------------------------------------|-------------------------------------------------------------------------------|
| 1 | **Executive summary**                            | KPIs in a grid + 4-bullet narrative. Must read in <60 s.                       |
| 2 | **Interactive drill — reason × country × bank** | Three cross-filtering charts + time-series. The analyst's working surface.    |
| 3 | **Remittance corridors**                         | Top 15 sender→destination pairs, coloured by ticket-attach rate.               |
| 4 | **Silent majority**                              | Rejections that never reached Care — attach rate by reason.                   |
| 5 | **What Care handled (Zendesk side)**             | Tickets by status / agent-assigned reason / monthly volume.                   |
| 6 | **Destination banks**                            | Top 15 receiving banks + dominant rejection reason for each.                  |
| 7 | **Recommendations**                              | Six actionable items (data-quality, partner engagement, automation).          |

Why this order: executive summary first (you're allowed to stop there), then
the self-serve drill (most time is spent here), then progressively narrower
cross-sections, ending with action.

## Section 2 — the cross-filter drill (the heart of the page)

Three charts in **three equal columns** (read left → right):

1. **Rejection reasons** (clay sequential scale)
2. **Destination countries** (sand sequential scale)
3. **Receiving banks** (slate sequential scale)

Followed by a **time-series chart** underneath, one line per rejection reason
(top 8) plus a dotted "All reasons" total line, with `hovermode="x unified"`
so hovering any date lists every reason's count on that date. The time chart
**follows the active filters** and has a day / week / month granularity
toggle.

### Bidirectional cross-filter — the invariant

- Each of the three filters (`reason`, `country`, `bank`) is independent and
  stored in `st.session_state`.
- A chart's bars are computed over the dataset filtered by the **other two**
  dimensions, not its own — so the selected bar stays visible and clicking
  any chart narrows the remaining two.
- Selected bars get a **clay outline** (3 px, `#CC785C`) — visual
  confirmation that the click registered.
- A **Reset filters** button clears all three at once.

### Normalising reason values

Very long bureaucratic reasons (e.g. "Received - If cancellation is required,
it should be performed from the correspondents portal…") collapse to
`"Other"` at load time so the bar chart stays readable. Collapse rule used
for dlocal:

```python
df["reason"] = df["reason"].where(
    ~df["reason"].astype(str).str.contains(
        r"correspondents?\s+portal|supervisor\s+for\s+assistance",
        case=False, regex=True, na=False,
    ),
    "Other",
)
```

Adjust the regex per correspondent as new verbose reasons appear.

## Visual design — Anthropic-inspired palette

Used throughout the drill card so every correspondent report feels the same.

| Token               | Hex          | Role                                   |
|---------------------|-------------|----------------------------------------|
| `ANTHROPIC_PAPER`   | `#F5F4EE`   | Soft cream background (card + plot)    |
| `ANTHROPIC_INK`     | `#1F1D1B`   | Near-black text                        |
| `ANTHROPIC_CLAY`    | `#CC785C`   | Primary accent — selected-bar outline  |
| `ANTHROPIC_CLAY_DARK` | `#A1543D` | Clay at max in sequential scale        |
| `ANTHROPIC_SAND`    | `#EBE5D7`   | Secondary warm beige                   |
| `ANTHROPIC_BORDER`  | `rgba(20,20,19,0.10)` | Thin warm border / gridlines  |

### Plotly scales

```python
ANTHROPIC_CLAY_SCALE  = [[0.0,"#F5F4EE"],[0.3,"#E6C2B0"],[0.6,"#D49B82"],[1.0,"#A1543D"]]  # reasons
ANTHROPIC_SAND_SCALE  = [[0.0,"#F5F4EE"],[0.4,"#EBE5D7"],[0.7,"#C9A27E"],[1.0,"#8C6B4A"]]  # countries
ANTHROPIC_SLATE_SCALE = [[0.0,"#F5F4EE"],[0.4,"#D1D7DE"],[0.7,"#8C9AA8"],[1.0,"#3C4D5E"]]  # banks

ANTHROPIC_QUALITATIVE = [
    "#CC785C", "#1F1D1B", "#6A8CAA", "#A8B796",
    "#C9A27E", "#7E8D83", "#A1543D", "#D1BFA7",
]
```

### Typography

- Family: `Inter, -apple-system, BlinkMacSystemFont, sans-serif`
- Body 14 px · Titles 17 px · Legend 13 px
- Letter-spacing `-0.01em` on headings for the crisp Anthropic feel

### Container (Streamlit)

```python
with st.container(border=True):
    ...
```

Styled via CSS:
```css
div[data-testid="stVerticalBlockBorderWrapper"] {
  background: #F5F4EE;
  border: 1px solid rgba(20,20,19,0.10);
  border-radius: 14px;
  padding: 24px;
  box-shadow: 0 1px 2px rgba(0,0,0,0.04),
               0 4px 12px rgba(0,0,0,0.03);
}
```

## Reuse playbook — applying this to a new correspondent

1. **Add a config entry** (if needed) for the correspondent's search query
   and any custom field IDs in `src/config.py`.
2. **Add a new loader module** `src/<correspondent>_rejections.py` that
   imports from `src/dlocal_rejections.py` as a template. The only things
   likely to change: the correspondent name matching in `load_zendesk_*()`
   and the verbose-reason regex for normalisation.
3. **Duplicate the Streamlit page block** in `src/dashboard.py`:
   - Copy the `elif page == "nav_dlocal_rej":` block.
   - Rename to `nav_<correspondent>_rej`.
   - Swap loaders and the default rejection file path.
   - Keep the palette / styling constants unchanged (they're the shared
     visual language).
4. **Add nav entry + i18n labels** for the new page.
5. **Optional: build a standalone HTML** via
   `scripts/build_<correspondent>_report.py` — copy
   `scripts/build_dlocal_report.py` and swap the loaders.

The goal: the analyst sees the same layout, colour-coding and drill
mechanics for every correspondent we analyse. Consistency = faster reading.

## Why this pattern works

- **One drill answers most questions.** Instead of a dozen static charts,
  the bidirectional filter lets the user write their own question:
  *"what banks in Nigeria have Invalid Account rejections?"* is a click path
  (Invalid Account → Nigeria → read the banks chart + the time-series).
- **Silent-majority section forces a business reframe.** Most correspondent
  reports stop at rejection counts. We go one step further and show what
  fraction of those rejections even reached Care — turning volume data into
  a discussion about UX and customer retention.
- **The Anthropic palette is warm and printable.** Cream + ink survives
  black-and-white printing, projector contrast, and executive scrutiny
  better than saturated blues/reds.

## Pitfalls to avoid

- **Don't drop the total line** from the time-series. Analysts want to see
  both the composition and the absolute trend.
- **Don't expand the bar charts to >12 categories.** Above that, the human
  eye loses the ranking.
- **Don't use raw country codes** on chart labels — always pass through
  `pretty_country()` so "NG" becomes "Nigeria".
- **Don't hardcode the correspondent name in section headings.** Keep it in
  a single top-level title so the template is truly reusable.

---

**Primary implementation references:**
- [src/dlocal_rejections.py](../src/dlocal_rejections.py) — shared data layer
- [src/dashboard.py](../src/dashboard.py) — Streamlit page
  (`elif page == "nav_dlocal_rej":`)
- [scripts/build_dlocal_report.py](../scripts/build_dlocal_report.py) — HTML
  variant
