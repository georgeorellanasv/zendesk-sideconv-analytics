"""
Internacionalización — traducciones para el dashboard.

Uso:
    from src.i18n import t
    lang = "en" or "es"
    label = t("filters", lang)
"""

TRANSLATIONS: dict[str, dict[str, str]] = {
    # ---------- Navigation ----------
    "nav_analytics":   {"en": "Summary",             "es": "Resumen"},
    "nav_operational": {"en": "Operational Health",  "es": "Salud Operacional"},
    "nav_partner":     {"en": "Partner Scorecard",   "es": "Scorecard de Partners"},
    "nav_customer":    {"en": "Customer Journey",    "es": "Jornada del Cliente"},
    "nav_database":    {"en": "Database",            "es": "Base de Datos"},
    "nav_concepts":    {"en": "Concepts",            "es": "Conceptos"},
    "page_label":      {"en": "Page",                "es": "Página"},
    "language":        {"en": "Language",            "es": "Idioma"},

    # ---------- Filters ----------
    "filters":            {"en": "Filters",              "es": "Filtros"},
    "thread_direction":   {"en": "Thread Direction",     "es": "Dirección del Thread"},
    "recipient_type":     {"en": "Recipient Type",       "es": "Tipo de Destinatario"},
    "classification":     {"en": "Classification",       "es": "Clasificación"},
    "ticket_status_filter":{"en": "Ticket Status",         "es": "Estado del Ticket"},
    "correspondent_filter":{"en": "Correspondent",         "es": "Corresponsal"},
    "ticket_id_filter":    {"en": "Drill by Ticket ID",    "es": "Drill por Ticket ID"},
    "ticket_id_placeholder":{"en": "e.g. 22525756 (empty = all)", "es": "Ej: 22525756 (vacío = todos)"},
    "active_filters":     {"en": "Active filters",         "es": "Filtros activos"},
    "clear_filters":      {"en": "Clear all filters",      "es": "Limpiar filtros"},
    "all":                {"en": "All",                   "es": "Todos"},

    # ---------- KPIs ----------
    "total_tickets":       {"en": "Total tickets",        "es": "Tickets totales"},
    "total_threads":       {"en": "Total threads",        "es": "Threads totales"},
    "tickets_with_threads":{"en": "Tickets with threads", "es": "Tickets con threads"},
    "threads_filter":      {"en": "Threads (filtered)",   "es": "Threads (filtro)"},
    "open_filter":         {"en": "Open (filtered)",      "es": "Abiertos (filtro)"},
    "tickets_kpi":         {"en": "Tickets",              "es": "Tickets"},
    "threads_kpi":         {"en": "Threads",              "es": "Threads"},
    "messages_kpi":        {"en": "Messages",             "es": "Mensajes"},

    # ---------- Section titles ----------
    "title_analytics":         {"en": "Ria CX — Summary",                          "es": "Ria CX — Resumen"},
    "caption_analytics":       {"en": "Overview at Ticket, Thread and Message level", "es": "Panorama a nivel Ticket, Thread y Mensaje"},

    # Hierarchy KPIs
    "kpi_avg_threads_per_ticket":      {"en": "Avg Threads / Ticket",      "es": "Avg Threads / Ticket"},
    "kpi_avg_threads_per_ticket_help": {"en": "Average number of threads opened per ticket. Indicator of case complexity.",
                                        "es": "Promedio de threads abiertos por ticket. Indicador de complejidad del caso."},
    "kpi_avg_msgs_per_thread":         {"en": "Avg Msgs / Thread",          "es": "Avg Mensajes / Thread"},
    "kpi_avg_msgs_per_thread_help":    {"en": "Average number of messages exchanged per thread. Higher = more back-and-forth.",
                                        "es": "Promedio de mensajes intercambiados por thread. Más alto = más ping-pong."},
    "kpi_total_messages":              {"en": "Total messages",             "es": "Mensajes totales"},
    "kpi_total_messages_help":         {"en": "Total individual messages (events) across all threads.",
                                        "es": "Total de mensajes individuales (eventos) en todos los threads."},
    "kpi_total_tickets_help":          {"en": "Total tickets extracted from the US Care view.",
                                        "es": "Tickets totales extraídos de la vista US Care."},
    "kpi_total_threads_help":          {"en": "Total side conversations (threads) across all tickets.",
                                        "es": "Total de side conversations (threads) en todos los tickets."},

    # Section titles
    "sec_reasons":          {"en": "Reasons by hierarchy level",  "es": "Razones por nivel de jerarquía"},
    "sec_correspondents":   {"en": "Correspondents overview",      "es": "Panorama de corresponsales"},
    "sec_direction":        {"en": "Direction & Recipient",        "es": "Dirección y Destinatario"},
    "sec_stats":            {"en": "Statistical detail",           "es": "Detalle estadístico"},

    "chart_tickets_by_reason":      {"en": "Tickets by Reason (ticket-level)", "es": "Tickets por Razón (nivel ticket)"},
    "chart_tickets_by_reason_help": {"en": "Distribution of tickets by the Zendesk Reason field (set by the agent). Reflects the primary contact reason.",
                                     "es": "Distribución de tickets por el campo Reason de Zendesk (fijado por el agente). Refleja la razón primaria de contacto."},
    "chart_threads_by_class":       {"en": "Threads by Classification (thread-level)", "es": "Threads por Clasificación (nivel thread)"},
    "chart_threads_by_class_help":  {"en": "Distribution of threads by the classification our system derives from subject + body. Reflects what we actually do for each case.",
                                     "es": "Distribución de threads por la clasificación que nuestro sistema deriva de subject + body. Refleja lo que realmente hacemos en cada caso."},

    "chart_top_corr_volume":        {"en": "Top correspondents by volume",  "es": "Top corresponsales por volumen"},
    "chart_top_corr_volume_help":   {"en": "Partners we communicate with most often in the analyzed period.",
                                     "es": "Partners con los que más nos comunicamos en el período analizado."},
    "chart_corr_response":          {"en": "Response time by correspondent (median)", "es": "Tiempo de respuesta por corresponsal (mediana)"},
    "chart_corr_response_help":     {"en": "Median first-reply time per correspondent. Sorted fastest-to-slowest among partners with ≥3 threads.",
                                     "es": "Tiempo mediano al primer reply por corresponsal. Ordenado del más rápido al más lento, entre partners con ≥3 threads."},

    "chart_threads_per_ticket_dist":      {"en": "Threads per ticket (distribution)", "es": "Threads por ticket (distribución)"},
    "chart_threads_per_ticket_dist_help": {"en": "How many threads each ticket generates. Most tickets cluster at 1-2; outliers indicate complex cases.",
                                           "es": "Cuántos threads genera cada ticket. La mayoría se concentran en 1-2; los outliers indican casos complejos."},
    "chart_msgs_per_thread_dist":      {"en": "Messages per thread (distribution)", "es": "Mensajes por thread (distribución)"},
    "chart_msgs_per_thread_dist_help": {"en": "How many messages each thread contains. Longer threads indicate heavier back-and-forth.",
                                        "es": "Cuántos mensajes tiene cada thread. Los más largos indican más ping-pong."},

    # ---------- Automation (Sprint 1a) ----------
    "col_thread_is_automated":       {"en": "Thread Is Automated",    "es": "Thread Automatizado"},
    "col_thread_automation_signal":  {"en": "Automation Signal",      "es": "Señal de Automatización"},
    "m_pct_automated":               {"en": "% Automated threads",    "es": "% Threads Automatizados"},
    "m_pct_automated_help":          {"en": "Percentage of threads heuristically classified as automated (created by triggers, mailboxes, or templates).",
                                      "es": "Porcentaje de threads clasificados heurísticamente como automatizados (creados por triggers, buzones o templates)."},
    "m_automated_manual_split":      {"en": "Automated vs Manual",    "es": "Automatizados vs Manuales"},
    "m_automated_manual_split_help": {"en": "Breakdown of manual (human-initiated) vs automated (triggered) threads.",
                                      "es": "Desglose de threads manuales (iniciados por humano) vs automatizados (por trigger)."},

    # ---------- Reason history (Sprint 2) ----------
    "col_ticket_reason_initial":      {"en": "Ticket Reason Initial",      "es": "Razón Inicial del Ticket"},
    "col_ticket_reason_last":         {"en": "Ticket Reason Last",         "es": "Razón Última del Ticket"},
    "col_ticket_reason_changes_count":{"en": "Ticket Reason Changes",      "es": "Cambios de Razón"},
    "col_ticket_reason_history":      {"en": "Ticket Reason History",      "es": "Historial de Razón"},
    "m_pct_tickets_reason_changed":       {"en": "Tickets with reason changed", "es": "Tickets con razón cambiada"},
    "m_pct_tickets_reason_changed_help":  {"en": "Percentage of tickets whose Reason for Contact was changed at least once by the agent.",
                                           "es": "Porcentaje de tickets cuya Razón de Contacto fue cambiada al menos una vez por el agente."},
    "title_database":          {"en": "Complete Database",                         "es": "Base de Datos Completa"},
    "caption_database":        {"en": "Tickets + Threads + Messages — ordered by Ticket ID", "es": "Tickets + Threads + Mensajes — ordenados por Ticket ID"},
    "title_concepts":          {"en": "Concepts & Data Dictionary",                "es": "Conceptos y Diccionario de Datos"},
    "caption_concepts":        {"en": "Understand the hierarchy and each column",  "es": "Entiende la jerarquía y cada columna"},

    "threads_by_reason":       {"en": "Threads by reason",        "es": "Threads por razón"},
    "by_direction":            {"en": "By direction",             "es": "Por dirección"},
    "top_correspondents":      {"en": "Top correspondents",       "es": "Top corresponsales"},
    "ticket_reason_l1":        {"en": "Ticket reason (L1)",       "es": "Razón del ticket (L1)"},
    "direction_vs_reason":     {"en": "Direction × Reason (heatmap)", "es": "Dirección × Razón (heatmap)"},
    "recipient_chart":         {"en": "Recipient type",           "es": "Tipo de destinatario"},
    "detail_table":            {"en": "Thread detail",            "es": "Detalle de threads"},
    "search_ticket":           {"en": "Search by Ticket ID",      "es": "Buscar por Ticket ID"},
    "search_placeholder":      {"en": "e.g., 22034431",           "es": "Ej: 22034431"},
    "search_invalid":          {"en": "Enter a valid ticket number.", "es": "Ingresa un número de ticket válido."},
    "no_correspondents":       {"en": "No threads to correspondents with current filters.", "es": "Sin threads hacia corresponsales con los filtros actuales."},
    "records":                 {"en": "records",                  "es": "registros"},
    "download_excel":          {"en": "Download as Excel (.xlsx)","es": "Descargar como Excel (.xlsx)"},

    # ---------- Column headers (dashboard) ----------
    "col_ticket_num":           {"en": "Ticket #",              "es": "Ticket #"},
    "col_ticket_opened":        {"en": "Ticket Opened",         "es": "Ticket Abierto"},
    "col_ticket_status":        {"en": "Ticket Status",         "es": "Estado del Ticket"},
    "col_ticket_reason":        {"en": "Ticket Reason",         "es": "Razón del Ticket"},
    "col_ticket_correspondent": {"en": "Ticket Correspondent",  "es": "Corresponsal del Ticket"},
    "col_ticket_country":       {"en": "Ticket Country",        "es": "País del Ticket"},
    "col_ticket_subject":       {"en": "Ticket Subject",        "es": "Asunto del Ticket"},
    "col_ticket_updated":       {"en": "Ticket Updated",        "es": "Ticket Actualizado"},
    "col_ticket_product":       {"en": "Ticket Product",        "es": "Producto del Ticket"},
    "col_ticket_side_conv_count":{"en": "Ticket Thread Count",   "es": "Total Threads del Ticket"},
    "col_msg_actor_email":      {"en": "Msg Actor Email",       "es": "Email del Remitente"},

    "col_thread_num":            {"en": "Thread #",              "es": "Thread #"},
    "col_thread_subject":        {"en": "Thread Subject",        "es": "Asunto del Thread"},
    "col_thread_started":        {"en": "Thread Started",        "es": "Thread Iniciado"},
    "col_thread_direction":      {"en": "Thread Direction",      "es": "Dirección del Thread"},
    "col_thread_recipient_type": {"en": "Thread Recipient Type", "es": "Tipo Destinatario del Thread"},
    "col_thread_classification": {"en": "Thread Classification", "es": "Clasificación del Thread"},
    "col_thread_confidence":     {"en": "Thread Confidence",     "es": "Confianza de Clasificación"},
    "col_thread_ext_reply":      {"en": "Thread External Reply",          "es": "Respuesta Externa del Thread"},
    "col_thread_response_hrs":   {"en": "Thread Response (hrs)",          "es": "Respuesta del Thread (hrs)"},
    "col_thread_last_cp_reply":  {"en": "Thread Last Counterparty Reply", "es": "Último Reply de la Contraparte"},
    "col_thread_resolution_hrs": {"en": "Thread Resolution (hrs)",        "es": "Resolución del Thread (hrs)"},
    "col_thread_exchanges":      {"en": "Thread Exchanges",               "es": "Intercambios del Thread"},
    "col_thread_state":          {"en": "Thread State",                   "es": "Estado del Thread"},

    "col_msg_num":      {"en": "Msg #",       "es": "Msg #"},
    "col_msg_type":     {"en": "Msg Type",    "es": "Tipo de Mensaje"},
    "col_msg_date":     {"en": "Msg Date",    "es": "Fecha del Mensaje"},
    "col_msg_actor":    {"en": "Msg Actor",   "es": "Remitente del Mensaje"},
    "col_msg_from":     {"en": "Msg From",    "es": "Mensaje De"},
    "col_msg_to":       {"en": "Msg To",      "es": "Mensaje Para"},
    "col_msg_subject":  {"en": "Msg Subject", "es": "Asunto del Mensaje"},
    "col_msg_body":     {"en": "Msg Body",    "es": "Cuerpo del Mensaje"},

    # ======================================================================
    # P1 — OPERATIONAL HEALTH
    # ======================================================================
    "p1_title":          {"en": "Operational Health",                                        "es": "Salud Operacional"},
    "p1_caption":        {"en": "Overall health of the side-conversation ecosystem",        "es": "Salud general del ecosistema de side conversations"},

    # Metric: SLA 24h
    "m_sla24":           {"en": "% within 24h SLA",                                          "es": "% dentro de SLA 24h"},
    "m_sla24_help":      {"en": "Percentage of threads where the counterparty replied within 24 hours. Excludes threads with no reply.",
                          "es": "Porcentaje de threads donde la contraparte respondió dentro de 24 horas. Excluye threads sin respuesta."},
    "m_sla48":           {"en": "% within 48h SLA",                                          "es": "% dentro de SLA 48h"},
    "m_sla48_help":      {"en": "Percentage of threads where the counterparty replied within 48 hours.",
                          "es": "Porcentaje de threads donde la contraparte respondió dentro de 48 horas."},

    # Metric: P90
    "m_p90":             {"en": "P90 Response",                                              "es": "P90 Respuesta"},
    "m_p90_help":        {"en": "90% of threads get a first reply within this time. Reveals the long-tail outliers that averages hide.",
                          "es": "El 90% de los threads reciben primer reply dentro de este tiempo. Revela los outliers de cola larga que los promedios esconden."},
    "m_median":          {"en": "Median Response",                                           "es": "Respuesta Mediana"},
    "m_median_help":     {"en": "Median (P50) first-reply time. Not affected by outliers, unlike the average.",
                          "es": "Mediana (P50) del tiempo al primer reply. No se ve afectada por outliers, a diferencia del promedio."},

    # Metric: One-and-done
    "m_one_done":        {"en": "One-and-done rate",                                         "es": "Resuelto en un intercambio"},
    "m_one_done_help":   {"en": "% of threads resolved in ≤2 messages (create + 1 reply). Indicator of efficiency — no back-and-forth needed.",
                          "es": "% de threads resueltos en ≤2 mensajes (create + 1 reply). Indicador de eficiencia — sin ping-pong."},

    # Metric: Ghost rate
    "m_ghost":           {"en": "Ghost rate",                                                "es": "Tasa de silencio"},
    "m_ghost_help":      {"en": "% of threads to external where counterparty NEVER replied. High = communication breakdown.",
                          "es": "% de threads externos donde la contraparte NUNCA respondió. Alta = colapso de comunicación."},

    # Aging buckets
    "m_aging":           {"en": "Open threads by age",                                       "es": "Threads abiertos por edad"},
    "m_aging_help":      {"en": "Open threads bucketed by hours since creation. Anything over 72h should be escalated.",
                          "es": "Threads abiertos agrupados por horas desde creación. Todo > 72h debería escalarse."},
    "bucket_lt24":       {"en": "< 24h",                                                     "es": "< 24h"},
    "bucket_24_72":      {"en": "24-72h",                                                    "es": "24-72h"},
    "bucket_72_168":     {"en": "3-7 days",                                                  "es": "3-7 días"},
    "bucket_gt168":      {"en": "> 7 days",                                                  "es": "> 7 días"},

    # Weekday vs weekend
    "m_weekday_perf":    {"en": "Weekday vs Weekend",                                        "es": "Entre Semana vs Fin de Semana"},
    "m_weekday_perf_help":{"en": "Comparison of avg response time on weekdays vs weekends. Helps detect if partners slow down on weekends.",
                          "es": "Comparación del tiempo promedio de respuesta en días hábiles vs fines de semana. Detecta si los partners se ralentizan."},

    # Volume time series
    "chart_thread_volume": {"en": "Thread volume by day",                                    "es": "Volumen de threads por día"},
    "chart_heatmap_time":  {"en": "Thread creation — Day × Hour",                           "es": "Creación de threads — Día × Hora"},
    "chart_heatmap_time_help": {"en": "When threads are typically created. Peaks indicate workload concentration windows.",
                               "es": "Cuándo se crean los threads típicamente. Los picos indican ventanas de concentración de carga."},

    # ======================================================================
    # P2 — PARTNER SCORECARD
    # ======================================================================
    "p2_title":          {"en": "Partner Scorecard",                                          "es": "Scorecard de Partners"},
    "p2_caption":        {"en": "Correspondent-level performance analysis (SLA, volume, complexity)", "es": "Análisis de desempeño por corresponsal (SLA, volumen, complejidad)"},

    "m_fastest_partner":     {"en": "Fastest partner",      "es": "Partner más rápido"},
    "m_fastest_partner_help":{"en": "Correspondent with the best average first-reply time (minimum 5 threads).", "es": "Corresponsal con el mejor tiempo promedio al primer reply (mínimo 5 threads)."},
    "m_slowest_partner":     {"en": "Slowest partner",      "es": "Partner más lento"},
    "m_slowest_partner_help":{"en": "Correspondent with the worst average first-reply time (minimum 5 threads).", "es": "Corresponsal con el peor tiempo promedio al primer reply (mínimo 5 threads)."},
    "m_top_volume_partner":  {"en": "Highest volume",       "es": "Mayor volumen"},
    "m_top_volume_partner_help":{"en": "Correspondent we exchange the most threads with.",    "es": "Corresponsal con el que intercambiamos más threads."},
    "m_total_blocked":       {"en": "Total blocked hours",  "es": "Horas totales bloqueadas"},
    "m_total_blocked_help":  {"en": "Sum of resolution_hrs across all correspondent threads — cumulative time waiting on partners.",
                              "es": "Suma de resolution_hrs de todos los threads con corresponsales — tiempo acumulado esperando respuesta de partners."},

    "table_partner_leaderboard":     {"en": "Partner leaderboard",  "es": "Leaderboard de partners"},
    "table_partner_leaderboard_help":{"en": "Per-partner scorecard showing volume and performance metrics. Click columns to sort.",
                                      "es": "Scorecard por partner con métricas de volumen y desempeño. Ordena por columna haciendo clic."},

    "col_partner_name":        {"en": "Partner",           "es": "Partner"},
    "col_partner_tickets":     {"en": "# Tickets",         "es": "# Tickets"},
    "col_partner_threads":     {"en": "# Threads",         "es": "# Threads"},
    "col_partner_avg_threads": {"en": "Avg Threads/Ticket","es": "Avg Threads/Ticket"},
    "col_partner_median_resp": {"en": "Median 1st Reply",  "es": "Mediana 1er Reply"},
    "col_partner_p90_resp":    {"en": "P90 1st Reply",     "es": "P90 1er Reply"},
    "col_partner_sla_pct":     {"en": "% SLA 24h",         "es": "% SLA 24h"},
    "col_partner_avg_exch":    {"en": "Avg Exchanges",     "es": "Avg Intercambios"},
    "col_partner_ghost_pct":   {"en": "% Ghosted",         "es": "% Ghosted"},
    "col_partner_blocked_hrs": {"en": "Blocked hrs",       "es": "Horas Bloqueadas"},

    "chart_partner_heatmap":     {"en": "Response time by Partner × Classification",
                                  "es": "Tiempo de respuesta por Partner × Clasificación"},
    "chart_partner_heatmap_help":{"en": "Heatmap showing median response time (hrs) for each partner and request type. Darker = slower.",
                                  "es": "Heatmap mostrando tiempo mediano de respuesta (hrs) por partner y tipo de solicitud. Más oscuro = más lento."},

    "chart_partner_distribution":     {"en": "Response time distribution (top partners)",
                                       "es": "Distribución de tiempos de respuesta (top partners)"},
    "chart_partner_distribution_help":{"en": "Box plot showing response time distribution per partner. Wider = less consistent.",
                                       "es": "Box plot de distribución de tiempos por partner. Más ancho = menos consistente."},

    # ======================================================================
    # P3 — CUSTOMER JOURNEY
    # ======================================================================
    "p3_title":          {"en": "Customer Journey",                                          "es": "Jornada del Cliente"},
    "p3_caption":        {"en": "How often we contact customers and what we ask them",      "es": "Qué tan seguido contactamos clientes y qué les pedimos"},

    "m_pct_tickets_client":      {"en": "Tickets with client contact",                      "es": "Tickets con contacto al cliente"},
    "m_pct_tickets_client_help": {"en": "% of tickets that generated at least one thread directly to the customer. Lower is better — means we resolve without bothering them.",
                                  "es": "% de tickets que generaron al menos un thread directo al cliente. Más bajo es mejor — significa que resolvemos sin molestarlos."},

    "m_client_response_rate":      {"en": "Client response rate",                           "es": "Tasa de respuesta del cliente"},
    "m_client_response_rate_help": {"en": "% of client threads where the customer replied. Low rate suggests we're asking at bad times or unclear requests.",
                                    "es": "% de threads al cliente donde el cliente respondió. Tasa baja sugiere mala hora o solicitudes poco claras."},

    "m_client_silent":      {"en": "Silent clients",                                        "es": "Clientes silenciosos"},
    "m_client_silent_help": {"en": "# client threads with zero reply from the customer. Potential abandonment or lost customers.",
                             "es": "# threads al cliente con cero respuesta del cliente. Potencial abandono o clientes perdidos."},

    "m_multi_contact":      {"en": "Multi-contact tickets",                                 "es": "Tickets con multi-contacto"},
    "m_multi_contact_help": {"en": "# of tickets where we contacted the customer more than once. Friction indicator — we should have asked everything at once.",
                             "es": "# de tickets donde contactamos al cliente más de una vez. Indicador de fricción — debimos preguntar todo de una vez."},

    "chart_client_reasons":     {"en": "Top reasons for contacting customers",
                                 "es": "Top razones para contactar clientes"},
    "chart_client_reasons_help":{"en": "What we most often ask customers. Each of these is a candidate for automation or process improvement.",
                                 "es": "Lo que más le pedimos a los clientes. Cada uno es candidato a automatización o mejora de proceso."},

    "chart_client_response_time":     {"en": "Client response time distribution",
                                       "es": "Distribución del tiempo de respuesta del cliente"},
    "chart_client_response_time_help":{"en": "How quickly customers reply to our outreach. Useful for setting realistic follow-up cadences.",
                                       "es": "Qué tan rápido responden los clientes a nuestros contactos. Útil para definir cadencias de follow-up realistas."},
}


def t(key: str, lang: str = "es") -> str:
    """Return the translation of `key` in the given language, or the key itself if missing."""
    entry = TRANSLATIONS.get(key)
    if not entry:
        return key
    return entry.get(lang, entry.get("es", key))
