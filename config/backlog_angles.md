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
- **Estat**: LLIURE

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

---

## Angles descartats deliberadament

- **Municipal** (`municipal.csv`): l'índex de capacitat comercial per municipi només té el sector G-I agregat, sense desglossar CNAE 47. No és publicable com a dada de comerç al detall.
- **Marges per branca** (`marges_branca_ine.csv`): gastat al Núm. 13.
- **ICM per modes de distribució**: gastat als Núm. 11 i 14.
- **ICM per CCAA**: gastat als Núm. 12 i 15.
- **CDMGE com a protagonista**: descartat el 2026-08-16 per finestra massa curta (15 dies volàtils). Val com a Bloc 3 amb el mes tancat.

Xifres verificades contra els CSV de `observatori-comerc/data/cache/` el
**2026-08-17**. Última actualització del fitxer: 2026-08-17.
