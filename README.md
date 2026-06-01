# j3b3-newsletter

Pipeline semi-automatizado de la newsletter del **Observatorio del Comercio** (J3B3).

Producto editorial: **"El Pulso de la semana"** — envío semanal los lunes,
con datos del CDMGE (INE), Eurostat retail mensual y prensa sectorial filtrada.

> Documento de referencia: `templates/linea_editorial.md` y `templates/data_dictionary.md`.
> Briefing completo: `/Users/j3b3/Downloads/files/briefing-newsletter-pilot.md`.

---

## Estado actual

Pipeline en construcción. Lanzamiento público: **1 de junio de 2026**.

| Hito | Fecha objetivo |
|---|---|
| Prueba 0 | Antes del fin de semana del 16-17 de mayo |
| Prueba 1 (Núm. 1) | Lunes 19 de mayo |
| Prueba 2 (Núm. 2) | Lunes 26 de mayo |
| Prueba 3 (Núm. 3) | Lunes 2 de junio |
| Lanzamiento | 1 de junio |

---

## Instalación

```bash
cd j3b3-newsletter
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp config/.env.example config/.env
# Editar config/.env con las claves reales
```

---

## Configuración

Editar `config/.env` con:

- `ANTHROPIC_API_KEY` — clave de Anthropic con créditos para Sonnet 4.6.
- `MAILERLITE_API_KEY` — clave de administrador de MailerLite.
- `MAILERLITE_GROUP_PREVIEW` — ID del grupo de preview (una sola dirección).
- `MAILERLITE_GROUP_PILOT_INTERN` — ID del grupo piloto interno.
- `MAILERLITE_GROUP_GRATUITA` — ID del grupo público (desde lanzamiento).
- `OBSERVATORI_PATH` — ruta local al repositorio `observatori-comerc`.
- `MODO_EJECUCION` — `prueba` o `produccion`.

Editar `config/settings.yaml` para valores no sensibles (paleta, bloques, etc.).

---

## Uso

```bash
python run_newsletter.py
```

Flujo interactivo (todos los pasos requieren confirmación en terminal):

1. Detecta o pregunta la semana de envío.
2. Genera snapshot de datos en `data/semana-YYYY-MM-DD/`.
3. Genera borrador en Markdown con Sonnet 4.6.
4. Permite editar antes de continuar.
5. Compone HTML inline-safe.
6. Envía preview a `MAILERLITE_GROUP_PREVIEW`.
7. Pide confirmación explícita antes del envío real.
8. Envía al grupo destino y registra en `output/semana-YYYY-MM-DD/send_log.json`.

**Norma absoluta**: el pipeline nunca envía al grupo destino sin confirmación
escrita explícita en terminal. Doble confirmación obligatoria.

---

## Estructura del repositorio

```
j3b3-newsletter/
├── data/                       Snapshots de datos por semana (congelados)
│   └── semana-YYYY-MM-DD/
│       ├── pulso_diario.csv
│       ├── pulso_europeo.csv
│       ├── recopilacion_prensa.md
│       └── _meta.json
├── templates/
│   ├── linea_editorial.md      Línea editorial + 2 ediciones modelo (few-shot)
│   ├── data_dictionary.md      Diccionario de campos de las fuentes
│   └── email_base.html         Plantilla HTML del email
├── output/                     Archivo de ediciones publicadas
│   └── semana-YYYY-MM-DD/
│       ├── newsletter.md
│       ├── newsletter.html
│       ├── dades_origen/       Copia auditable de los datos usados
│       ├── send_log.json
│       └── metrics.json
├── scripts/
│   ├── snapshot.py             Captura de datos desde observatori-comerc
│   ├── generate.py             Llama a Sonnet 4.6 con la línea editorial
│   ├── compose.py              Markdown → HTML email-safe
│   ├── preview.py              Envía preview vía MailerLite
│   └── send.py                 Envía al grupo destino tras confirmación
├── config/
│   ├── .env                    Secretos (NO en git)
│   ├── .env.example
│   └── settings.yaml
├── run_newsletter.py           Orquestador interactivo
└── README.md
```

---

## Validación por prueba

Checklist mínimo antes de cada envío:

- [ ] Snapshot generado y verificado (lag de datos aceptable)
- [ ] Borrador revisado por humano
- [ ] Sección `### TRAZABILIDAD (no se envía)` confirma origen de cada cifra
- [ ] HTML renderizado correctamente en Gmail web y Apple Mail
- [ ] Preview recibido y comprobado por el usuario
- [ ] Confirmación explícita en terminal antes del envío real
- [ ] `send_log.json` generado tras envío
- [ ] 24-48 h después: revisar métricas (apertura, clics) en `metrics.json`

---

## Troubleshooting

Pendiente: se completa tras Prueba 0.

---

## Automatización (Nivel 3) — GitHub Actions

Desde junio 2026, el envío semanal queda programado automáticamente cada
domingo por la noche mediante una GitHub Action que:

1. Detecta el próximo lunes y el siguiente número de edición.
2. Ejecuta `snapshot → generate → compose`.
3. Crea la campaña a Brevo con `scheduledAt = lunes 08:30 CEST` (la envía Brevo,
   no el pipeline — sin intervención humana en el envío).
4. Guarda el `brevo_campaign_id` en `config/historial_editorial.json`.
5. Envía una notificación a `jordi@j3b3.com` con las instrucciones para cancelar
   si hay algo que revisar.

### Scripts

- `scripts/schedule.py` — orquestrador no-interactivo. Soporta `--dry-run` para
  simular el flujo sin tocar Brevo ni el historial.
- `scripts/cancel.py --semana YYYY-MM-DD` — cancela una campaña programada
  pasándola a draft. Brevo no la enviará.

### Workflow

`.github/workflows/newsletter-schedule.yml`:

- Cron: `0 20 * * 0` (cada domingo 22:00 CEST = 20:00 UTC).
- También se puede ejecutar manualmente desde el panel de GitHub Actions
  (`workflow_dispatch`).
- Clona `observatori-comerc` en `/tmp/observatori-comerc` para que
  `snapshot.py` pueda leer las series de datos.
- Tras el `schedule.py`, hace commit+push del `historial_editorial.json`
  actualizado para que la próxima ejecución detecte el número siguiente.

### GitHub Secrets a configurar

En https://github.com/jordi-j3b3/j3b3-newsletter → Settings → Secrets and
variables → Actions → **New repository secret**, añadir estos seis (los
valores se encuentran en el `config/.env` local):

| Secret | Origen / valor de referencia |
|---|---|
| `ANTHROPIC_API_KEY` | Clave Anthropic con créditos para Sonnet 4.6 |
| `BREVO_API_KEY` | Clave Brevo con scope de campañas + transaccional |
| `BREVO_LIST_PREVIEW_ID` | `3` |
| `BREVO_LIST_PILOT_ID` | `4` |
| `BREVO_FROM_EMAIL` | `observatorio@j3b3.com` |
| `BREVO_FROM_NAME` | `Observatorio del Comercio` |

`OBSERVATORI_PATH` **no** es secret: el workflow lo fija a `/tmp/observatori-comerc`
(la ruta del clone temporal).

### Mirror al dashboard

Tras el envío de Brevo, el contenido **no se publica automáticamente** en el
dashboard del Observatorio. Para publicarlo, ejecutar localmente (o, en su
defecto, antes del envío):

```bash
python scripts/mirror_only.py            # detecta la semana más reciente
python scripts/mirror_only.py --setmana 2026-06-08 --numero 4
```

`mirror_only.py` es idempotente: si la edición ya está publicada, no hace nada.

### Cancelar antes del envío

Si la notificación del domingo revela un problema, antes del lunes 08:00:

```bash
python scripts/cancel.py --semana 2026-06-08
```

La campaña pasa a draft en Brevo y se anota `cancelled_at_utc` en el historial.
Aviso: si el mirror al dashboard ya se hizo, hay que revertir manualmente
el commit correspondiente en `observatori-comerc`.

### Dry-run de validación

Antes de activar el cron, validar el flujo sin tocar Brevo:

```bash
python scripts/schedule.py --dry-run
python scripts/schedule.py --dry-run --semana 2026-06-08 --numero 4
```

Muestra el payload simulado que se enviaría a `/v3/emailCampaigns` y el
contenido de la notificación, sin crear la campaña ni modificar el historial.
