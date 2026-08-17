# Roadmap — j3b3-newsletter

Tareas pendientes ordenadas por momento de ejecución.

## `scripts/verify.py` — verificació numèrica del borrador abans de compose · FET (2026-08-17)

IMPLEMENTAT. Corre entre `generate.py` i `compose.py`, cablejat a
`executa_pipeline()` de `schedule.py` (bloqueja: no compon, no publica web i no
crea campanya) i a `run_newsletter.py` (pregunta, amb default NO).
Regressió: `tests/casos_verify/executa.py --semana YYYY-MM-DD`, 3 casos.

**Taxonomia decidida** (el dubte que bloquejava el disseny): cada número del cos
es classifica com ANCORAT (cel·la d'un CSV del snapshot, amb tolerància segons
els decimals impresos) · DERIVAT (diferència reproduïble entre dues cel·les) ·
EXTERN (surt a `context_efectiu.txt`, o sigui la tesi de l'editor o els fets
macro: verificat per l'editor, no per l'script) · PREMSA (dins un paràgraf del
Bloc 2) · ORFE. Un ORFE és ERROR als blocs de dades pròpies (1 i 3) i AVÍS a la
resta. Aquesta gradació és el que evita el mode de fallada que temíem: un gate
que crida en fals s'acaba desactivant.

**Les afirmacions de ratxa i superlatiu** s'extreuen amb una crida a Sonnet que
NOMÉS fa de parser (retorna entitat, mètrica, periode, direcció, n, referència) i
es verifiquen amb codi contra la sèrie. Si el parser s'inventa una afirmació, la
comprovació falla; si se'n salta una, cau al gate de números orfes.

**Dos canvis que va exigir:** `snapshot.py` ara desa l'HISTÒRIC per CCAA de
l'ICM (abans només el mes més recent, o sigui que la ratxa territorial del
Núm. 15 era inverificable per construcció), i `generate.py` desa
`output/semana-X/context_efectiu.txt`.

**Per què.** El Núm. 15 (2026-08-10) ha estat l'edició amb més marge d'error
detectat fins ara, i per primera vegada amb un **error factual**, no d'estil: el
borrador afirmava que "Cataluña acumula seis meses consecutivos en negativo en
ventas reales". És fals. La ratxa de sis mesos consecutius (gener-juny 2026) és
de **Balears**; Catalunya va estar en positiu de gener a maig (+2,7, +0,1, +3,5,
+2,3, +0,4), només entra en negatiu al juny i tanca el semestre en **+1,2%
acumulat**. El model havia llegit correctament la sèrie de Balears a la tesi i
n'havia traslladat la propietat a l'altra comunitat que apareixia al costat.
L'error va sobreviure a la generació i el va enxampar la revisió humana, que és
precisament el que no ha de ser l'única barrera.

**Principi de disseny (el mateix que l'anti-al·lucinació de notícies).** El gate
va a la **capa de dades**, no al prompt: una regla al system prompt és defensa en
profunditat, no la defensa principal. `verify.py` s'executa **entre `generate.py`
i `compose.py`** i falla en dur si una xifra del cos no es pot ancorar a una
cel·la concreta d'un CSV del snapshot.

**Esbós del que hauria de fer.**

1. Extreure del borrador (ja sense TRAZABILIDAD) tots els números amb el seu
   context textual: percentatges, milers, valors absoluts, punts.
2. Per a cada número, buscar-lo als CSV del snapshot i resoldre a quina sèrie
   pertany (àmbit, tipus, indicador, període).
3. Marcar com a **error** el número que no aparegui a cap CSV i no estigui
   declarat com a procedent de `<CONTEXT_MACRO>` o de premsa.
4. Marcar com a **error d'atribució** el cas d'avui: un número que SÍ existeix al
   CSV però associat en el text a un subjecte diferent del de la seva fila
   (Balears → Catalunya). És el cas difícil i el que dona valor real a l'eina.
5. Comprovar les afirmacions de superlatiu i de ratxa ("mínim de la sèrie", "sis
   mesos consecutius", "primera caiguda des de"), que són verificables per
   construcció sobre la sèrie i que avui ningú comprova automàticament.

**El matís que cal resoldre al disseny, i per això no s'improvisa.** Definir què
compta com a "número verificable" no és trivial: conviuen xifres del snapshot,
xifres de `<CONTEXT_MACRO>` (verificades a mà per l'editor, absents dels CSV),
xifres de premsa citades dins una notícia del Bloc 2, i xifres derivades
legítimes (diferències, sumes, "un múltiple de"). Un verificador massa estricte
bloquejaria cada edició per soroll i s'acabaria desactivant, que és el pitjor
resultat possible. Cal decidir la taxonomia abans d'escriure codi.

## Arxiu web incomplet: falten els Núm. 4, 5 i 14 a pulso.j3b3.com · Prioridad: media

Confirmat 2026-08-08 contra el manifest viu: `docs/pulso/manifest.json` conté
[1, 2, 3, 6, 7, 8, 9, 10, 11, 12, 13, 15]. El **Núm. 14** és el cas recent i el
més il·lustratiu del forat estructural ja documentat més avall: es va corregir el
mirall del dashboard el 2026-08-02 però ningú va tornar a executar
`publish_web.py`, així que l'edició mai va arribar a la web estàtica.

Es deixa per a una **sessió dedicada** (decidit 2026-08-08: no barrejar-ho amb el
tancament d'una edició en curs). Procediment de recuperació ja documentat a la
nota sobre `publish_web.py` d'aquest mateix fitxer: copiar el `.md` verificat del
mirall d'`observatori-comerc/data/newsletter/` a un `output/semana-X/` temporal i
cridar `publish_web.py --semana X --numero N --output-dir <temp>`. `update_manifest()`
sobreescriu per `numero`, així que regenerar reescriu índex i sitemap sols.

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
