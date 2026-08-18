# Perfil d'estil operatiu — prosa de Jordi Bacaria

> Document de calibratge per a qualsevol redacció signada per Jordi (articles
> d'opinió, columnes, tesis editorials, textos de presentació). Complementa
> `config/estil_editorial.md`, que fixa la veu del butlletí; aquest fitxer és el
> perfil mesurat, amb els paràmetres concrets que s'han de reproduir.

## 0. Fonts d'aquest perfil, i què queda exclòs

Construït sobre:

1. Els fragments A–H de `config/estil_editorial.md`, secció 1: dos informes
   signats (2019, 2023) i quatre peces d'opinió/crònica de 2017 i 2025, totes
   confirmades per Jordi com a 100% seves i anteriors a l'ús d'IA al despatx.
   Són l'única mostra del registre **columna** que és íntegrament seva.
2. L'historial complet de `config/tesi_setmana.md` (`git log -p --all`, set
   versions recuperades, Núm. 12 a 15): 186 frases de prosa analítica seva. És
   la mostra gran, i és la base de les mesures de la secció 1.
3. L'historial de `config/noticies_editor.md`: notes curtes d'angle editorial.
4. La secció 4 de `estil_editorial.md`, «Patrons a evitar», que és feedback seu
   directe sobre text que no li sonava propi.

**Excloses expressament les edicions publicades d'El Pulso de la semana.** Les
genera el pipeline amb Sonnet a partir de la tesi; són el producte, no la mà.
Calibrar-hi és l'error típic i produeix el to que Jordi rebutja.

Cautela sobre la font 2: alguns commits de tesi porten `Co-Authored-By` de
models. La tesi és dictada i corregida per ell (les correccions manuals hi són
visibles al log), però on hi hagi conflicte entre la tesi i els fragments A–H,
manen els fragments: allà l'autoria és certa i el gènere és el mateix que el
d'un article d'opinió.

Registres: **informe** (tercera persona, zero metàfora, tota recomanació
condicionada a norma o dada) i **columna** (el d'aquest perfil). No s'han de
barrejar, i no s'ha de forçar el registre informe sobre una peça signada.

## 1. Mesures de frase i puntuació

Sobre les 186 frases de la mostra de tesis:

| Paràmetre | Valor | Com aplicar-ho |
|---|---|---|
| Paraules per frase, mitjana | 21,6 | No baixar a un ritme de frases curtes encadenades |
| Mediana | 19 | La frase típica és mitjana-llarga, amb una subordinada |
| Percentil 10 / 90 | 9 / 36 | Alternança real: hi ha frases de 9 i frases de 36 |
| Frase més llarga de la mostra | 74 | Les frases molt llargues són legítimes si són enumeratives |
| Frases de 8 paraules o menys | 9% | Una de cada onze. La frase curta és puntuació, no ritme |
| Frases de 35 o més | 10% | Mateixa proporció que les curtes |
| Dos punts | ~1 cada 2 frases | És el signe de la casa |
| Guió llarg | ~1 cada 6 frases | Per a l'aclariment o la conseqüència |
| Punt i coma | ~1 cada 27 frases | Rar, i sempre per aparellar dues xifres simètriques |
| Parèntesi | freqüent | Per quantificar de passada, no per divagar |

Regla operativa: **els dos punts són el motor de la frase.** L'estructura
canònica és enunciat + dos punts + la càrrega. «El comerç minorista espanyol ja
ha perdut ocupació, però no l'ha destruïda: l'ha cedida.» / «I això té data de
caducitat: acaba quan acaba la temporada.» Si un paràgraf no en té cap, sona a
un altre autor.

## 2. Estructura i subordinació

- **Subordinació moderada, encadenada per causa i no per contrast.** Una
  principal, una subordinada, i la conseqüència entra amb guió llarg o dos
  punts. Rarament tres nivells d'encaix.
- **El «però» va dins de la frase, no obre frase nova.** El gir es fa al mig:
  «ha perdut ocupació, però no l'ha destruïda».
- **«I» inicial per a la conseqüència que remata**: «I això té data de
  caducitat», «I passa mentre Balears capta el 21,8%...». És deliberat i
  apareix un parell de vegades per peça.
- **Enumeració de causes en tricolon, sovint amb sumands explícits**:
  «estructura de mercat laboral + base industrial + renda disponible real».
- **Parell condicional curt com a cadència**: «On hi ha aquestes tres coses, el
  comerç minorista resisteix. On no, cau.» Va seguit d'una imatge que la tanca:
  «El mapa del retail ja no és pla.»
- **Senyalització explícita de l'estructura quan l'argument té parts**: «Anem
  per parts», «En primer lloc / En segon lloc / En tercer lloc». No es deixa
  implícit.
- **Subtítols temàtics curts** dins d'una peça llarga (dues a quatre paraules,
  nominals: «El concepte», «Posicionament», «El present»). Mai un subtítol que
  sigui una frase declarativa amb subjecte i verb: això és tic d'IA.

## 3. Connectors i frases-frontissa habituals

D'ús freqüent i propi: *Anem per parts.* · *En primer lloc / En segon lloc.* ·
*Convé no exagerar…* · *Cal dir-ho en una frase.* · *Val la pena…* · *El
mecanisme és…* · *La pregunta rellevant no és X, sinó quan i a qui primer.* ·
*Als seus propis termes…* · *Tot i això…* · *Ja veurem fins on arriba…*

Matís important sobre «no és X, sinó Y»: **només s'admet per redefinir la
pregunta**, no com a fórmula de tancament ni com a contrast decoratiu. «La
pregunta rellevant no és si el xoc arribarà al retail, sinó quan i a qui
primer» és seu. «El fre no és sectorial. És selectiu» no ho és.

## 4. Com introdueix les dades

Aquesta és la part més reconeixible i la que més es falseja.

1. **Cap xifra sense mecanisme, cap mecanisme sense xifra.** «La cotització
   baixa un 7%. La causa s'explica en l'anunci de la companyia…» Les dues
   meitats sempre juntes.
2. **La xifra va amb la seva base i el seu període dins de la mateixa frase**,
   sovint entre parèntesis: «el Brent cotitza cap als 90 dòlars (24% per sobre
   de l'inici de la guerra amb l'Iran al febrer)».
3. **Xifres en paral·lel aparellades amb punt i coma**, quan la comparació és
   l'argument: dues sèries, mateixa unitat, mateixa estructura sintàctica.
4. **Comentari sec després de la xifra, mai abans**: «Una xifra gens
   menyspreable.» L'adjectivació va després del número i és breu.
5. **Precisió sense arrodonir per estètica.** 23.562 euros, no «uns 24.000».
   Un decimal com a màxim, i només si la lectura ho demana: −2,41%, 13,4%.
6. **Cobertura i límits declarats al cos, no en una nota.** Si la sèrie d'ocupats
   és de CNAE 47 i la d'atur és de tota la secció G, ho diu. Si dues fonts
   divergeixen, ho diu i explica per què («mesuren coses diferents, l'una
   preguntant a les llars i l'altra a les empreses»), en lloc de triar en
   silenci la que convé a l'argument. Aquesta honestedat explícita és un tret
   d'estil, no només de mètode.
7. **De la xifra al sector**: la dada concreta desemboca sempre en una lectura
   de sector o de política, mai es queda en el número.
8. **Font amb nom i afiliació completa** quan cita algú: «l'economista i
   col·lega del Col·legi d'Economistes de Catalunya Manuel Amado Martí».

## 5. Obertures

- Entra per un **fet concret, datat i verificable**, o per una **xifra amb
  data**. Mai per una generalitat ni per context abstracte.
  «L'endemà de fer públics els millors comptes anuals de la seva història, la
  cotització baixa un 7%.» / «El març s'explica amb un president nord-americà
  desbocat.»
- Si obre amb **pregunta**, la pregunta és bastida i es respon immediatament,
  frase a frase, en el mateix bloc. «¿Qué hay detrás de esta marca?» seguit de
  la resposta sistemàtica. Cap pregunta retòrica sense resposta.
- El titular tendeix a ser **una afirmació concreta i seca**, sovint amb un
  substantiu inesperat, no una pregunta ni un joc de paraules.

## 6. Tancaments

- **Frase aforística curta, l'última paraula sobre el tema.** No és un resum ni
  una recapitulació.
- Tres formes que li són pròpies:
  - **Paral·lelisme de contrast** amb dos subjectes reals: «las grandes marcas
    aportan caché a la ciudad, las PIMEs aportan el alma».
  - **Vocatiu o apel·lació seca**: «Posa-li, Barcelona.»
  - **Assenyalar el que no consta**: dir què no diu la font, la llei o l'autor
    citat, en lloc d'afirmar una conclusió pròpia.
- Del micro al macro: el cas concret del cos acaba en implicació de sector o de
  política local, gairebé sempre al paràgraf final.

## 7. Persona verbal

- **Base impersonal i tercera persona.** «Convé no exagerar», «es llegeix
  millor al compte de resultats», «les dades sostenen».
- **Primera persona del singular, una vegada per peça com a màxim**, i al punt
  de màxim judici personal: «bajo mi punto de vista», «em sembla obligada una
  concessió». Mai com a crossa de paràgraf.
- **«Nosaltres» només institucional** («l'Observatori ha d'explicar…»), mai com
  a plural editorial per emetre opinions.
- **Apel·lació directa al lector, puntual**: «El lector pot deduir que…». Un
  recurs per peça.
- **Concessió abans d'afirmar, dins la mateixa frase**: «Aquest plantejament pot
  agradar més o menys, però…». Reconeix l'objecció i continua; no li dedica un
  paràgraf a part.

## 8. Registre lèxic

- **Mixt i deliberat: terme tècnic + col·loquialisme culte.** EBITDA, EBE sobre
  vendes, integració vertical, percentil, marge de contribució conviuen amb
  «peccata minuta», «desbocat», «estirabots», «veure les orelles al llop»,
  «apagar el foc amb benzina». Cap peça sencera en un sol registre.
- **Metàfora i dita popular: una o dues per peça, i sempre per condensar un
  argument.** «No arriba al lineal», «el matalàs previ», «l'euro turístic». Si
  no n'hi ha cap que encaixi de forma natural, no se'n força cap.
- **Ironia seca, mai acudit senyalat.** L'humor és a la brevetat i al
  distanciament: «Ja veurem fins on arriba l'amenaça.»
- Algun castellanisme del parlar professional li és natural en esborrany
  («colchón», «frenat»); al text final, forma catalana correcta.
- **Riquesa lèxica**: no repeteix la paraula clau dins del mateix bloc.
- **Terminologia**: noms de llei complets però sense articulat; per a Smith,
  «camàlic» o «bastaix» per a *porter*, mai «porter».

## 9. Tics propis (reproduir-los)

- Dos punts com a signe dominant.
- «Anem per parts» abans d'una enumeració de tres.
- Comentari sec de tres paraules just després d'una xifra gran.
- Guió llarg per a la conseqüència que no cabia a la frase.
- Parèntesi que quantifica de passada.
- «I» inicial per rematar.
- Dir en veu alta quan una font contradiu una altra.
- Tancar assenyalant el que la font **no** diu.
- Predicció datada, amb llindar numèric i falsable, ancorada en una tendència
  ja en marxa i no en especulació: abans de projectar, diu quina dada d'avui la
  sosté.

## 10. Què NO fa (llista de veto)

- **«No A. Sí B.»** — negació i afirmació contrària en dues frases curtes
  simètriques. Veto explícit seu. «El fre no és sectorial. És selectiu.» Fora.
  Alternativa: construir la cadena causal i deixar que el judici emergeixi al
  final.
- **«No només… sinó també»** com a crossa.
- **«X ho entén; qui no ho faci perdrà quota»** — sentència genèrica sobre qui
  no fa les coses bé, que no afegeix informació a la primera meitat.
- **«La contradicció és només aparent»** i qualsevol meta-avís del que ve a
  continuació. Explica directament; no anuncia que explicarà.
- **Autoqualificar-se**: «una anàlisi honesta mostra que», «cal dir-ho
  clarament».
- **Pregunta retòrica sense resposta** com a ganxo.
- **Subtítols que són frases declaratives completes.**
- **Estructura idèntica peça rere peça** (mateix nombre de blocs, mateixa
  cadència de tancament).
- **Intensificadors buits**: clau, crucial, profundament, absolutament.
- **Arrodonir per estètica**, i més d'un decimal.
- **Xifra sola** sense mecanisme, o mecanisme sense xifra.
- **Metàfora nova decorativa a cada paràgraf.**
- **Emojis**: cap, en cap suport.
- **Amagar una divergència de font** o triar en silenci la sèrie que convé.
- **Barrejar dades o referències de projectes diferents** dins d'una mateixa
  peça.

## 11. Prova ràpida abans de lliurar

1. Hi ha dos punts fent feina, aproximadament un cada dues frases?
2. Cada xifra porta base, període, font i mecanisme?
3. Queda alguna estructura «No A. Sí B.»? Reescriure-la com a cadena causal.
4. Els subtítols són nominals i curts?
5. La primera persona apareix una vegada, i al punt de màxim judici?
6. El tancament és una frase que el lector podria citar de memòria?
7. Hi ha una o dues metàfores en tota la peça, i condensen argument?
8. S'ha dit en veu alta el límit de les dades, al cos i no en una nota?
