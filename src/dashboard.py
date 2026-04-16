"""
Fase 5 — Dashboard Streamlit.

Visualiza tickets y side conversations extraídas de la vista US Care de Zendesk.

Usage (desde el root del proyecto, con el venv activo):
    streamlit run src/dashboard.py
"""

import io
import sqlite3
import sys
from pathlib import Path

# Ensure project root is in path when running via `streamlit run`
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd
import plotly.express as px
import streamlit as st

from src.config import DB_PATH
from src.concepts_content import CONCEPTS_EN, CONCEPTS_ES
from src.i18n import t

# ---------------------------------------------------------------------------
# Page config
# ---------------------------------------------------------------------------

st.set_page_config(
    page_title="Ria CX — Side Conversations Analytics",
    page_icon="📊",
    layout="wide",
)

# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------


@st.cache_data(ttl=300)
def load_data() -> tuple[pd.DataFrame, pd.DataFrame]:
    conn = sqlite3.connect(DB_PATH)

    tickets = pd.read_sql_query(
        """
        SELECT
            ticket_id, subject, status, created_at, updated_at,
            reason_raw, correspondent_raw, country_raw, product_raw,
            side_conv_count
        FROM tickets
        """,
        conn,
        parse_dates=["created_at", "updated_at"],
    )

    side_convs = pd.read_sql_query(
        """
        SELECT
            sc.side_conv_id,
            sc.ticket_id,
            sc.sc_sequence,
            sc.subject       AS sc_subject,
            sc.state,
            sc.created_at,
            sc.updated_at,
            sc.sc_direction,
            sc.sc_recipient_type,
            sc.sc_reason_classification,
            sc.sc_reason_confidence,
            sc.external_reply_at,
            sc.external_response_hrs,
            sc.last_counterparty_reply_at,
            sc.resolution_hrs,
            sc.total_exchanges,
            t.reason_raw,
            t.correspondent_raw,
            t.status         AS ticket_status
        FROM side_conversations sc
        JOIN tickets t ON t.ticket_id = sc.ticket_id
        """,
        conn,
        parse_dates=["created_at", "updated_at"],
    )

    conn.close()

    for col in ["sc_direction", "sc_recipient_type", "sc_reason_classification"]:
        side_convs[col] = side_convs[col].fillna("unknown")

    side_convs["correspondent"] = (
        side_convs["correspondent_raw"]
        .fillna("")
        .str.split("::")
        .str[0]
        .str.strip()
        .replace("", "Sin corresponsal")
    )

    tickets["reason_l1"] = tickets["reason_raw"].str.split("__").str[0].fillna("(vacío)")
    tickets["reason_l2"] = tickets["reason_raw"].str.split("__").str[1].fillna("")

    return tickets, side_convs


@st.cache_data(ttl=300)
def load_full_db() -> pd.DataFrame:
    """Carga completa: tickets + side convs + eventos, ordenada por ticket y side conv."""
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql_query(
        """
        SELECT
            t.ticket_id,
            t.subject          AS ticket_subject,
            t.status           AS ticket_status,
            t.created_at       AS ticket_created,
            t.updated_at       AS ticket_updated,
            t.reason_raw,
            t.correspondent_raw,
            t.country_raw,
            t.product_raw,
            t.side_conv_count,
            sc.side_conv_id,
            sc.sc_sequence,
            sc.subject         AS sc_subject,
            sc.state           AS sc_state,
            sc.created_at      AS sc_created,
            sc.sc_direction,
            sc.sc_recipient_type,
            sc.sc_reason_classification,
            sc.sc_reason_confidence,
            sc.external_reply_at,
            sc.external_response_hrs,
            sc.last_counterparty_reply_at,
            sc.resolution_hrs,
            sc.total_exchanges,
            e.event_id,
            e.event_sequence,
            e.event_type,
            e.created_at       AS event_created,
            e.actor_name,
            e.actor_email,
            e.from_address,
            e.to_addresses,
            e.message_subject,
            e.message_body
        FROM tickets t
        LEFT JOIN side_conversations sc ON sc.ticket_id = t.ticket_id
        LEFT JOIN side_conversation_events e ON e.side_conv_id = sc.side_conv_id
        ORDER BY t.ticket_id, sc.sc_sequence, e.event_sequence
        """,
        conn,
    )
    conn.close()
    return df


tickets_df, sc_df = load_data()

# ---------------------------------------------------------------------------
# Language selector
# ---------------------------------------------------------------------------

lang = st.sidebar.selectbox(
    "🌐 Language / Idioma",
    options=["en", "es"],
    format_func=lambda x: "English" if x == "en" else "Español",
    index=0,
)

# ---------------------------------------------------------------------------
# Navegación
# ---------------------------------------------------------------------------

page_keys = [
    "nav_analytics",
    "nav_operational",
    "nav_partner",
    "nav_customer",
    "nav_database",
    "nav_concepts",
]
page_labels = [t(k, lang) for k in page_keys]
page_idx = st.sidebar.radio(
    t("page_label", lang),
    options=range(len(page_keys)),
    format_func=lambda i: page_labels[i],
)
page = page_keys[page_idx]

# ---------------------------------------------------------------------------
# Sidebar — filtros (aplican a ambas páginas)
# ---------------------------------------------------------------------------

st.sidebar.markdown("---")
st.sidebar.title(t("filters", lang))

ALL = t("all", lang)
direction_opts = [ALL] + sorted(sc_df["sc_direction"].unique().tolist())
sel_direction = st.sidebar.selectbox(t("thread_direction", lang), direction_opts)

recipient_opts = [ALL] + sorted(sc_df["sc_recipient_type"].unique().tolist())
sel_recipient = st.sidebar.selectbox(t("recipient_type", lang), recipient_opts)

reason_opts = [ALL] + sorted(sc_df["sc_reason_classification"].unique().tolist())
sel_reason = st.sidebar.selectbox(t("classification", lang), reason_opts)

st.sidebar.markdown("---")
st.sidebar.caption(
    f"DB: `{DB_PATH.name}`  \n"
    f"{len(tickets_df):,} tickets · {len(sc_df):,} side convs"
)

# Aplicar filtros a side_convs
filtered = sc_df.copy()
if sel_direction != ALL:
    filtered = filtered[filtered["sc_direction"] == sel_direction]
if sel_recipient != ALL:
    filtered = filtered[filtered["sc_recipient_type"] == sel_recipient]
if sel_reason != ALL:
    filtered = filtered[filtered["sc_reason_classification"] == sel_reason]


# =========================================================================
# PAGE: ANALYTICS
# =========================================================================

if page == "nav_analytics":
    st.title(t("title_analytics", lang))
    st.caption(t("caption_analytics", lang))

    # --- Calculate message total from full_db (loaded lazily) ---
    @st.cache_data(ttl=300)
    def _total_messages() -> int:
        conn = sqlite3.connect(DB_PATH)
        n = conn.execute("SELECT COUNT(*) FROM side_conversation_events").fetchone()[0]
        conn.close()
        return n

    total_messages = _total_messages()
    total_tickets = len(tickets_df)
    total_threads = len(sc_df)
    avg_threads_per_ticket = total_threads / max(total_tickets, 1)
    avg_msgs_per_thread = total_messages / max(total_threads, 1)

    # ============================================================
    # ROW 1 — KPIs jerárquicos (5 cards: Ticket → Thread → Message)
    # ============================================================
    st.markdown("### 🎫→💬→✉️  " + ("Jerarquía de datos" if lang == "es" else "Data Hierarchy"))
    k1, k2, k3, k4, k5 = st.columns(5)
    k1.metric(t("total_tickets", lang), f"{total_tickets:,}", help=t("kpi_total_tickets_help", lang))
    k2.metric(t("total_threads", lang), f"{total_threads:,}", help=t("kpi_total_threads_help", lang))
    k3.metric(t("kpi_total_messages", lang), f"{total_messages:,}", help=t("kpi_total_messages_help", lang))
    k4.metric(t("kpi_avg_threads_per_ticket", lang), f"{avg_threads_per_ticket:.1f}", help=t("kpi_avg_threads_per_ticket_help", lang))
    k5.metric(t("kpi_avg_msgs_per_thread", lang), f"{avg_msgs_per_thread:.1f}", help=t("kpi_avg_msgs_per_thread_help", lang))

    st.markdown("---")

    # ============================================================
    # ROW 2 — Razones por nivel de jerarquía
    # ============================================================
    st.markdown(f"### {t('sec_reasons', lang)}")
    col1, col2 = st.columns(2)

    with col1:
        st.subheader(t("chart_tickets_by_reason", lang), help=t("chart_tickets_by_reason_help", lang))
        tickets_in_filter = tickets_df[tickets_df["ticket_id"].isin(filtered["ticket_id"])]
        reason_l1 = (
            tickets_in_filter.groupby("reason_l1").size()
            .reset_index(name="count").sort_values("count", ascending=True).tail(12)
        )
        fig_tr = px.bar(
            reason_l1, x="count", y="reason_l1", orientation="h",
            color="count", color_continuous_scale="Greens",
            labels={"reason_l1": "", "count": "# tickets"},
        )
        fig_tr.update_layout(coloraxis_showscale=False, height=400, margin=dict(l=0, r=0, t=10, b=0))
        st.plotly_chart(fig_tr, use_container_width=True)

    with col2:
        st.subheader(t("chart_threads_by_class", lang), help=t("chart_threads_by_class_help", lang))
        thread_class = (
            filtered.groupby("sc_reason_classification").size()
            .reset_index(name="count").sort_values("count", ascending=True).tail(12)
        )
        fig_tc = px.bar(
            thread_class, x="count", y="sc_reason_classification", orientation="h",
            color="count", color_continuous_scale="Blues",
            labels={"sc_reason_classification": "", "count": "# threads"},
        )
        fig_tc.update_layout(coloraxis_showscale=False, height=400, margin=dict(l=0, r=0, t=10, b=0))
        st.plotly_chart(fig_tc, use_container_width=True)

    st.markdown("---")

    # ============================================================
    # ROW 3 — Corresponsales: volumen + tiempo de respuesta
    # ============================================================
    st.markdown(f"### {t('sec_correspondents', lang)}")
    col3, col4 = st.columns(2)

    sc_ext = filtered[filtered["sc_recipient_type"] == "correspondent"]

    with col3:
        st.subheader(t("chart_top_corr_volume", lang), help=t("chart_top_corr_volume_help", lang))
        if sc_ext.empty:
            st.info(t("no_correspondents", lang))
        else:
            top_corr = (
                sc_ext.groupby("correspondent").size()
                .reset_index(name="count").sort_values("count", ascending=False).head(10)
            )
            fig_vol = px.bar(
                top_corr, x="correspondent", y="count",
                color="count", color_continuous_scale="Oranges",
                labels={"correspondent": "", "count": "# threads"},
            )
            fig_vol.update_layout(
                coloraxis_showscale=False, height=360,
                margin=dict(l=0, r=0, t=10, b=0), xaxis_tickangle=-35,
            )
            st.plotly_chart(fig_vol, use_container_width=True)

    with col4:
        st.subheader(t("chart_corr_response", lang), help=t("chart_corr_response_help", lang))
        if sc_ext.empty:
            st.info(t("no_correspondents", lang))
        else:
            resp_corr = (
                sc_ext.dropna(subset=["external_response_hrs"])
                .groupby("correspondent")
                .agg(median_hrs=("external_response_hrs", "median"),
                     n=("external_response_hrs", "count"))
                .reset_index()
            )
            resp_corr = resp_corr[resp_corr["n"] >= 3]
            resp_corr = resp_corr.sort_values("median_hrs", ascending=True).head(10)
            if not resp_corr.empty:
                fig_resp = px.bar(
                    resp_corr, x="correspondent", y="median_hrs",
                    color="median_hrs", color_continuous_scale="RdYlGn_r",
                    labels={"correspondent": "", "median_hrs": "Median (hrs)"},
                )
                fig_resp.update_layout(
                    coloraxis_showscale=False, height=360,
                    margin=dict(l=0, r=0, t=10, b=0), xaxis_tickangle=-35,
                )
                st.plotly_chart(fig_resp, use_container_width=True)

    st.markdown("---")

    # ============================================================
    # ROW 4 — Dirección + Recipient Type
    # ============================================================
    st.markdown(f"### {t('sec_direction', lang)}")
    col5, col6 = st.columns(2)

    with col5:
        st.subheader(t("by_direction", lang))
        dir_counts = filtered.groupby("sc_direction").size().reset_index(name="count")
        fig_dir = px.pie(
            dir_counts, names="sc_direction", values="count",
            hole=0.45, color_discrete_sequence=px.colors.qualitative.Set2,
        )
        fig_dir.update_traces(textposition="inside", textinfo="percent+label")
        fig_dir.update_layout(showlegend=False, height=360, margin=dict(l=0, r=0, t=10, b=0))
        st.plotly_chart(fig_dir, use_container_width=True)

    with col6:
        st.subheader(t("recipient_chart", lang))
        recip_counts = (
            filtered.groupby("sc_recipient_type").size()
            .reset_index(name="count").sort_values("count", ascending=False)
        )
        fig_recip = px.bar(
            recip_counts, x="sc_recipient_type", y="count",
            color="sc_recipient_type", color_discrete_sequence=px.colors.qualitative.Pastel,
            labels={"sc_recipient_type": "", "count": "# threads"},
        )
        fig_recip.update_layout(
            showlegend=False, height=360, margin=dict(l=0, r=0, t=10, b=0),
        )
        st.plotly_chart(fig_recip, use_container_width=True)

    st.markdown("---")

    # ============================================================
    # ROW 5 — Detalle estadístico (distribuciones)
    # ============================================================
    st.markdown(f"### {t('sec_stats', lang)}")
    col7, col8 = st.columns(2)

    with col7:
        st.subheader(t("chart_threads_per_ticket_dist", lang), help=t("chart_threads_per_ticket_dist_help", lang))
        tpt = (
            sc_df.groupby("ticket_id").size().reset_index(name="threads_per_ticket")
        )
        tpt["bucket"] = tpt["threads_per_ticket"].clip(upper=10).astype(str)
        tpt.loc[tpt["threads_per_ticket"] >= 10, "bucket"] = "10+"
        bucket_counts = (
            tpt["bucket"].value_counts().reset_index()
        )
        bucket_counts.columns = ["threads_per_ticket", "count"]
        # Orden numerico
        order = sorted([b for b in bucket_counts["threads_per_ticket"] if b != "10+"],
                       key=lambda x: int(x))
        if "10+" in bucket_counts["threads_per_ticket"].values:
            order.append("10+")
        bucket_counts["threads_per_ticket"] = pd.Categorical(
            bucket_counts["threads_per_ticket"], categories=order, ordered=True
        )
        bucket_counts = bucket_counts.sort_values("threads_per_ticket")
        fig_tpt = px.bar(
            bucket_counts, x="threads_per_ticket", y="count",
            color="count", color_continuous_scale="Teal",
            labels={"threads_per_ticket": "# threads", "count": "# tickets"},
        )
        fig_tpt.update_layout(
            coloraxis_showscale=False, height=340, margin=dict(l=0, r=0, t=10, b=0),
        )
        st.plotly_chart(fig_tpt, use_container_width=True)

    with col8:
        st.subheader(t("chart_msgs_per_thread_dist", lang), help=t("chart_msgs_per_thread_dist_help", lang))
        msgs_dist = filtered.dropna(subset=["total_exchanges"]).copy()
        msgs_dist["bucket"] = msgs_dist["total_exchanges"].clip(upper=10).astype(int).astype(str)
        msgs_dist.loc[msgs_dist["total_exchanges"] >= 10, "bucket"] = "10+"
        bucket_counts2 = msgs_dist["bucket"].value_counts().reset_index()
        bucket_counts2.columns = ["msgs", "count"]
        order2 = sorted([b for b in bucket_counts2["msgs"] if b != "10+"],
                        key=lambda x: int(x))
        if "10+" in bucket_counts2["msgs"].values:
            order2.append("10+")
        bucket_counts2["msgs"] = pd.Categorical(
            bucket_counts2["msgs"], categories=order2, ordered=True
        )
        bucket_counts2 = bucket_counts2.sort_values("msgs")
        fig_mpt = px.bar(
            bucket_counts2, x="msgs", y="count",
            color="count", color_continuous_scale="Purples",
            labels={"msgs": "# messages", "count": "# threads"},
        )
        fig_mpt.update_layout(
            coloraxis_showscale=False, height=340, margin=dict(l=0, r=0, t=10, b=0),
        )
        st.plotly_chart(fig_mpt, use_container_width=True)


# =========================================================================
# PAGE: P1 — OPERATIONAL HEALTH
# =========================================================================

elif page == "nav_operational":
    st.title(t("p1_title", lang))
    st.caption(t("p1_caption", lang))
    st.markdown("---")

    df = sc_df.copy()
    if sel_direction != ALL:
        df = df[df["sc_direction"] == sel_direction]
    if sel_recipient != ALL:
        df = df[df["sc_recipient_type"] == sel_recipient]
    if sel_reason != ALL:
        df = df[df["sc_reason_classification"] == sel_reason]

    # Solo para threads hacia external (donde tiene sentido medir SLA)
    df_external = df[df["sc_direction"].isin(["ria_to_external", "ria_to_client"])].copy()
    with_response = df_external.dropna(subset=["external_response_hrs"])

    # ------------------- KPIs Row 1: SLA & Response -------------------
    c1, c2, c3, c4, c5 = st.columns(5)

    sla24 = (with_response["external_response_hrs"] <= 24).mean() * 100 if len(with_response) else 0
    sla48 = (with_response["external_response_hrs"] <= 48).mean() * 100 if len(with_response) else 0
    median_resp = with_response["external_response_hrs"].median() if len(with_response) else 0
    p90_resp = with_response["external_response_hrs"].quantile(0.90) if len(with_response) else 0

    one_done = (df["total_exchanges"] <= 2).mean() * 100 if len(df) else 0
    ghost = (df_external["external_response_hrs"].isna()).mean() * 100 if len(df_external) else 0

    c1.metric(t("m_sla24", lang), f"{sla24:.0f}%", help=t("m_sla24_help", lang))
    c2.metric(t("m_sla48", lang), f"{sla48:.0f}%", help=t("m_sla48_help", lang))
    c3.metric(t("m_median", lang), f"{median_resp:.1f} h", help=t("m_median_help", lang))
    c4.metric(t("m_p90", lang), f"{p90_resp:.1f} h", help=t("m_p90_help", lang))
    c5.metric(t("m_ghost", lang), f"{ghost:.0f}%", help=t("m_ghost_help", lang))

    # ------------------- KPIs Row 2: Efficiency -------------------
    c6, c7 = st.columns(2)
    c6.metric(t("m_one_done", lang), f"{one_done:.0f}%", help=t("m_one_done_help", lang))

    # Weekday vs weekend
    if len(with_response) and "created_at" in with_response.columns:
        wr = with_response.copy()
        wr["dayofweek"] = pd.to_datetime(wr["created_at"], errors="coerce").dt.dayofweek
        weekday_avg = wr.loc[wr["dayofweek"] < 5, "external_response_hrs"].mean()
        weekend_avg = wr.loc[wr["dayofweek"] >= 5, "external_response_hrs"].mean()
        delta_txt = f"{(weekend_avg - weekday_avg):+.1f} h"
        c7.metric(
            t("m_weekday_perf", lang),
            f"{weekday_avg:.1f} h  ➜  {weekend_avg:.1f} h",
            delta=delta_txt,
            delta_color="inverse",
            help=t("m_weekday_perf_help", lang),
        )

    st.markdown("---")

    # ------------------- Aging buckets -------------------
    st.subheader(t("m_aging", lang), help=t("m_aging_help", lang))

    open_threads = df[df["state"] == "open"].copy()
    if len(open_threads) and "created_at" in open_threads.columns:
        now = pd.Timestamp.utcnow()
        open_threads["age_hours"] = (now - pd.to_datetime(open_threads["created_at"], errors="coerce", utc=True)).dt.total_seconds() / 3600
        buckets = pd.cut(
            open_threads["age_hours"],
            bins=[0, 24, 72, 168, float("inf")],
            labels=[t("bucket_lt24", lang), t("bucket_24_72", lang),
                    t("bucket_72_168", lang), t("bucket_gt168", lang)],
        )
        bucket_counts = buckets.value_counts().reindex(
            [t("bucket_lt24", lang), t("bucket_24_72", lang),
             t("bucket_72_168", lang), t("bucket_gt168", lang)],
            fill_value=0,
        ).reset_index()
        bucket_counts.columns = ["bucket", "count"]

        colors_aging = ["#2ecc71", "#f1c40f", "#e67e22", "#e74c3c"]
        fig_aging = px.bar(
            bucket_counts, x="bucket", y="count",
            color="bucket", color_discrete_sequence=colors_aging,
            labels={"bucket": "", "count": "# open threads"},
        )
        fig_aging.update_layout(
            showlegend=False,
            height=300,
            margin=dict(l=0, r=0, t=10, b=0),
        )
        st.plotly_chart(fig_aging, use_container_width=True)

    st.markdown("---")

    # ------------------- Volume time series + Heatmap day×hour -------------------
    colA, colB = st.columns(2)

    with colA:
        st.subheader(t("chart_thread_volume", lang))
        if "created_at" in df.columns:
            ts_df = df.copy()
            ts_df["date"] = pd.to_datetime(ts_df["created_at"], errors="coerce").dt.date
            ts_counts = (
                ts_df.groupby(["date", "sc_reason_classification"])
                .size().reset_index(name="count")
            )
            fig_ts = px.bar(
                ts_counts, x="date", y="count",
                color="sc_reason_classification",
                labels={"date": "", "count": "# threads", "sc_reason_classification": ""},
            )
            fig_ts.update_layout(
                height=360, margin=dict(l=0, r=0, t=10, b=0),
                legend=dict(orientation="h", y=-0.25),
            )
            st.plotly_chart(fig_ts, use_container_width=True)

    with colB:
        st.subheader(t("chart_heatmap_time", lang), help=t("chart_heatmap_time_help", lang))
        if "created_at" in df.columns:
            hm = df.copy()
            dt = pd.to_datetime(hm["created_at"], errors="coerce")
            hm["dow"] = dt.dt.dayofweek
            hm["hour"] = dt.dt.hour
            hm_pivot = (
                hm.groupby(["dow", "hour"]).size().reset_index(name="count")
                .pivot(index="dow", columns="hour", values="count")
                .fillna(0)
            )
            dow_labels = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
            if lang == "es":
                dow_labels = ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"]
            hm_pivot.index = [dow_labels[i] for i in hm_pivot.index]
            fig_hm = px.imshow(
                hm_pivot, color_continuous_scale="Blues",
                aspect="auto", labels={"color": "#"},
            )
            fig_hm.update_layout(
                height=360, margin=dict(l=0, r=0, t=10, b=0),
            )
            st.plotly_chart(fig_hm, use_container_width=True)


# =========================================================================
# PAGE: P2 — PARTNER SCORECARD
# =========================================================================

elif page == "nav_partner":
    st.title(t("p2_title", lang))
    st.caption(t("p2_caption", lang))
    st.markdown("---")

    # Solo threads hacia corresponsales
    partner_df = sc_df[sc_df["sc_recipient_type"] == "correspondent"].copy()
    if sel_reason != ALL:
        partner_df = partner_df[partner_df["sc_reason_classification"] == sel_reason]

    if partner_df.empty:
        st.info("No partner threads with current filters.")
    else:
        # Construir leaderboard por corresponsal (usa columna correspondent ya normalizada)
        agg_map = {
            "side_conv_id":           "count",
            "ticket_id":              "nunique",
            "external_response_hrs":  ["median", lambda s: s.quantile(0.9) if s.notna().any() else None],
            "total_exchanges":        "mean",
            "resolution_hrs":         "sum",
        }
        leaderboard = partner_df.groupby("correspondent").agg(agg_map)
        leaderboard.columns = ["threads", "tickets", "median_resp", "p90_resp", "avg_exch", "blocked_hrs"]

        # Métricas adicionales
        leaderboard["avg_threads_per_ticket"] = (leaderboard["threads"] / leaderboard["tickets"]).round(2)

        # SLA % y Ghost %
        for corr in leaderboard.index:
            sub = partner_df[partner_df["correspondent"] == corr]
            with_reply = sub.dropna(subset=["external_response_hrs"])
            leaderboard.loc[corr, "sla_pct"] = (
                (with_reply["external_response_hrs"] <= 24).mean() * 100 if len(with_reply) else 0
            )
            leaderboard.loc[corr, "ghost_pct"] = (
                sub["external_response_hrs"].isna().mean() * 100 if len(sub) else 0
            )

        leaderboard = leaderboard.reset_index()
        leaderboard = leaderboard[leaderboard["threads"] >= 1]  # filtrar vacíos
        leaderboard = leaderboard.sort_values("threads", ascending=False)

        # ------------------- KPIs top -------------------
        min_threads = 5
        eligible = leaderboard[leaderboard["threads"] >= min_threads].dropna(subset=["median_resp"])

        c1, c2, c3, c4 = st.columns(4)
        if not eligible.empty:
            fastest = eligible.nsmallest(1, "median_resp").iloc[0]
            slowest = eligible.nlargest(1, "median_resp").iloc[0]
            c1.metric(
                t("m_fastest_partner", lang),
                fastest["correspondent"],
                f"{fastest['median_resp']:.1f} h",
                delta_color="off",
                help=t("m_fastest_partner_help", lang),
            )
            c2.metric(
                t("m_slowest_partner", lang),
                slowest["correspondent"],
                f"{slowest['median_resp']:.1f} h",
                delta_color="off",
                help=t("m_slowest_partner_help", lang),
            )
        top_vol = leaderboard.nlargest(1, "threads").iloc[0]
        c3.metric(
            t("m_top_volume_partner", lang),
            top_vol["correspondent"],
            f"{int(top_vol['threads'])} threads",
            delta_color="off",
            help=t("m_top_volume_partner_help", lang),
        )
        c4.metric(
            t("m_total_blocked", lang),
            f"{leaderboard['blocked_hrs'].sum():,.0f} h",
            help=t("m_total_blocked_help", lang),
        )

        st.markdown("---")

        # ------------------- Leaderboard table -------------------
        st.subheader(t("table_partner_leaderboard", lang), help=t("table_partner_leaderboard_help", lang))

        display_df = leaderboard[[
            "correspondent", "tickets", "threads", "avg_threads_per_ticket",
            "median_resp", "p90_resp", "sla_pct", "avg_exch", "ghost_pct", "blocked_hrs"
        ]].copy()

        # Redondear
        display_df["median_resp"] = display_df["median_resp"].round(1)
        display_df["p90_resp"] = display_df["p90_resp"].astype(float).round(1)
        display_df["sla_pct"] = display_df["sla_pct"].round(0)
        display_df["avg_exch"] = display_df["avg_exch"].round(1)
        display_df["ghost_pct"] = display_df["ghost_pct"].round(0)
        display_df["blocked_hrs"] = display_df["blocked_hrs"].round(0)

        display_df = display_df.rename(columns={
            "correspondent":           t("col_partner_name", lang),
            "tickets":                 t("col_partner_tickets", lang),
            "threads":                 t("col_partner_threads", lang),
            "avg_threads_per_ticket":  t("col_partner_avg_threads", lang),
            "median_resp":             t("col_partner_median_resp", lang),
            "p90_resp":                t("col_partner_p90_resp", lang),
            "sla_pct":                 t("col_partner_sla_pct", lang),
            "avg_exch":                t("col_partner_avg_exch", lang),
            "ghost_pct":               t("col_partner_ghost_pct", lang),
            "blocked_hrs":             t("col_partner_blocked_hrs", lang),
        })

        st.dataframe(display_df.reset_index(drop=True), use_container_width=True, height=400)

        st.markdown("---")

        # ------------------- Heatmap Partner × Classification -------------------
        st.subheader(t("chart_partner_heatmap", lang), help=t("chart_partner_heatmap_help", lang))

        top_partners = leaderboard.nlargest(10, "threads")["correspondent"].tolist()
        hm_df = partner_df[partner_df["correspondent"].isin(top_partners)].copy()
        hm_df = hm_df.dropna(subset=["external_response_hrs"])
        if not hm_df.empty:
            pivot = hm_df.pivot_table(
                index="correspondent", columns="sc_reason_classification",
                values="external_response_hrs", aggfunc="median",
            ).fillna(0)
            fig_hm = px.imshow(
                pivot, text_auto=".1f",
                color_continuous_scale="Reds", aspect="auto",
                labels={"color": "h"},
            )
            fig_hm.update_layout(
                height=420, margin=dict(l=0, r=0, t=10, b=0),
                xaxis_tickangle=-40,
            )
            st.plotly_chart(fig_hm, use_container_width=True)

        # ------------------- Box plot distribución -------------------
        st.subheader(t("chart_partner_distribution", lang), help=t("chart_partner_distribution_help", lang))
        box_df = partner_df[partner_df["correspondent"].isin(top_partners)].dropna(subset=["external_response_hrs"])
        if not box_df.empty:
            fig_box = px.box(
                box_df, x="correspondent", y="external_response_hrs",
                points=False, color="correspondent",
                labels={"correspondent": "", "external_response_hrs": "Response (hrs)"},
            )
            fig_box.update_layout(
                showlegend=False, height=400,
                margin=dict(l=0, r=0, t=10, b=0),
                xaxis_tickangle=-35,
            )
            st.plotly_chart(fig_box, use_container_width=True)


# =========================================================================
# PAGE: P3 — CUSTOMER JOURNEY
# =========================================================================

elif page == "nav_customer":
    st.title(t("p3_title", lang))
    st.caption(t("p3_caption", lang))
    st.markdown("---")

    # Threads directos al cliente
    client_df = sc_df[sc_df["sc_recipient_type"] == "client"].copy()

    # ------------------- KPIs -------------------
    c1, c2, c3, c4 = st.columns(4)

    tickets_with_client = client_df["ticket_id"].nunique()
    total_tickets = tickets_with_client + tickets_df["ticket_id"].nunique()
    pct_with_client = (tickets_with_client / max(len(tickets_df), 1)) * 100

    # Client response rate = % client threads donde hubo al menos un reply del cliente
    with_cp_reply = client_df[client_df["total_exchanges"] > 1]
    client_response_rate = (len(with_cp_reply) / max(len(client_df), 1)) * 100

    # Silent clients = client threads con total_exchanges == 1 (solo el create)
    silent = (client_df["total_exchanges"] == 1).sum()

    # Multi-contact tickets = tickets con >1 thread al cliente
    client_per_ticket = client_df.groupby("ticket_id").size()
    multi_contact = (client_per_ticket > 1).sum()

    c1.metric(t("m_pct_tickets_client", lang),
              f"{pct_with_client:.0f}%",
              f"{tickets_with_client} / {len(tickets_df)}",
              delta_color="off",
              help=t("m_pct_tickets_client_help", lang))
    c2.metric(t("m_client_response_rate", lang),
              f"{client_response_rate:.0f}%",
              help=t("m_client_response_rate_help", lang))
    c3.metric(t("m_client_silent", lang),
              f"{int(silent)}",
              help=t("m_client_silent_help", lang))
    c4.metric(t("m_multi_contact", lang),
              f"{int(multi_contact)}",
              help=t("m_multi_contact_help", lang))

    st.markdown("---")

    # ------------------- Top reasons for contacting customers -------------------
    colA, colB = st.columns(2)

    with colA:
        st.subheader(t("chart_client_reasons", lang), help=t("chart_client_reasons_help", lang))
        reasons = (
            client_df.groupby("sc_reason_classification")
            .size().reset_index(name="count")
            .sort_values("count", ascending=True)
            .tail(12)
        )
        if not reasons.empty:
            fig_r = px.bar(
                reasons, x="count", y="sc_reason_classification",
                orientation="h", color="count",
                color_continuous_scale="Purples",
                labels={"sc_reason_classification": "", "count": "# threads"},
            )
            fig_r.update_layout(
                coloraxis_showscale=False, height=400,
                margin=dict(l=0, r=0, t=10, b=0),
            )
            st.plotly_chart(fig_r, use_container_width=True)

    with colB:
        st.subheader(t("chart_client_response_time", lang), help=t("chart_client_response_time_help", lang))
        resp_df = client_df.dropna(subset=["external_response_hrs"]).copy()
        if not resp_df.empty:
            # Cap en 168h (7 días) para que el histograma sea legible
            resp_df["response_capped"] = resp_df["external_response_hrs"].clip(upper=168)
            fig_d = px.histogram(
                resp_df, x="response_capped", nbins=30,
                labels={"response_capped": "Response (hrs, capped 168h)", "count": "# threads"},
                color_discrete_sequence=["#9b59b6"],
            )
            fig_d.update_layout(
                height=400, margin=dict(l=0, r=0, t=10, b=0),
                showlegend=False,
            )
            st.plotly_chart(fig_d, use_container_width=True)


# =========================================================================
# PAGE: BASE DE DATOS
# =========================================================================

elif page == "nav_database":
    st.title(t("title_database", lang))
    st.caption(t("caption_database", lang))

    full_df = load_full_db()

    # Aplicar mismos filtros
    db_filtered = full_df.copy()
    if sel_direction != ALL:
        db_filtered = db_filtered[db_filtered["sc_direction"] == sel_direction]
    if sel_recipient != ALL:
        db_filtered = db_filtered[db_filtered["sc_recipient_type"] == sel_recipient]
    if sel_reason != ALL:
        db_filtered = db_filtered[
            db_filtered["sc_reason_classification"] == sel_reason
        ]

    # Búsqueda por ticket ID
    search_ticket = st.text_input(
        t("search_ticket", lang), placeholder=t("search_placeholder", lang)
    )
    if search_ticket.strip():
        try:
            tid = int(search_ticket.strip())
            db_filtered = db_filtered[db_filtered["ticket_id"] == tid]
        except ValueError:
            st.warning(t("search_invalid", lang))

    # KPIs
    k1, k2, k3 = st.columns(3)
    n_tickets = db_filtered["ticket_id"].nunique()
    n_sc = db_filtered["side_conv_id"].nunique()
    n_events = db_filtered["event_id"].notna().sum()
    k1.metric(t("tickets_kpi", lang), f"{n_tickets:,}")
    k2.metric(t("threads_kpi", lang), f"{n_sc:,}")
    k3.metric(t("messages_kpi", lang), f"{n_events:,}")

    st.markdown("---")

    # Vista jerárquica: Ticket → Side Conv → Eventos
    # Orden narrativo: TICKET -> CONVERSACIÓN -> MENSAJE
    display_db_cols = [
        # --- TICKET (contexto estático) ---
        "ticket_id",
        "ticket_created",
        "ticket_status",
        "reason_raw",
        "correspondent_raw",
        "country_raw",
        "ticket_subject",
        # --- SIDE CONVERSATION (la conversación) ---
        "sc_sequence",
        "sc_subject",
        "sc_created",
        "sc_direction",
        "sc_recipient_type",
        "sc_reason_classification",
        "sc_reason_confidence",
        "external_reply_at",
        "external_response_hrs",
        "last_counterparty_reply_at",
        "resolution_hrs",
        "total_exchanges",
        "sc_state",
        # --- MENSAJE (cada intercambio) ---
        "event_sequence",
        "event_type",
        "event_created",
        "actor_name",
        "from_address",
        "to_addresses",
        "message_subject",
        "message_body",
    ]

    display_db_cols = [c for c in display_db_cols if c in db_filtered.columns]

    rename_map = {
        # Ticket
        "ticket_id":           t("col_ticket_num", lang),
        "ticket_created":      t("col_ticket_opened", lang),
        "ticket_status":       t("col_ticket_status", lang),
        "reason_raw":          t("col_ticket_reason", lang),
        "correspondent_raw":   t("col_ticket_correspondent", lang),
        "country_raw":         t("col_ticket_country", lang),
        "ticket_subject":      t("col_ticket_subject", lang),
        # Thread
        "sc_sequence":              t("col_thread_num", lang),
        "sc_subject":               t("col_thread_subject", lang),
        "sc_created":               t("col_thread_started", lang),
        "sc_direction":             t("col_thread_direction", lang),
        "sc_recipient_type":        t("col_thread_recipient_type", lang),
        "sc_reason_classification": t("col_thread_classification", lang),
        "sc_reason_confidence":     t("col_thread_confidence", lang),
        "external_reply_at":          t("col_thread_ext_reply", lang),
        "external_response_hrs":      t("col_thread_response_hrs", lang),
        "last_counterparty_reply_at": t("col_thread_last_cp_reply", lang),
        "resolution_hrs":             t("col_thread_resolution_hrs", lang),
        "total_exchanges":            t("col_thread_exchanges", lang),
        "sc_state":                   t("col_thread_state", lang),
        # Message
        "event_sequence":  t("col_msg_num", lang),
        "event_type":      t("col_msg_type", lang),
        "event_created":   t("col_msg_date", lang),
        "actor_name":      t("col_msg_actor", lang),
        "from_address":    t("col_msg_from", lang),
        "to_addresses":    t("col_msg_to", lang),
        "message_subject": t("col_msg_subject", lang),
        "message_body":    t("col_msg_body", lang),
    }

    st.dataframe(
        db_filtered[display_db_cols]
        .rename(columns=rename_map)
        .reset_index(drop=True),
        use_container_width=True,
        height=600,
    )

    # Descargar XLSX
    st.markdown("---")
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        db_filtered[display_db_cols].to_excel(
            writer, index=False, sheet_name="Ria CX Data"
        )
    st.download_button(
        label=t("download_excel", lang),
        data=buffer.getvalue(),
        file_name="ria_cx_full_database.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


# =========================================================================
# PAGE: CONCEPTS
# =========================================================================

elif page == "nav_concepts":
    st.title(t("title_concepts", lang))
    st.caption(t("caption_concepts", lang))
    st.markdown("---")

    content = CONCEPTS_ES if lang == "es" else CONCEPTS_EN
    st.markdown(content, unsafe_allow_html=False)
