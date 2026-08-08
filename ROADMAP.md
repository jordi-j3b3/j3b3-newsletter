# Roadmap — j3b3-newsletter

Tareas pendientes ordenadas por momento de ejecución.

## Post-lanzamiento (después del 1 de junio de 2026)

- **Sincronització única dels tres punts de sortida (Brevo + mirall + web)** · Prioridad: alta
  Avui una edició acaba en **tres llocs independents** generats cadascun amb la
  seva pròpia comanda a partir del mateix `output/semana-X/newsletter.md`: la
  campanya de Brevo (contingut pujat via `crea_campanya_programada()` a
  `schedule.py`), el mirall del dashboard (`mirror_to_dashboard()` a
  `scripts/mirror.py`, cap a `observatori-comerc/data/newsletter/semana-X.md`)
  i la web estàtica (`scripts/publish_web.py`, cap a `docs/pulso/num-N.html`).
  Cap dels tres es torna a disparar automàticament quan es corregeix el
  contingut després de la generació inicial — cal fer-ho manualment un per un.
  Ja ha causat el mateix patró d'incident tres vegades: Núm. 10 (2026-07-06,
  mirall no regenerat després de re-generar l'edició), Núm. 12 (2026-07-20,
  mirall i web amb el contingut de la campanya cancel·lada) i la correcció
  del Núm. 14 (2026-08-02, contingut afegit al Bloc 1 després que el cron
  automàtic ja hagués publicat als tres llocs amb la versió incompleta).
  Proposta: un únic punt d'entrada (p.ex. `scripts/resync.py --semana X
  --numero N`) que agafi `output/semana-X/newsletter.md` com a font única de
  veritat i actualitzi els tres destins en una sola crida — PUT del
  `htmlContent` a la campanya de Brevo existent (sense tocar `scheduledAt`),
  `mirror_to_dashboard()` i `publish_web.py` — de manera que una correcció
  d'última hora sigui una sola comanda en lloc de tres passos manuals fàcils
  d'oblidar-ne un.

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

- **Font canònica del CDMGE: fixar-la i sincronitzar la còpia d'OneDrive** · Prioridad: mitjana
  El valor titular del CDMGE (mitjana mòbil 30d de la `tasa_anual`, `cdmge.csv`)
  difereix segons l'origen de dades: **+25,9%** citat manualment, **+21,2%** al repo
  `~/repos/observatori-comerc` (fins 15-jun-2026), **+2,3%** a la còpia d'OneDrive de
  l'observatori (desactualitzada, fins 15-maig-2026). Abans de tornar a usar aquesta
  dada a cap edició cal (1) fixar quina còpia és la font canònica —presumiblement
  `~/repos/observatori-comerc`, la que corre el pipeline— i (2) actualitzar/descartar
  la còpia d'OneDrive perquè no s'agafi per error. Avís tècnic associat: el valor
  **281,5%** de l'1-jun-2026 és un **efecte base real** (denominador baix del 2025),
  no un error de parseig, i **contamina qualsevol mitjana de finestra** que el toqui
  (l'avg30 baixa de 21,2% a 12,2% si s'exclou; mediana 8,1%). Detectat 2026-07-25 en
  validar (i descartar) la hipòtesi calor→CDMGE del Núm. 13.

- **Sèrie d'anomalia tèrmica per CCAA (AEMET) com a possible font futura** · Prioridad: baixa
  Per poder validar hipòtesis climàtiques (p.ex. calor→consum, calor→divergència
  territorial de l'ICM) caldria integrar al pipeline de l'observatori una sèrie
  d'**anomalia tèrmica mensual per CCAA** (font candidata: AEMET, API OpenData).
  Avui el cache de l'observatori no té cap dataset meteo/clima, i sense temperatura
  per territori aquestes hipòtesis no són testables amb dades pròpies. Investigar
  si AEMET OpenData exposa sèries mensuals agregables a CCAA i el seu format/límits
  abans de comprometre-hi cap desenvolupament. Origen 2026-07-25 (hipòtesi calor
  descartada per manca d'aquesta dada).

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

## Causa arrel del Núm. 14: la tesi setmanal no arriba mai a la CI (prioritat alta)

Detectat 2026-08-08 preparant el Núm. 15. `config/tesi_setmana.md` i
`config/noticies_editor.md` estan al `.gitignore` i no estaven trackejats. El
workflow `newsletter-schedule.yml` treballa sobre un clon net des d'origin, de
manera que `generate.py` no troba cap dels dos fitxers i genera l'edició
**ignorant la tesi de l'editor sense avisar**. Això és exactament el que va
passar amb el Núm. 14 del 2026-08-03, i que es va deixar apuntat com a "causa
arrel no investigada".

Aquesta setmana s'ha resolt a mà: els dos fitxers s'han afegit amb `git add -f`
perquè el cron els trobi. Un cop trackejats, el `git add -A -- config/ docs/`
del workflow ja captura la seva eliminació quan `generate.py` els consumeix i
els renombra a `.used.md`, així que el cicle es tanca sol.

Queda pendent el fix estructural, perquè `git add -f` cada setmana és un rasclet
que algú s'oblidarà de passar:

1. Treure `config/tesi_setmana.md` i `config/noticies_editor.md` del
   `.gitignore` (mantenir-hi només els `.used.md`), igual que ja es fa amb
   `config/estil_editorial.md`, que sí està trackejat.
2. Afegir a `generate.py` un avís explícit i visible quan s'esperava tesi i no
   n'hi ha cap: avui el fallback és silenciós, i un fallback silenciós en un
   pipeline supervisat un cop per setmana és indistingible d'un èxit.
3. Fer que `schedule.py` inclogui a la notificació de diumenge si l'edició
   s'ha generat amb tesi o sense.
