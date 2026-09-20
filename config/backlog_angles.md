# Backlog d'angles editorials

Llista d'angles amb dades verificades i **encara no cremats** a cap de les 16
edicions enviades. Serveix per a dues coses:

1. **Automàtica**: si una setmana no hi ha `config/tesi_setmana.md`, `generate.py`
   injecta aquest fitxer al prompt i el model ha de triar-ne un en lloc de
   caure a l'heurística de "la dada més fresca manda", que és la que produïa
   edicions intercanviables.
2. **Manual**: material de partida quan el Jordi seu a escriure la tesi.

## Com es fa servir

Cada angle porta la **xifra ja verificada contra el CSV** (data de verificació al
peu), el **mecanisme** —que és el que el converteix en tesi i no en dada—, i el
suport de Bloc 3. Qui l'agafi ha de **tornar a verificar la xifra** contra el
snapshot de la setmana: aquests fitxers s'actualitzen i un any nou pot moure-la.

Quan un angle s'utilitza, es marca `Estat: USAT (Núm. X, YYYY-MM-DD)`. El camp
`angle_backlog` de `config/historial_editorial.json` en guarda l'identificador,
de manera que el prompt de les setmanes següents ja sap quins estan gastats.

**Regla que no es negocia**: cap d'aquests angles substitueix la verificació de
`scripts/verify.py`. Que la xifra sigui aquí no vol dir que sigui certa avui.

---

## A1 · La mortalitat empresarial del comerç espanyol és pitjor que la europea

- **Dataset**: `estructura_retail_supervivencia.csv` (Eurostat, demografia empresarial)
- **Xifra**: de cada 100 comerços espanyols oberts, en sobreviuen **75,9 el primer any i 58,7 el segon** (2023). A la UE-27, 78,3 i 62,1. Bretxa de 2,4 punts al primer any i **3,4 al segon**: no és que obrim pitjor, és que el segon any pesa més aquí.
- **Mecanisme**: el diferencial s'obre al segon any, quan s'acaba el coixí inicial i toca renovar lloguer i finançament. És un argument sobre estructura de costos fixos i accés al crèdit, no sobre esperit emprenedor. Connecta directe amb les polítiques municipals de suport al comerç, que gairebé sempre financen l'obertura i no la supervivència.
- **Bloc 3**: barres ES vs UE-27 a Y1 i Y2, o comparativa de països si s'amplia el fetcher.
- **Per què no està cremat**: cap edició ha tractat demografia empresarial. Les 16 han anat de vendes, ocupació, marges, preus o territori.
- **Estat**: LLIURE

## A2 · Espanya té el comerç més atomitzat de la UE en ocupació, no en nombre d'empreses

- **Dataset**: `estructura_retail_mida.csv` (Eurostat SBS, classes de mida)
- **Xifra**: el **97,2%** de les empreses de comerç espanyoles tenen menys de 10 treballadors, contra el 95,5% de la UE-27 — diferència petita. La que importa és l'altra: aquestes microempreses ocupen el **45,7%** dels treballadors del sector a Espanya, contra el **35,6%** de la UE-27 i el **21,2%** d'Alemanya (2023).
- **Mecanisme**: tothom té moltes microempreses; el que distingeix Espanya és quanta gent hi treballa. Deu punts de bretxa en ocupació és el que explica per què la productivitat agregada del sector no puja quan les grans cadenes inverteixen: el gruix de la plantilla és fora d'aquesta inversió. Itàlia és pitjor (54,1%), cosa que evita el to de queixa nacional i converteix la comparació en un eix sud-nord.
- **Bloc 3**: barres del pes de les microempreses en ocupació per país (ES, IT, PT, FR, UE-27, DE).
- **Per què no està cremat**: el Núm. 11 i el 14 van tractar els MODES DE DISTRIBUCIÓ de l'INE (unilocalitzades, petites cadenes…), que és una altra classificació. Cap edició ha usat classes de mida d'Eurostat ni el contrast empreses/ocupació.
- **Estat**: LLIURE

## A3 · L'alimentació especialitzada ha perdut 8.200 establiments en sis anys

- **Dataset**: `subsectors_472.csv` (INE, Enquesta Estructural)
- **Xifra**: els establiments de comerç especialitzat d'alimentació passen de **96.251 (2018) a 88.059 (2024)**, un **−8,5%**. Dins: carnisseries 21.748, forns i pastisseries 19.201, altres aliments 14.230, fruiteries 12.449, estancs 9.134, peixateries 8.614, begudes 2.683.
- **Mecanisme**: la desaparició no és uniforme i això és la tesi. Els forns aguanten (producte de consum diari amb prima de frescor); les peixateries són el suelo (producte que exigeix coneixement del client i té substitut fàcil al lineal). El que decideix no és la mida sinó si el producte tolera l'autoservei.
- **Bloc 3**: barres d'establiments per branca 472, o variació 2018-2024 per branca si es calcula.
- **Per què no està cremat**: cap edició ha entrat al detall de 472. Precaució: hi ha un treball previ de peixateries per a Mercabarna — **no creuar-hi dades ni referències**, l'edició ha de sostenir-se només amb la font INE.
- **Estat**: LLIURE

## A4 · La inversió per local varia 7 vegades entre comunitats

- **Dataset**: `eee_ccaa.csv` (INE, Enquesta Estructural per CCAA)
- **Xifra**: **26.637 €/local** a la Comunitat Valenciana contra **3.622 €/local** a Extremadura (2024). Ràtio de **7,4 vegades**.
- **Mecanisme**: eix territorial nou. El Núm. 12 va fer divergència de VENDES per CCAA; això és divergència de CAPACITAT D'INVERSIÓ, que és el que determina la divergència de vendes de d'aquí a tres anys. La conclusió incòmoda: la política de dinamització comercial arriba on ja hi ha inversió privada.
- **Bloc 3**: barres d'inversió per local per CCAA.
- **Per què no està cremat**: els Núm. 12 i 15 van usar l'ICM per CCAA (vendes). Aquest dataset —locals, xifra de negoci, sous, inversió, VAB per comunitat— no s'ha tocat mai.
- **Estat**: LLIURE

## A5 · La densitat comercial és inversa a la riquesa

- **Dataset**: `empreses.csv` (INE DIRCE + Padró)
- **Xifra**: **9,4 comerços per 1.000 habitants a Extremadura** contra **6,2 a Madrid** (2025). Rang de 3,1.
- **Mecanisme**: la comunitat amb menys renda té més comerços per habitant, i la més rica menys. No és una paradoxa: és mida mitjana d'establiment. On hi ha renda, el mateix consum es concentra en menys locals i més grans. Serveix per desmuntar l'indicador de "densitat comercial" com a mesura de salut del sector, que és com se fa servir habitualment als plans locals.
- **Bloc 3**: barres de comerços per 1.000 habitants per CCAA.
- **Per què no està cremat**: cap edició ha usat densitat per habitant. Serie llarga disponible (2008-2025), o sigui que permet mirar si la bretxa s'obre o es tanca.
- **Estat**: LLIURE

## A6 · El comerç espanyol ven més en línia que la mitjana europea i està menys digitalitzat per dins

- **Dataset**: `digitalitzacio_comerc.csv` (Eurostat, ETICCE)
- **Xifra** (2025): venda electrònica **ES 44,0% vs UE 39,0%** (+5,0). Núvol **ES 33,3% vs UE 43,1%** (−9,8). Intel·ligència artificial **ES 14,0% vs UE 15,5%** (−1,5).
- **Mecanisme**: la contradicció aparent és l'angle. Espanya va per davant en el canal que el client veu i per darrere en la infraestructura que no es veu. Vendre en línia sense núvol vol dir fer-ho sobre sistemes que no escalen: el sostre no és comercial, és tècnic. Predicció natural: la bretxa de núvol es tradueix en bretxa de marge quan el volum en línia creixi.
- **Bloc 3**: barres de la bretxa ES−UE per tecnologia.
- **Per què no està cremat**: cap edició ha tractat digitalització. Compte: només hi ha tres tecnologies al dataset, o sigui que no es pot generalitzar a "digitalització" en abstracte — s'ha de parlar de les tres.
- **Estat**: LLIURE

## A7 · Mercadona ven una tercera part de tot el que venen els 63 líders

- **Dataset**: `lideres_empreses.csv` (SABI, tancament 2024)
- **Xifra**: Mercadona **34,06 MM€** de 109,3 MM€ agregats dels 63 líders, o sigui **31,2%** del total del panell. Segueixen Carrefour 8,6%, Lidl 6,1%, Alcampo 4,4%, Dia 4,0%. Marge net: Mercadona 4,1%, Carrefour 3,0%, Lidl 2,8%, Dia 2,0%, **Alcampo −0,2%**.
- **Mecanisme**: no la concentració en abstracte, sinó que el líder és també el que té més marge. On hi ha oligopoli sense líder rendible hi ha guerra de preus; aquí el més gran és el més rendible, cosa que fa la posició molt més difícil d'atacar. Alcampo en negatiu és el contrapunt: escala sense rendibilitat.
- **Bloc 3**: barres de quota dels 5-8 primers, o dispersió de marge net per operador.
- **Per què no està cremat**: el Núm. 2 va parlar d'oligopoli amb el CDMGE (proxy de grans cadenes, sense noms). Aquest dataset té **noms i marges**, que és una altra edició. Veure el redisseny de la pàgina de Líders pendent al dashboard.
- **Estat**: LLIURE — però amb cautela editorial: nomenar empreses i els seus marges exigeix que la font aguanti (SABI, tancaments oficials) i que no s'hi afegeixi cap judici sobre la gestió.

## A8 · L'ocupació del comerç espanyol té sis punts menys de joves que la europea

- **Dataset**: `ocupacio_comerc.csv` (Eurostat LFS)
- **Xifra** (2025): 15-24 anys **ES 8,5% vs UE-27 14,2%** (−5,7 punts). 40-49 **ES 27,0% vs 22,7%**. 50-59 **ES 24,5% vs 22,1%**.
- **Mecanisme**: el comerç espanyol no és una porta d'entrada al mercat laboral com a la resta d'Europa; és un sector de plantilla madura. Això explica el problema de relleu generacional que surt cada mes a la premsa municipal, i el converteix en estructural en lloc d'anecdòtic: no és que els joves no vulguin agafar la botiga del pare, és que fa quinze anys que no entren al sector.
- **Bloc 3**: barres de distribució per edat, ES vs UE-27.
- **Per què no està cremat**: el Núm. 15 va usar l'EPA (nivell d'ocupació i el seu traspàs al turisme). L'estructura d'EDAT no s'ha tocat mai, i el dataset té sèrie des del 2008.
- **Estat**: **USAT (Núm. 19, 2026-09-14)**. Correcció de xifra respecte del que deia aquesta fitxa: la bretxa 2025 és de **5,8 punts**, no 5,7 — 5,7 surt de restar els percentatges ja arrodonits (14,2−8,5), i el càlcul correcte és 14,236−8,478=5,758. L'edició va explotar la sèrie longitudinal (màxim de 6,8p el 2022, tres anys consecutius d'estretiment fins a 5,8p) i el creuament del tram 50+ (ES per sota de la UE-27 de 2008 a 2021, per sobre des del 2022 excepte el 2023).

## A9 · Els béns han perdut cinc punts del consum de les llars en vint anys

- **Dataset**: `estructura_consum.csv` (Eurostat, comptes nacionals)
- **Xifra**: pes dels béns en el consum de les llars espanyoles: **43,4% (2005) → 40,7% (2019) → 38,2% (2024) → 38,2% (2025)**. El 2020 va rebotar a 44,2% i va tornar a caure.
- **Mecanisme**: el terreny de joc del comerç al detall s'encongeix estructuralment, i el 2020 va demostrar que el rebot és reversible. Cada punt de quota que passa a serveis és mercat que el comerç no recupera creixent millor, perquè no és seu. Marc per llegir qualsevol dada de vendes: créixer un 2% dins un pastís que s'encongeix no és el mateix que créixer un 2%.
- **Bloc 3**: evolució del pes dels béns, o comparativa amb altres països.
- **Per què no està cremat**: PARCIALMENT GASTAT. El Núm. 2 en va treure les prediccions P011-P014 del registre (quota de béns el 2030 i el 2035). L'angle **retrospectiu** —els vint anys, i el rebot del 2020 com a prova de reversibilitat— no s'ha publicat, però cal citar la predicció anterior i no fer com si fos tema nou.
- **Estat**: SEMI-GASTAT (revisar el Núm. 2 abans d'usar-lo)

## A10 · El VAB del comerç ha perdut mig punt de PIB des del 2021

- **Dataset**: `pib_vab.csv` (INE, comptabilitat nacional)
- **Xifra**: pes del CNAE 47 al VAB total: **5,62% (2021) → 5,10% (2022) → 5,25% (2023)**. El 2024 encara no té VAB del comerç publicat, només el total.
- **Mecanisme**: el sector recupera vendes nominals més ràpid que valor afegit, cosa que vol dir que el creixement se'n va en compres i no en marge. És la versió macro del "coixí nominal" del Núm. 16, i per tant s'ha d'esperar unes setmanes per no repetir el mecanisme.
- **Bloc 3**: evolució del pes al VAB, o comparativa europea amb `europa_vab.csv` (28 països, sèrie des del 1975).
- **Per què no està cremat**: cap edició ha usat el VAB com a xifra protagonista.
- **Estat**: LLIURE — però **no la setmana següent al Núm. 16**: mateix mecanisme (nominal contra real), calen algunes edicions de separació.

## A11 · La bretxa juvenil del comerç és tres vegades la del conjunt de l'economia

- **Dataset**: `ocupacio_comerc.csv` (Eurostat `lfsa_egan22d`) **ampliat amb l'agregat `nace_r2=TOTAL`** — avui el fetcher només demana G47. Requereix tocar `fetch_ocupacio_comerc()` per demanar també TOTAL i desar-lo al CSV, i afegir la sèrie a `verify.py` (`_afegeix_ocupacio_edat`). **Sense aquesta integració l'angle no es pot publicar**: qualsevol xifra seria ORFE al gate.
- **Xifra** (verificada amb crida real a l'API el 2026-09-13, pendent de repassar el dia que s'integri): pes dels 15-24 anys, bretxa UE-27 menys Espanya. **2025: comerç 5,8 punts vs conjunt de l'economia 1,7 punts → 3,3 vegades.** El 2008 era 1,4 vs 0,6 (2,4x); el 2016, 5,4 vs 3,1 (1,7x). El rati puja de forma sostinguda des del 2016.
- **Mecanisme**: desmunta l'objecció més òbvia a l'angle A8 ("això no és el comerç, és el mercat laboral espanyol"). Sí que hi ha una bretxa juvenil general a Espanya, però la del comerç és el triple i s'ha anat separant de la general. La bretxa del conjunt de l'economia s'ha anat tancant des del 2013 (3,3 → 1,7 punts); la del comerç, no al mateix ritme.
- **CAUTELA CRÍTICA — les dues lectures són certes i diuen coses oposades**: des del 2022, en punts absoluts el comerç ha tancat MÉS (−1,0p contra −0,7p del conjunt); en termes relatius el conjunt ha tancat més ràpid (−29% contra −15%), i per això el rati s'eixampla. No es pot escriure ni "el comerç millora més" ni "el comerç es queda enrere" sense dir quina mètrica es fa servir. Aquesta és la trampa de l'angle.
- **Bloc 3**: dues sèries de bretxa (comerç vs total economia) per anys clau, o el rati per any.
- **Estat**: LLIURE — però **no abans de la integració del fetcher**. És angle d'edició sencera, no nota al peu.

## A12 · El comerç paga un 14% menys que la mitjana de l'economia, i no s'ha mogut en deu anys

- **Dataset**: `eaes.csv` (INE, Enquesta Anual d'Estructura Salarial) — **ja és a `observatori-comerc/data/cache/` però NO es copia a l'snapshot ni el coneix `verify.py`**. Cal afegir-lo a `snapshot.py` i a `carrega_series()` abans de poder-lo publicar.
- **Xifra** (verificada contra el CSV el 2026-09-13): salari mitjà del comerç **24.137,40 €** el 2023 contra **28.049,94 €** del conjunt d'indústria, construcció i serveis: **−13,9%** (−3.913 €). La forquilla dels deu anys de sèrie (2014-2023) va de −12,5% a −15,0%: mai es tanca, mai s'eixampla gaire. Per sota només hi ha activitats artístiques, administratives, altres serveis i hostaleria (16.985,78 €).
- **CAVEAT DE COBERTURA OBLIGATORI**: l'EAES agrupa "Comercio" com a **secció G** (majorista + minorista + reparació de vehicles), no CNAE 47 pur. És el mateix problema de cobertura que la regla 14 de la casa amb l'EPA. Qualsevol ús exigeix la frase d'advertiment en el cos.
- **Mecanisme**: acompanya A8/A11 com a **hipòtesi etiquetada**, mai com a diagnòstic. El dataset diu què es paga; no diu res sobre per què els joves trien un sector o un altre. Formulació admissible: "una hipótesis posible, no verificable solo con estos datos, es que…".
- **Estat**: LLIURE com a suport d'A8/A11; no aguanta una edició sola.

## A13 · El cens de comerç perd empreses a tot arreu, i el rànquing no s'assembla al mapa de la renda

> **Estat: RESERVAT — NO TRIAR.** Angle preparat i verificat, retirat de la
> circulació el 2026-09-20 per decisió editorial. **El model no l'ha de
> seleccionar** mentre aquesta línia hi sigui. Qui el reprengui ha de llegir
> abans la nota d'ús que hi ha al final de la fitxa.

- **Dataset**: `cens_ccaa.csv` a l'snapshot (origen `empreses.csv`, INE DIRCE, CNAE 47 per CCAA, sèrie 2008-2025, foto a 1 de gener)
- **Xifra** (finestra neta 2023-2025, verificada contra el CSV el 2026-09-19): Espanya **−4,0%** (393.287 → 377.471). Perden més: Astúries −6,8%, País Basc −6,2%, Castella i Lleó −6,0%, Cantàbria −5,9%, Galícia −5,8%. Perden menys: Balears −1,1%, Madrid −1,9%, Navarra −2,0%, la Rioja −2,8%, Catalunya −2,9%.
- **Mecanisme**: les disset comunitats perden empreses; l'única cosa que varia és el ritme, i el rànquing no segueix cap eix obvi. A dalt hi ha Balears i Madrid, que no s'assemblen en res excepte en pressió de demanda sobre el local; a baix hi ha la cornisa cantàbrica sencera, que comparteix piràmide d'edat i no densitat ni renda. La lectura defensable és demogràfica abans que comercial: on la població envelleix i no es reposa, el cens es buida al ritme de les jubilacions sense relleu. La caiguda no és un indicador de salut del comerç sinó de relleu.
- **Bloc 3**: barres de variació acumulada 2023-2025 per CCAA (la sèrie ja la construeix `verify.py`, o sigui que el rànquing sencer ancora).
- **Dues cauteles que no es negocien**:
  1. **Compta EMPRESES, no locals.** Un traspàs no surt del cens; un tancament de local d'una empresa amb dos locals, tampoc. Cap frase pot fer servir aquesta font per parlar de locals buits, de rotació ni de qui ocupa un baix.
  2. **Trencament de sèrie 2022→2023**: Espanya perd 35.318 empreses en un sol any, 2,8 vegades el moviment més gran de qualsevol altre any des del 2008 (−12.606 el 2011) i 4,9 vegades la mitjana (−7.230). Sembla canvi metodològic **no verificat**. Cap comparació pot travessar aquest salt: la finestra comença el 2023 i prou.
- **Matís obligatori si s'usa Catalunya**: l'avantatge català ve gairebé tot del 2024 (−1,05% contra −2,16% d'Espanya). El 2025 les dues sèries convergeixen (−1,88% i −1,90%). Presentar el −2,9% com a tendència catalana sostinguda seria fals.
- **No comparable amb Eurostat**: el BSD dona 426.519 empreses el 2023 i el DIRCE 393.287 el mateix any. Universos diferents. Si un text cita totes dues, ho ha de dir.
- **Per què no està cremat**: cap edició enviada ha usat el cens per CCAA com a xifra protagonista. El Núm. 17 va fer demografia empresarial amb Eurostat BSD (natalitat), que és una altra font i un altre mecanisme; el Núm. 20 el va tenir al borrador i no es va publicar.
- **NOTA D'ÚS quan es desbloquegi**: l'angle es va preparar en una setmana en què hi havia mesures d'administracions sobre locals comercials a la premsa, i el borrador el connectava amb elles. Aquesta connexió és la que queda descartada, no la dada. Si es reprèn, ha de sostenir-se sol —variació del cens i lectura demogràfica— sense citar ni avaluar cap mesura concreta de cap administració, i sense fer de la comparació entre comunitats un judici sobre les seves polítiques. El punt de partida net és el rànquing complet de les disset, no una comunitat destacada.

---

## Angles descartats deliberadament

- **Municipal** (`municipal.csv`): l'índex de capacitat comercial per municipi només té el sector G-I agregat, sense desglossar CNAE 47. No és publicable com a dada de comerç al detall.
- **Marges per branca** (`marges_branca_ine.csv`): gastat al Núm. 13.
- **ICM per modes de distribució**: gastat als Núm. 11 i 14.
- **ICM per CCAA**: gastat als Núm. 12 i 15.
- **CDMGE com a protagonista**: descartat el 2026-08-16 per finestra massa curta (15 dies volàtils). Val com a Bloc 3 amb el mes tancat.

Xifres verificades contra els CSV de `observatori-comerc/data/cache/` el
**2026-08-17**, excepte l'A13, verificada contra l'snapshot de la setmana
2026-09-21 el **2026-09-19**. Última actualització del fitxer: 2026-09-20.
