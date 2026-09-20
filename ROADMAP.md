# Roadmap — j3b3-newsletter

Tareas pendientes ordenadas por momento de ejecución.

## 0 · PRIORITAT MÀXIMA — el gate deixa passar errors per atzar (2026-09-20)

**Per davant de qualsevol altra cosa d'aquest fitxer.** El bug del Núm. 17
bloquejava contingut bo (fals positiu): costava una setmana sense edició. Aquest
deixa passar contingut dolent (fals negatiu): posa una xifra falsa a la bústia
dels subscriptors i no hi ha manera de saber quantes vegades ja ha passat.

### Què es va mesurar

Sobre el borrador del Núm. 20, sense tocar ni el text ni l'snapshot:

- **Set execucions de `verify.py`**: la primera va donar 1 ERROR i va dir "el
  borrador NO passa el gate"; les sis següents, "Gate superat". L'error era
  real (una afirmació de superlatiu sobre la quota salarial que la sèrie no
  aguanta).
- **Vuit passades de `extreu_afirmacions()`** sobre el mateix cos: 5, 5, 4, 4,
  1, 5, 5, 5 afirmacions. La unió satura en 6 afirmacions diferents a partir de
  la segona passada.
- L'afirmació que genera l'ERROR surt en **4 de 8 passades**.
- La part determinista (ancoratge de números) va sortir **idèntica a totes**:
  51 ancorats, 0 orfes. El problema és només la capa LLM.

### Causa

`extreu_afirmacions()` (`scripts/verify.py`) crida l'API amb
`temperature=0.0`. Temperatura zero **no** garanteix determinisme: la mateixa
entrada torna llistes d'afirmacions diferents. `schedule.py` decideix per codi
de sortida, o sigui que la fiabilitat del bloqueig era una loteria.

### Fet (2026-09-20)

1. **Unió de passades a `verify.py`.** `extreu_afirmacions(cos, modelo,
   passades=3)` fa N crides i verifica la **unió deduplicada**: una afirmació
   que aparegui en qualsevol passada entra al gate. Nou flag `--passades`.
   L'informe imprimeix el recompte de cada passada perquè la dispersió es vegi.
   La clau de deduplicació inclou entitat i mètrica: si dues passades parsegen
   la mateixa frase amb subjectes diferents, es verifiquen les dues lectures.
2. **Segona capa a `schedule.py`.** Executa `verify.py` `VERIFY_RUNS` vegades
   (default 3) i bloqueja si **qualsevol** execució troba un error.
3. **Dues sèries derivades noves a `carrega_series()`**, pel mateix motiu que
   ja tenien la bretxa de digitalització i la variació del cens: si una xifra
   editorial no és cap cel·la, o surt ORFA (ERROR al Bloc 1 i 3) o s'ancora on
   no toca. Afegides les mitjanes per període de la quota salarial
   (`prod|quota_salarial_mitjana`) i el complement de la classe de mida
   (`mida|<pais>|<ind>|LT10`, el pes de les empreses de menys de 10 ocupats).

### Tercera troballa: "ANCORAT" no vol dir correcte

Amb 356 sèries carregades, l'ancoratge és una cerca de valor i qualsevol número
de dos dígits i un decimal troba parella. Comprovat el 2026-09-20 sobre el
Núm. 20: el **49,1%** del pes de les microempreses sortia com a ANCORAT perquè
casava amb l'índex de vendes minoristes de **Bulgària del juliol de 2006** i
amb quatre dies del CDMGE. La sèrie correcta no estava carregada. El recompte
"ANCORAT 40 · ORFE 0" donava, doncs, una seguretat que no hi era.

Carregar la sèrie bona (punt 3 de la llista de dalt) ho arregla per a aquest
cas: ara el diagnòstic d'ATRIBUCIÓ diu "el valor citat encaixa amb España · %
del empleo del comercio en empresas de menos de 10 ocupados". Però la resolució
principal d'aquella frase **segueix caient a la sèrie equivocada** (UE-27,
menors de 25 anys), perquè el vocabulari de mètrica se solapa molt. No bloqueja
perquè la confiança és baixa, que és el comportament correcte.

Pendent de decidir: si l'ancoratge ha d'exigir que la sèrie on encaixa el valor
sigui també plausible per entitat i mètrica, en lloc d'acceptar qualsevol
coincidència numèrica. Avui no ho exigeix.

### El que NO queda resolt — cal decidir

La unió arregla la **cobertura** (quines frases s'examinen) però no la
**severitat**. Mesurat després del canvi, amb 3 passades: de 5 execucions, 2 van
donar ERROR i 3 "Gate superat". La raó és que el parse de la mètrica varia i
això canvia contra quina sèrie es resol la frase:

- parsejada com a *quota salarial* → resolució neta → **ERROR**;
- parsejada com a *valor afegit constants* → la mètrica no casa → "RESOLUCIÓ
  INCERTA" → **AVÍS**, i el gate passa.

En totes dues lectures la comprovació **falla**. La frase no és certa sota cap
sèrie candidata; l'única cosa que canvia és la confiança de la resolució, i la
confiança baixa la converteix en avís per disseny (la decisió que es va prendre
arran del Núm. 17, i que segueix sent correcta).

Amb una probabilitat d'encert per passada del 15-20%, pujar passades no és
solució: caldrien ~18 per arribar al 95%.

**Proposta per al fix de fons** (no aplicada; toca la part més delicada del
pipeline i no es va voler fer el dia d'una edició): si una afirmació falla la
comprovació contra **totes** les sèries candidates a què es resol, ha de ser
ERROR encara que la resolució sigui incerta. Això no reobre els falsos positius
del Núm. 17, que eren casos on l'afirmació era CERTA contra la sèrie bona i el
gate n'havia triat una de dolenta: aquí no hi ha cap lectura sota la qual la
frase sigui certa. Requereix que `verifica_racha()` i `verifica_superlatiu()`
avaluïn contra la llista de candidates i no només contra la millor.

**Mentrestant**: el gate no és una garantia. Cap edició s'hauria de programar
només perquè `verify.py` digui "Gate superat".

## Gate: falsos positius que van costar el Núm. 17 · FET (2026-08-28)

El diumenge 2026-08-23 el cron va generar el Núm. 17 i `verify.py` el va
suspendre amb 5 errors. Tots falsos. Com que el gate bloqueja la cadena, no es va
compondre ni programar cap campanya: **el dilluns 24 d'agost no va sortir cap
edició** i no es va detectar fins l'11è dia. Última enviada: Núm. 16 (Brevo 32).
(El primer intent d'aquell diumenge havia fallat abans, per l'SDK d'Anthropic
saltant a 1.x —`temperature` ja no és un kwarg vàlid—, arreglat amb el pin
`anthropic<1.0` de `d751e01`.)

Arrel comuna dels cinc: `resol_serie()` només exigia coincidència d'**entitat**,
sense cap llindar de mètrica. N'hi havia prou que la frase i la sèrie
compartissin "España" per resoldre "la brecha de empleo joven entre España y la
UE-27" contra "ventas minoristas de España" i comptar-hi una ratxa sense sentit.

Quatre canvis (tots a `scripts/verify.py`):

1. **Llindar de mètrica.** `Serie.temes` posa el vocabulari de cada família en la
   llengua del producte (les etiquetes dels CSV són tècniques i en català) i la
   resolució exigeix entitat **i** mètrica. Sense mètrica no hi ha resolució:
   AVÍS de "no s'ha pogut resoldre", no ERROR.
2. **Confiança alta/baixa.** Amb resolució incerta un desquadrament és AVÍS i no
   bloqueja. Un gate que crida en fals s'acaba desactivant; un que bloqueja en
   fals és pitjor encara, perquè el resultat és el silenci.
3. **El Bloc 2 no bloqueja mai.** Allà el subjecte és una notícia i la font és el
   mitjà ("Cataluña lidera las aperturas de Charter").
4. **Dues guardes de sentit:** una ratxa "en negatiu" sobre una sèrie sense cap
   valor negatiu no és comprovable (era el cas de "lleva quince años sin atraer
   jóvenes" contra els milers d'ocupats), i una ratxa real més llarga que la
   declarada no és un error, és un text que es queda curt.

**Forat de cobertura tancat de camí:** `ocupacio_comerc.csv` (ocupats per tram
d'edat, Eurostat LFS) arribava al snapshot des del 2026-06-22 però `verify.py` no
el carregava mai — o sigui que tota xifra d'estructura d'edat era ORFE, i al
Bloc 1 això és ERROR. Ara es carrega amb els agregats que el butlletí anomena
("los menores de 25", "los mayores de 50"), amb el pes sobre el total i amb la
bretxa Espanya−UE-27, i `ancora()` accepta que el text escrigui persones
(172.200) contra una sèrie en milers (172,2).

**I un defecte del prompt, no del gate:** `slice_ocupacio_spain()` de
`generate.py` filtrava `pais_codi == "ES"`, així que la UE-27 no arribava mai al
model tot i ser al CSV. El Núm. 17 va treure el 14,2% europeu del backlog
editorial i la traçabilitat va afirmar que el CSV no el contenia. Renombrada a
`slice_ocupacio_edat()`: passa ES i UE-27, amb el pes de cada tram ja calculat.

Regressió: `tests/casos_verify/executa.py --semana 2026-08-24` (4 casos, el nou
és `cas3_falsos_positius.md`, que ha de PASSAR) i `tests/casos_verify/unitaris.py`
(comprovacions deterministes de la resolució, sense crida a l'LLM).

Pendent, si es vol tancar el mode de fallada del tot: que un gate suspès avisi
per correu com ho fa la notificació de diumenge, en lloc de deixar-ho només al
correu de fallada de GitHub Actions, que és el que va passar desapercebut.

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

## Arxiu web: Núm. 14 RESOLT (2026-08-17); els Núm. 4 i 5 no són un forat · Prioridad: baixa

**El Núm. 14 estava mal diagnosticat.** No faltava la pàgina: `docs/pulso/num-14.html`
existia i era correcta des del commit `8eed024`. El que faltava era la seva
entrada al `manifest.json`, o sigui que la pàgina era **òrfena**: viva a la URL
però inabastable des de l'índex i absent del sitemap. Resolt amb
`resync.py --semana 2026-08-03 --nomes web`, que reconstrueix manifest, índex i
sitemap des del markdown. Manifest ara: [1,2,3,6,7,8,9,10,11,12,13,14,15,16].

**Els Núm. 4 i 5 NO s'han de publicar.** Mai es van enviar a ningú: eren
borradors cancel·lats (campanyes Brevo 9 i 10, suspeses el 2026-06-03) i el que
va sortir aquella setmana va ser el Núm. 6. Publicar-los ara posaria a l'arxiu
públic contingut que cap subscriptor ha rebut. L'única qüestió real és
**presentacional**: el lector veu la numeració saltar del 3 al 6. Decisió
pendent del Jordi, no incidència: o es deixa el salt, o es documenta a l'índex,
o es renumera l'arxiu (que trencaria les URL ja indexades: no recomanat).

### Nota original (2026-08-08), conservada

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

## `config/backlog_angles.md` — angles no cremats · FET (2026-08-17)

Deu angles amb la xifra ja verificada contra el CSV, el mecanisme escrit i el
suport de Bloc 3, cap d'ells usat a les 16 edicions enviades (revisió una per
una dels miralls del dashboard, no de l'historial, que arrossega entrades
cancel·lades).

**Mecanisme, no només document:** quan una setmana NO hi ha
`config/tesi_setmana.md`, `generate.py` injecta el backlog al prompt i el model
ha de triar-ne un en lloc de caure a l'heurística de "la dada més fresca
manda" — que és la causa de fons del "totes les newsletters s'assemblen" del
juny. L'angle triat es registra al camp `angle_backlog` de l'historial i els ja
gastats s'injecten com a prohibits a les setmanes següents.

Pendent de reposar la llista quan baixi de 4-5 angles lliures. Datasets del
dashboard encara sense explotar per si cal ampliar-la: `eaes.csv`,
`estructura_comerc.csv`, `subsectors_dirce.csv`, `subsectors_epf.csv`,
`europa_vab.csv` (28 països des del 1975).

## Bug: `--force` crema `angle_backlog` d'edicions que mai han passat verify.py · Prioridad: mitjana

Detectat 2026-08-23 regenerant el Núm. 17. `generate.py` marca l'angle triat al
camp `angle_backlog` de l'historial des del primer intent, encara que aquest
intent quedi bloquejat per `verify.py` i mai arribi a `compose.py` ni a Brevo.
La funció que calcula els angles "ja gastats" (`generate.py:96-97`) llegeix
**tot** l'historial sense excloure l'entrada `(numero, semana)` de l'edició que
s'està regenerant, de manera que un `--force` sobre una edició bloquejada crema
el seu propi angle abans d'hora i força el model a triar-ne un altre de
diferent — amb xifra protagonista i notícies noves, no una correcció de la
mateixa edició.

**Fix correcte:** excloure `(numero, semana)` de l'edició actual de la llista
`usats` a `generate.py:96-97` en comptar angles gastats. No urgent — no
bloqueja el pipeline, només fa que un `--force` post-bloqueig no conservi
l'angle triat inicialment. Queda per a una sessió de calma.

Relacionat, i amb el mateix efecte però pel costat de l'historial: una entrada
d'una edició que **no s'ha publicat** (com el Núm. 17 del 2026-08-24) crema
igualment el seu `angle_backlog` i entra a la memòria editorial que s'injecta al
prompt. Mentre no es corregeixi, l'entrada d'una edició bloquejada no s'hauria
de pujar a origin sense decidir-ho expressament.

## DIRCE al snapshot (perquè la predicció del Núm. 17 sigui verificable) · Prioridad: mitjana

El Núm. 17 predica sobre el cens del DIRCE (`<372.000` empreses de CNAE 47 a
1-1-2026, resolució desembre de 2026), però `subsectors_dirce.csv` no arriba al
snapshot: les quatre xifres del Bloc 4 surten ORFES i el gate només les pot
avisar. Al Bloc 4 això és el comportament correcte —una predicció no és al CSV—
però la BASE de la predicció (377.471 el 2025, i les variacions de −8.513 i
−7.303) sí que hauria de poder ancorar-se.

Fix: afegir `dirce_origen: "data/cache/subsectors_dirce.csv"` a `settings.yaml`,
copiar-lo a `snapshot.py`, injectar-lo a `generate.py` i carregar-lo a
`verify.py`. Mateix patró que `estructura_empreses.csv` (commit del 2026-08-28).
**Avís obligatori quan es faci**: el cens del DIRCE i el d'Eurostat BSD NO són
la mateixa magnitud (377.471 contra 426.519) i no es poden comparar entre si; i
el salt 2022→2023 del DIRCE és de −35.318 empreses, vuit vegades el dels anys
següents, cosa que fa pensar en un canvi metodològic **no verificat**. Cap text
s'hi ha de recolzar sense comprovar-ho.

## El mirall falla en silenci quan no troba el repo del dashboard · Prioridad: mitjana

Detectat el 2026-09-04 programant el Núm. 18. `mirror_only.py` no feia
`load_dotenv`, o sigui que `OBSERVATORI_PATH` no arribava mai i `mirror.py`
queia al valor per defecte `ROOT.parent / "observatori-comerc"`, que no
existeix. El `.env` ja està arreglat (`aab412f`), **però la part important
segueix oberta**: el que va fer que això passés desapercebut no va ser la ruta
sinó el silenci.

`mirror_to_dashboard()` (`scripts/mirror.py:32-37`) té dues guardes que
imprimeixen i fan `return`:

```python
if not obs_root.is_dir():
    print(f"\n[mirror] Repo destí no trobat a {obs_root}. Salto espejado.")
    return
if not src.is_file():
    print(f"\n[mirror] Origen no trobat: {src}. Salto espejado.")
    return
```

Retorna `None` tant si ha publicat com si no ha fet res. Els quatre cridants
—`send.py:143`, `schedule.py:515`, `mirror_only.py:84` i `resync.py:181`— no
poden distingir els dos casos i continuen com si hagués anat bé.

**El forat és que el resync tampoc ho veu**, que és precisament l'script que
existeix per adonar-se'n. `sincronitza_mirall()` (`resync.py:173-183`) retorna
la cadena fixa `"mirall publicat (commit + push a observatori-comerc)"` sense
mirar què ha passat, i el titular el llegeix del fitxer destí; si el destí no
existeix, `titular_desti` queda buit i la comprovació final
(`resync.py:331-333`) fa:

```python
if not titular_desti:
    print(f"  {d:<10} (no s'ha pogut llegir el titular per comparar)")
    continue
```

`continue` sense afegir res a `problemes`. Resultat: resync imprimeix "Els
llocs sincronitzats diuen el mateix" i surt amb codi 0 havent-se saltat el
mirall del tot. És el mateix patró dels incidents dels Núm. 10, 12 i 14 que
van motivar l'script.

Fix proposat, en tres trossos petits:

1. `mirror_to_dashboard()` retorna un `bool` (o llança) en lloc de `None`, i
   distingeix "no hi ha res a fer perquè ja estava publicat" (èxit idempotent)
   de "no he pogut publicar" (fallada).
2. `sincronitza_mirall()` propaga aquest resultat en lloc de la cadena fixa.
3. A la comprovació final del resync, un titular buit en un destí que s'ha
   intentat sincronitzar és un **problema**, no una línia informativa. El cas
   legítim de "no comparable" és el `--dry-run`, que ja es tracta a part.

Val la pena revisar de camí si `OBSERVATORI_PATH` hauria de ser obligatori i
fallar d'entrada quan no hi és, en lloc de tenir un valor per defecte relatiu
que només és correcte en una disposició de carpetes que ja no fem servir.

## Els camps estructurats de l'historial no reflecteixen les correccions manuals · Prioridad: mitjana

Detectat el 2026-09-04 al Núm. 18. La predicció generada per Sonnet es fixava
sobre "el tramo de 10 a 49 ocupados", un desglossament que **no existeix al
pipeline** (el fetcher de digitalització demana `size_emp=GE10` agregat) i que
a més contradeia el mecanisme del Bloc 1, que parla del tram per sota de 10.
Es va reescriure a mà sobre la bretxa GE10 amb llindar `< −7,0 pp`.

El text enviat és el corregit. **Els camps de l'historial, no.** Van quedar
amb la primera versió:

```
metrica_prediccion: "... tramo 10-49 ocupados ... encuesta TIC Eurostat 2027"
umbral_prediccion:  "se mantiene o amplía respecto a -9,8 pp"
```

La causa és l'ordre del pipeline: `generate.py` extreu els camps estructurats
amb una segona crida al model **sobre el borrador que acaba d'escriure**, i
els desa a `config/historial_editorial.json` abans que ningú hagi llegit el
text. Tot el que es corregeixi després —a mà, o iterant contra `verify.py`—
queda fora. Aquesta setmana es va agafar per casualitat; en una setmana normal
passa de llarg.

Per què importa més del que sembla: aquests camps no són documentació, són
**entrada d'altres sistemes**. El registre de prediccions
(`observatori-prediccions`) llegeix `metrica_prediccion` i `umbral_prediccion`
per autopuntuar, o sigui que hauria avaluat una predicció que no s'ha publicat
mai, contra una sèrie que no tenim. I `format_historial_para_prompt()` injecta
`angulo_bloc1` de les últimes sis edicions al prompt: un angle mal registrat
contamina l'anti-repetició durant un mes i mig.

Mecanisme proposat — **re-extreure els camps del text final, no del primer**:

- Moure l'extracció fora de `generate.py` a un pas propi
  (`scripts/extract_historial.py`) que llegeixi
  `output/semana-X/newsletter.md` tal com és **en aquell moment** i reescrigui
  l'entrada de l'historial d'aquella setmana.
- Cridar-lo des de `schedule.py` just abans de crear la campanya, que és
  l'últim punt en què el text encara pot canviar. Així el que es registra és
  sempre el que s'envia, sense dependre de si hi ha hagut correccions.
- `generate.py` continua fent la primera extracció (fa falta per a
  l'anti-repetició si l'edició no s'arriba a enviar), però deixa de ser
  l'autoritat.

Alternativa més barata si no es vol tocar l'ordre del pipeline: que
`verify.py` compari els camps de l'historial amb el text que acaba de
verificar i avisi quan no es corresponen. No ho arregla, però ho fa visible al
mateix lloc on ja mirem si l'edició està bé. Té l'inconvenient de barrejar
responsabilitats: el gate és numèric i això no ho és.

Sigui quina sigui l'opció, convé deixar constància al propi historial quan un
camp s'ha corregit a mà. Al Núm. 18 s'hi ha posat un camp `nota_correccio`
amb el motiu; si es formalitza, millor un nom fix i documentat al
`data_dictionary.md`.

## Post-lanzamiento (después del 1 de junio de 2026)

- **Sincronització única dels tres punts de sortida (Brevo + mirall + web)** · FET (2026-08-17): `scripts/resync.py`
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

## Bug de verify.py: el gate error/avís no era determinista · FET (2026-09-14, Núm. 19)

Detectat preparant el Núm. 19 (estructura d'edat de la plantilla). Fallots a la
capa de parseig, observats al llarg de **cinc execucions**. La capa d'ancoratge
numèric va donar sempre el mateix (ORFE 0); la resolució de sèries va canviar a
cada passada amb el mateix text o amb variacions mínimes:

1. **Direcció del superlatiu invertida.** Una afirmació de MÀXIM es comprova com
   si fos de MÍNIM. El missatge diu "el text diu més baix de tota la sèrie" i
   llista com a contraexemples valors *inferiors* (2008 +1.37, 2009 +3.27…), que
   només contradirien una afirmació de mínim. Persisteix escrivint literalment
   "su valor más alto", o sigui que no és ambigüitat de redacció.

2. **Resolució de sèrie no determinista.** Una afirmació sobre el tram **50+**
   es va resoldre contra quatre sèries diferents en cinc execucions: "menores de
   25 años" (dos cops), "% del empleo del comercio en empresas de 10 o más
   ocupados", "ocupados CNAE 47, miles" i "UE-27, de 25 a 49 años". Una ratxa
   explícitament espanyola es va comprovar contra la sèrie de la **UE-27** fins i
   tot després d'escriure "en España" a la frase. I una afirmació sobre la bretxa
   d'edat es va resoldre contra "diferencial de ventas minoristas" (ICM), que no
   hi té cap relació. La sèrie correcta (`mayores de 50 años`) existeix a
   `_AGREGATS_EDAT` i es carrega bé — el problema és el matching, no les dades.

3. **El desempat per atribució no és fiable.** El gate sap detectar quan la xifra
   citada encaixa amb una altra sèrie: imprimeix "ATRIBUCIÓ: el valor citat
   encaixa amb España, mayores de 50 años". En una execució això va degradar
   l'error a avís no bloquejant; en una altra, amb la mateixa detecció impresa,
   va bloquejar igualment. El camí de degradació depèn de l'atzar del parseig.

Impacte: el gate bloqueja edicions correctes. És exactament el patró del
2026-08-23 documentat a la capçalera del propi `verify.py` (cinc errors falsos,
cap campanya, onze dies sense que ningú se n'adonés). La capa d'ancoratge
numèric, en canvi, va funcionar perfectament (ANCORAT 51, ORFE 0).

**Per què és prioritat alta, i no un altre fals positiu ocasional:** el mateix
text, amb la mateixa detecció d'atribució impresa ("ATRIBUCIÓ: el valor citat
encaixa amb España, mayores de 50 años"), **a vegades bloqueja i a vegades
degrada a avís**. Això no és una regla determinista amb un bug de matching —
és una font d'aleatorietat al mecanisme que decideix error vs. avís, molt
probablement perquè aquesta part del pipeline crida l'LLM com a parser (veure
la capçalera del fitxer: "l'LLM NOMÉS fa de parser") i la seva sortida no és
reproduïble entre crides. Mentre això sigui així, el gate no es pot confiar
cegament ni tampoc ignorar sistemàticament: cal fer-lo determinista, o com a
mínim, **conservador per defecte** (qualsevol cas de resolució incerta o
d'atribució detectada hauria de degradar a avís, mai bloquejar).

**Casos de regressió d'avui (Núm. 19, 2026-09-13), per a `tests/casos_verify/`.**
Totes les xifres sota estan contraverificades a mà contra
`data/semana-2026-09-14/ocupacio_comerc.csv` amb l'agregació de
`_AGREGATS_EDAT` i són CORRECTES; el gate les hauria de deixar passar sempre:

1. *"El tramo de 50 años o más pesaba un 18,2% en 2008. En 2025 pesa un 32,8%."*
   Resolt contra 4 sèries diferents en 5 execucions: "menores de 25 años" (×2),
   "% del empleo del comercio en empresas de 10 o más ocupados", "ocupados
   CNAE 47, miles", "UE-27, de 25 a 49 años". Sèrie correcta: `España, mayores
   de 50 años`. 18,17%→32,83% = ×1,81, verificat.
2. *"La brecha con la UE-27 llegó a 6,8 puntos en 2022, el valor más alto de la
   serie"* → direcció de superlatiu invertida: el gate llegeix "más alto" com
   si fos "más bajo" i llista contraexemples inferiors (2008 +1,37). Màxim
   real: 2022, 6,758p, verificat.
3. *"el tramo de 50 o más años nunca había pesado tanto como en 2025"* →
   resolt contra "UE-27, de 25 a 49 años" en comptes de `España, mayores de 50
   años`. 2025 és el màxim de la sèrie correcta, verificat.
4. *"Desde entonces, el peso de los menores de 25 en España ha subido todos
   los años"* → resolt contra la sèrie de la **UE-27** malgrat dir "en España"
   explícitament a la frase. Puja cada any 2021-2025 (6,84→7,00→7,14→7,95→
   7,98→8,48) a la sèrie espanyola, verificat.
5. *"el tramo de 50 o más años se ha dado la vuelta: por debajo de la media
   europea de 2008 a 2021, por encima desde 2022, salvo en 2023"* → resolt
   contra "España · % del empleo del comercio en empresas de 10 o más
   ocupados", sense relació. Creuament correcte verificat any a any.

Pla original (a-d): comprovar signe/direcció, donar pes al tram d'edat dins
`resol_serie()`, degradar sempre a avís quan hi ha detecció d'ATRIBUCIÓ, i
incorporar els casos com a regressió. Substituit per la solució aplicada (b i
c del pla original; a i d es van descartar, veure sota).

**Reincidència 2026-09-14 (mateixa sessió, mateix text de fons):** el mateix
gràfic 50+ (ara com a sèrie absoluta enlloc de diferencial) va tornar a fallar
amb les MATEIXES tres afirmacions, ara resoltes contra "España, de 25 a 49
años" en comptes de "mayores de 50 años" — de nou amb la línia d'ATRIBUCIÓ
correcta impresa i ignorada pel gate. En total, comptant les dues sessions
d'avui: ~8 execucions, el mateix contingut factual, almenys 6 sèries
diferents encertades erròniament. Això reforça que el problema no és a les
dades ni al text — és 100% a la capa de resolució/decisió del parser.

**Solució aplicada (2026-09-14), a `resol_serie()`:** l'arrel real no era la
direcció del superlatiu ni el pes del tram d'edat — era que `confianca` es
calculava mirant NOMÉS el millor candidat, sense comprovar si la tria era
neta. S'ha afegit `_MARGE_AMBIGUITAT` (0.3): ara `resol_serie()` també fa un
seguiment del segon millor candidat, i degrada `confianca` a "baixa" (que
`verifica_racha`/`verifica_superlatiu` ja convertien en AVÍS, no ERROR) en
qualsevol d'aquests dos casos:

1. El segon candidat queda a menys de `_MARGE_AMBIGUITAT` punts del millor
   (tria no neta — dues sèries gairebé igual de plausibles).
2. La llista `altres` (la mateixa detecció d'ATRIBUCIÓ que el gate ja
   imprimia) no és buida — el valor citat encaixa també amb una altra sèrie
   diferent de la triada.

Aquest segon punt és exactament el patró (c) del pla original, i cobreix
directament els 5+3 casos documentats amunt: en tots ells `altres` ja
identificava la sèrie correcta (impresa com "ATRIBUCIÓ: el valor citat
encaixa amb..."), simplement no s'usava per decidir la severitat.

**Diagnosi arrel, per si cal revisar-ho més endavant:** `s.vocabulari` (el
`temes` de cada sèrie a `_afegeix_ocupacio_edat`) és IDÈNTIC entre trams
d'edat — `base = f"{_TEMES_OCUPACIO} {_TEMES_EDAT} comercio minorista lfs
eurostat"` no conté cap paraula específica de tram ("25", "50", "mayores",
"menores"). Això vol dir que `coincidencia_met` mai diferencia un tram
d'edat d'un altre: tota la diferenciació depèn de `coincidencia_ent` (el
solapament amb l'`entitat` que l'LLM ha escrit), que pot ser un marge molt
prim si la frase no repeteix el tram literalment. No s'ha tocat `temes` en
aquest fix perquè el marge d'ambigüitat ja cobreix el símptoma real (bloqueig
per atzar); afegir paraules de tram a `temes` seria un reforç complementari,
no substitutiu.

**Test de regressió**: `tests/casos_verify/cas4_ocupacio_edat_ambigua.md`
(cas end-to-end, crida real a l'LLM) + `AMBIGUS_TRAM_EDAT` a
`tests/casos_verify/unitaris.py` (determinista, sense LLM, reprodueix
exactament els dos mecanismes de fallada amb `entidad` genèric). Verificat:
5/5 execucions de `unitaris.py` idèntiques (determinista per construcció) i
4/4 execucions de `executa.py --semana 2026-09-14` amb `cas4` en verd
(crida real a l'LLM, confirma estabilitat de punta a punta).
