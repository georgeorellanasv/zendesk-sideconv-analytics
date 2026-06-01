# XE Compliance / Dandelion TRG — Trigger Removal Bug

## Contexto

**Periodo del bug:** 2025 (todo el año)  
**Fix aplicado:** abril 2026  
**Equipo afectado:** Dandelion TRG → Xe - Compliance - Consumer

### ¿Qué pasaba?

Los agentes de Dandelion TRG aplicaban la macro **`dwp_stg_to_xe_compliance`**
(`Action::Assign to team::Xe Compliance`) para escalar tickets RFI a XE Compliance
(Consumer). Sin embargo, un trigger de XE detectaba los tickets recién llegados y
los removía automáticamente hacia Xe - Operations - EMEA, impidiendo que llegaran
al equipo correcto.

---

## IDs de grupos relevantes

| Grupo | ID |
|---|---|
| Dandelion TRG | `13019682334481` |
| Xe - Compliance - Consumer | `6750164830737` |
| Xe - Operations - EMEA | `1900000302173` |
| Xe - Care | `360006758518` |
| Xe - Operations | `360009716097` |
| Xe - Operations - EMEA | `360009701858` |

## Trigger causante del bug

| Campo | Valor |
|---|---|
| Nombre | `Xe: EMEA - Reopen ticket - Trade Volume less than 20k - less than 2 days` |
| ID | `11187241283345` |
| Acción | Mueve el ticket de `Xe - Compliance - Consumer` → `Xe - Operations - EMEA` |
| Via channel (en audits) | `rule` |

El trigger disparaba cuando un ticket llegaba a XE Compliance Consumer con bajo
volumen de transacciones (< 20k) y menos de 2 días de antigüedad, condiciones que
cumplían los tickets de Dandelion TRG por diseño.

---

## Análisis de 3 días (prueba — 10–12 marzo 2025)

Script: `scripts/xe_compliance_analysis.py`  
Reporte: `reports/xe_compliance_2025-03-10_2025-03-13.json`

| Métrica | Valor |
|---|---|
| Tickets en Dandelion TRG creados en esos 3 días | 182 |
| Llegaron a Xe - Compliance - Consumer | 11 (6%) |
| Afectados por el trigger-removal bug | 1 (9% de los que llegaron) |

**Ticket de ejemplo afectado:** `#14333831`  
Asunto: "Xe Money Transfer UK1944817276 // P14962743"

Timeline del caso:
1. `2025-03-11 16:26` — Agente asigna a XE Compliance Consumer (via web/macro)
2. `2025-03-13 17:05` — **Trigger** lo mueve a Xe Operations EMEA (bug)
3. `2025-03-13 18:12` — Agente corrige manualmente de vuelta a XE Compliance
4. Bouncing manual en grupos XE hasta el 2025-03-19
5. `2025-03-19 20:17` — Termina en Dandelion TRG

---

## Cómo correr el análisis

```powershell
# Desde la raíz del proyecto

# Solo ver grupos disponibles
python scripts/xe_compliance_analysis.py --discover-only

# 3 días específicos (con IDs ya conocidos — más rápido)
python scripts/xe_compliance_analysis.py `
  --start 2025-03-10 --end 2025-03-13 `
  --dandelion-id 13019682334481 `
  --xe-id 6750164830737

# Cualquier otro rango
python scripts/xe_compliance_analysis.py --start 2025-01-01 --end 2025-04-01
```

El reporte JSON se guarda en `reports/xe_compliance_<start>_<end>.json`.

---

## Limitaciones conocidas del script

1. **La búsqueda filtra por `group_id` actual = Dandelion TRG.** Tickets afectados
   que terminaron en otro grupo permanentemente no aparecen en los conteos.
   Para análisis completo: quitar el filtro `group_id` y buscar en todo el rango de fechas.

2. **El nombre de la macro no aparece en los audits.** Zendesk expone `via.channel = "web"`
   pero no el nombre de la macro aplicada. La asignación a XE Compliance se confirma
   por el cambio de `group_id`, no por el nombre de la macro.

3. **Para encontrar todos los afectados:** buscar tickets que alguna vez pasaron por
   XE Compliance Consumer y luego fueron movidos por el trigger ID `11187241283345`.

---

## Próximos pasos sugeridos

- Ampliar análisis a todo 2025 (sliceado por mes para no superar el cap de 1000 de Search API)
- Cruzar con `reason_raw` para confirmar que eran tickets RFI
- Estimar el total de tickets que nunca llegaron a XE Compliance por este bug
