# Roadmap — j3b3-newsletter

Tareas pendientes ordenadas por momento de ejecución.

## Post-lanzamiento (después del 1 de junio de 2026)

- **Resolución automática de URLs de Google News** · Prioridad: media
  En el pipeline de `scripts/snapshot.py` o `scripts/generate.py`, añadir un paso
  que resuelva los URLs `news.google.com/rss/articles/...` al URL directo del medio
  original durante el snapshot o la generación, para evitar este problema en
  futuras ediciones.
  Motivo: los URLs de Google News caducan, generan muro de consentimiento en la UE
  y pueden romperse con el link-rewriting de Brevo.
  Si no se puede resolver el URL directo, omitir la línea `[Ver noticia](...)` de
  esa noticia (degradación elegante) en vez de publicar un enlace de Google News.
  Stopgap aplicado en Núm. 3 (2026-06-01): se eliminó manualmente el enlace de
  Google News de la noticia 1 (El Economista); las noticias de Distribución
  Actualidad mantienen sus URLs directos.

- **Bloque 3: aprovechar todos los días disponibles del CDMGE, no solo los días clave** · Prioridad: media
  El bloque 3 ("Datos de la semana") debe usar todos los días disponibles del CDMGE
  hasta la fecha de generación, no solo los días clave preseleccionados (revisar
  `slice_cdmge_dias_clave` en `scripts/generate.py` y/o la captura en `snapshot.py`).
  Regla: si el mes en curso tiene 15 días de datos, el gráfico debe mostrar ~5 puntos
  representativos (días 3, 6, 9, 12, 15), no 2.
  Motivo / detectado en Núm. 7 (2026-06-15): el bloque mostraba solo los días 14 y 15
  ("dos lecturas") cuando había 15 días disponibles en la serie, dando una falsa
  sensación de serie provisional y volátil cuando en realidad había datos suficientes.

- **Feeds de petit comerç: verificar RSS directes** · Prioridad: baixa
  Tres feeds afegits via Google News el 2026-06-16 que cal migrar a feed directe si
  el domini és accessible sense anti-bot (HTTP 200):
  - **ACES** (Asociación Española de Centros y Parques Comerciales): domini oficial
    no identificat (aces.es és salut, acescentroscomerciales.es no resol). Investigar
    el domini corporatiu real de ACES i provar `/feed/`.
  - **Comerç Barcelona** (Consorci de Comerç de Barcelona): provar
    `https://comerc.barcelona/feed/` (WordPress probable). Si 200, substituir el
    feed Google News `google_comerc_barcelona` a `observatori-comerc/modules/press.py`.
  - **Comertia** (Associació de Franquícia i Retail Catalunya): provar
    `https://comertia.com/feed/`. Si 200, substituir `google_comertia`.
  Tots tres estan actius via Google News ara mateix. La migració a feed directe
  redueix dependència de Google i millora la latència de les entrades.
