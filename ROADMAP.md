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

- **Banco de España RSS: feed trencat** · Prioridad: baixa
  Verificat 2026-06-16: tot el domini `bde.es` redirigeix a `app.bde.es` que retorna
  404 per a qualsevol URL RSS (`/rss/es/rssNovedades.xml`, etc.). Cobertura actual:
  Google News amb query BCE/macro (`google_bce_macro` feed afegit 2026-06-16).
  Revisar periòdicament si BdE restaura el feed RSS directe a `bde.es`.

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

- **Pages: migrar a desplegament Actions-based amb `concurrency` group** · Prioridad: baixa
  Ara el site (pulso.j3b3.com) usa GitHub Pages **legacy branch-based** (source
  `main` /docs), que dispara el workflow gestionat "pages build and deployment"
  a cada push sense cap control de concurrència. Amb diversos push seguits (p.ex.
  3 en 35 min el 2026-07-05), els deploys es solapen i el darrer falla amb
  "Deployment failed, try again later." (build OK, deploy fallat en ~10s). El fix
  puntual és re-disparar el build (`gh api -X POST repos/.../pages/builds`), però
  la solució permanent és migrar a **Pages Actions-based**: un workflow propi al
  repo amb `actions/upload-pages-artifact` + `actions/deploy-pages` i un bloc
  `concurrency: { group: "pages", cancel-in-progress: true }`, que serialitza els
  deploys i cancel·la els obsolets en lloc de fer-los xocar. No és urgent (les
  fallades són transitòries i sense impacte de contingut), però elimina l'error
  recurrent per pushos ràpids seguits.
