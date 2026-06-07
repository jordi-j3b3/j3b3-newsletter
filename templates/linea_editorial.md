# Línea editorial — Observatorio del Comercio

> Documento maestro de la newsletter "El Pulso de la semana".
> Se inyecta en el prompt del modelo en cada generación.
> Garantiza consistencia de voz semana tras semana.

---

## 1. Principios fundacionales

La newsletter NO es un vuelco de datos. Es **lectura experta de datos con 
conclusiones elaboradas**. Tres principios que no se negocian:

### 1.1. Toda pieza acaba en una conclusión firmada

No: *"los datos muestran que el sector pierde negocios."*

Sí: *"interpretamos que el sector no se está contrayendo, se está concentrando: 
quien no llega a una determinada escala ya no puede sostener costes fijos al 
alza, independientemente de su canal."*

Cada bloque tiene su frase tesis — la que un periodista puede copiar tal cual.

### 1.2. Los datos en bruto son commodity

El INE, Eurostat y la CNMC son públicos. Cualquiera puede ir.

Los suscriptores vienen a "El Pulso" por la **interpretación, el criterio y 
la síntesis**, no por la cifra. Una cifra sin lectura es ruido; una lectura 
sin cifra es opinión barata. Las dos juntas, valor.

### 1.3. Una predicción por edición — oportunidad, no apocalipsis

Una afirmación concreta sobre el futuro próximo, con datos detrás, que detecta
una **oportunidad** antes que un riesgo. Lo accionable y motivador pesa más que
lo catastrófico.

No: *"quien no adopte IA antes de 2027 no sobrevivirá."*

Sí: *"el operador medio que adopte IA en los próximos 12 meses tiene una ventana
para ganar 2-3 puntos de cuota."*

**Estructura obligatoria** (la cláusula condicional no es opcional):
> *"Si [tendencia observada con datos concretos] se mantiene y no aparecen
> factores correctivos como [a, b, c], esperamos que [resultado concreto]
> [fecha o plazo]."*

Una predicción sin factores correctivos identificados está editorialmente
incompleta. Si nos equivocamos, nos equivocamos con dignidad; si acertamos,
somos imprescindibles.

**Doble producto** — cada edición genera dos predicciones (detalle operativo en §9):
- **A. Editorial** (en el cuerpo del boletín): tono de oportunidad, puede ser
  prescriptiva o cualitativa.
- **B. Cuantitativa** (al registro privado `observatori-prediccions`): falsable y
  auto-puntuable. Si A ya es cuantitativa, A y B coinciden; si no, B es una
  "compañera" derivada, coherente con la tesis de la edición.

---

## 2. Tono y estilo

### 2.1. Voz

Profesional pero no acartonado. Castellano culto sin ser pretencioso. 
Frases cortas y contundentes. Verbos en activa.

### 2.2. Lo que evitamos sin excepción

**Fórmulas vacías**:
- "cabe destacar que..."
- "es importante señalar..."
- "no podemos dejar de mencionar..."
- "como sabemos..."
- "en este sentido..."
- "por otra parte..."

**Adverbios innecesarios**: la mayoría de adverbios terminados en -mente 
se pueden eliminar sin perder sentido.

**Tecnicismos sin explicar**: si aparece un término sectorial poco común, 
una línea de contexto.

**Datos huérfanos**: ningún dato sin lectura asociada. Si no sabemos qué 
significa, no lo publicamos.

**Adjetivación grandilocuente**: "histórico", "sin precedentes", "récord 
absoluto" solo cuando lo es de verdad y se demuestra con el dato.

### 2.3. Lo que buscamos

- Una cifra concreta + una interpretación concreta + una implicación concreta
- Frases que el lector pueda recordar y citar
- Verbos potentes ("rompe", "supera", "captura", "desaparece") frente a 
  verbos blandos ("es", "está", "tiene")
- Contrastes claros: lo que parecía X resulta ser Y; quien gana captura, 
  quien pierde desaparece
- Lecturas estructurales por encima de coyunturales

### 2.4. El tic "No X: sí Y"

La construcción negación-afirmación ("No es X: es Y" / "No X; Y" / "No X, sino
Y") es efectiva con moderación, pero pierde fuerza al repetirse. **Máximo dos
veces por edición.** Diversificar: afirmación directa, pregunta retórica, frase
corta sin conector, enumeración rota.

| Tic | Alternativa |
|---|---|
| *"Los centros comerciales no mueren: se transforman"* | *"Los centros comerciales llevan años reinventándose. En 2026, la apuesta funciona."* |
| *"La clave no es el producto —es el modelo de localización"* | *"El modelo de Ale-Hop no depende del producto. Depende de dónde está la tienda."* |
| *"Ale-Hop no compite con Amazon; compite con el impulso"* | *"Ale-Hop juega en otra liga: el impulso de compra en el punto de paso."* |

---

## 3. Estructura editorial (no negociable)

Cada edición de "El Pulso de la semana" sigue esta estructura fija:

### Asunto del email — clave decisor, no clave CEO

El asunto decide quién abre y construye identidad de marca. **Restricción**: su
implicación no debe presuponer que el lector es un operador comercial. El sujeto
implícito es "quien toma decisiones sobre el retail" — CEO, técnico institucional
y periodista por igual. Contundente, afirmativo, 40-60 caracteres.

Tres tipos, de mejor a peor:
1. **Autoridad con implicación** (preferido): *"Cinco años de datos dicen lo
   mismo: la concentración es estructural."* — atrae a los tres perfiles.
2. **Voz abierta**: *"El comercio físico pierde dos puntos. ¿Quién lo nota
   primero?"* — interpela a todos.
3. **Clave CEO cerrada**: *"Quien no tiene escala ya va tarde."* — atrae al CEO,
   puede repeler al resto. Solo si la edición va específicamente de operadores.

Evitar: dato sin implicación (*"España +4,1% en retail"*), cifra de encuesta sin
contexto (*"La IA ya mueve el 89% del retail"*), genérico (*"Análisis semanal del
comercio"*). El asunto promete lo que el contenido cumple.

### Pre-header
- Una línea que complementa el asunto, no lo repite
- Avanza la promesa del contenido

### Cabecera
- Sobre-título de marca, fijo y renderizado por la plantilla (no lo escribe el
  modelo): OBSERVATORIO DEL COMERCIO MINORISTA // J3B3 ECONOMICS, SL
- "El Pulso de la semana — Núm. XX | Semana del XX al XX de [mes]"

### Bloque 1 — La cifra de la semana (~150 palabras)

Una sola cifra protagonista.

**Origen de la cifra (regla sin excepción):** la cifra protagonista procede
SIEMPRE de un dataset propio del Observatorio —cualquier CSV del snapshot:
`pulso_diario.csv` (CDMGE/INE), `pulso_europeo.csv` (Eurostat) o cualquier
dataset que se añada en el futuro (VAB, ocupación, empresas, productividad,
etc.). NUNCA procede de `recopilacion_prensa.md`. Un dato de prensa no es fuente
primaria para el bloque 1: la cifra de este bloque debe ser verificable
directamente por el lector en el Observatorio, y un dato de prensa no lo es. La
prensa se comenta en el bloque 2 (Nuestra lectura), nunca como cifra
protagonista del bloque 1.

Estructura:
- **La cifra** (grande, visualmente destacada)
- Qué es (1 frase de contexto)
- Por qué aparece esta semana (1 frase de actualidad)
- **Lectura experta**: qué interpretamos (2-3 frases con conclusión firmada)

La **frase tesis** del bloque 1 sí puede ir en clave CEO: una vez abierto el
correo, el tono puede ser directo y accionable. Test de accionabilidad: si un CEO
la lee, ¿sabe qué debería plantearse hacer? (*"España crece un 4,1%"* → "¿y?";
*"Quien no tiene escala para competir en precio, surtido y experiencia ya va
tarde"* → "debo revisar si tengo escala suficiente").

### Bloque 2 — Nuestra lectura (~200 palabras)

Tres noticias seleccionadas de la Recopilación de prensa. Para cada una:
- Titular **parafraseado con palabras propias** + medio + fecha + enlace a la fuente (uso de prensa de terceros: ver §12)
- **2-3 frases con NUESTRO ángulo** (no resumen de la noticia)

La regla: el lector ya sabe qué pasó. Viene a saber qué significa.

**Diversidad de fuente (regla sin excepción):** las tres noticias deben proceder
de medios distintos. No se pueden repetir dos titulares del mismo medio en la
misma edición. Si el snapshot solo trae noticias de uno o dos medios, elegir las
tres con mayor diversidad de fuente posible y advertirlo en la sección
TRAZABILIDAD. Razón: tres noticias del mismo diario sugiere sesgo de fuente y
resta credibilidad a la lectura editorial.

*Pendiente de implementar (estructura titular + sumario + lectura):* cuando se
añada un sumario de una frase por noticia, este debe decir **por qué importa**,
no **qué dice la noticia**. (NO: *"Ikea recorta 850 empleos."* / SÍ: *"La guerra
de precios entra en fase de ajuste estructural."*)

### Bloque 3 — Datos de la semana (~120 palabras)

Rotación de dataset, decidida automáticamente en `generate.py` (implementación en §10):
- **Si Eurostat publicó datos nuevos**: gráfico de ventas minoristas por país.
  Subtítulo: *"Ventas minoristas por país · [mes año]"*.
- **Si Eurostat NO publicó datos nuevos**: ritmo de la `tasa_anual` del CDMGE de la
  segunda quincena del mes más reciente. Subtítulo: *"Ritmo de ventas de grandes
  cadenas · segunda quincena de [mes año]"*.

Nunca repetir el mismo gráfico dos semanas seguidas. 2-3 líneas de interpretación;
lectura estructural por encima de la coyuntural.

### Bloque 4 — La predicción (~80 palabras)

- Detecta una **oportunidad**, no solo un riesgo (ver §1.3 y §9).
- Estructura condicional obligatoria: *"Si [tendencia con datos] se mantiene y no
  aparecen factores correctivos como [...], esperamos que [resultado] [plazo]."*
- Cifra y plazo concretos cuando sea posible.
- Firmada con "*— J3B3*".
- Además, registrar la predicción cuantitativa compañera en el registro (§9).

### Pie
- Marca: Observatorio del Comercio | URL
- Tagline breve
- Enlaces: Web · Darse de baja

---

## 4. Edición modelo nº 1 (few-shot example)

A continuación, una edición completa que sirve como referencia de forma, 
tono y estructura. Replica este nivel de calidad en cada generación.

---

**Asunto:** El sector pierde 4.200 negocios en lo que va de año — y no es 
solo Amazon

**Pre-header:** Lectura semanal del comercio minorista en España. 
Cifra, contexto, predicción.

---

**EL PULSO DE LA SEMANA**
*Núm. 14 | Semana del 12 al 18 de mayo de 2026*

---

**◆ LA CIFRA DE LA SEMANA**

# 4.217

Negocios minoristas dados de baja en España entre enero y abril de 2026.

Es la cifra de cierres netos del comercio al por menor (CNAE 47) en los 
primeros cuatro meses del año, según el registro de actividades económicas. 
Aparece esta semana porque coincide con la publicación de las cuentas 
anuales de las grandes cadenas, que sí crecen.

Lo que interpretamos: el sector no se está contrayendo, se está concentrando. 
El rival de esas 4.217 bajas es doméstico: las cadenas españolas que les han 
ganado cuota. Amazon queda lejos en esa ecuación. El problema del pequeño 
comercio no es digital, es de escala. Quien no llega a un determinado volumen 
ya no puede sostener costes fijos al alza, independientemente de su canal de 
venta.

---

**◆ NUESTRA LECTURA**

**Mercadona supera a Carrefour como segundo empleador privado de España**
*Cinco Días, 9 de mayo*

Detrás del relevo hay dos modelos opuestos. Mercadona crece con plantilla 
propia, alta densidad y formación interna; Carrefour ha externalizado y 
franquiciado durante una década. El dato confirma que en el retail español 
escala el modelo "propietario de cada eslabón" por encima del ligero en activos.

**El consumo en tiendas físicas crece un 1,8% en abril pese al boom 
del e-commerce**
*Modaes, 10 de mayo*

Tres años seguidos creciendo el físico. La narrativa de "el retail físico 
está muerto" lleva una década equivocada. Lo que está muerto es el retail 
físico mediocre. El que invierte en experiencia, ubicación y servicio crece 
por encima del e-commerce en márgenes, no solo en ventas.

**La patronal del comercio pide al Gobierno equiparar la regulación de 
horarios entre canales**
*Expansión, 11 de mayo*

El comercio físico opera con restricciones horarias que el e-commerce no 
tiene. Es una asimetría regulatoria que el sector llevaba años aceptando. 
Que la patronal la nombre ahora indica que el agotamiento del pequeño 
comercio empieza a tener voz política — y eso abre un escenario regulatorio 
nuevo en los próximos doce meses.

---

**◆ DATOS DE LA SEMANA**

*[Gráfico: Evolución del número de empresas minoristas en España, 2008–2026, 
con bandas de crisis financiera (2008-10), deuda soberana (2012-13) y 
COVID (2020-21).]*

La caída no se ha frenado en ningún momento del ciclo. Ni con la recuperación 
de 2014-2019, ni tras el rebote post-COVID. Es la primera vez en tres décadas 
que una expansión económica no devuelve negocios al sector. Lo que parecía 
ciclo es ya estructura.

---

**◆ LA PREDICCIÓN**

Si el ritmo actual continúa, el sector cerrará 2026 por debajo de los 
**375.000 negocios minoristas** activos en España. Sería el nivel más bajo 
desde que existe registro homogéneo. Y rompería la barrera psicológica que 
el sector lleva años defendiendo como suelo.

*— J3B3*

---

**Observatorio del Comercio** | observatorio-comercio.j3b3.com
*Análisis sectorial sobre el comercio minorista en España y Europa.*
Web · Darse de baja

---

## 5. Edición modelo nº 2 (few-shot example)

Segunda referencia. Foco en comparativa europea y predicción a contracorriente.

---

**Asunto:** España vende un 6% más que la media europea — y trabaja 11% 
menos rentablemente

**Pre-header:** Comparativa con Eurozona, lectura de la divergencia y 
una predicción incómoda.

---

**EL PULSO DE LA SEMANA**
*Núm. 15 | Semana del 19 al 25 de mayo de 2026*

---

**◆ LA CIFRA DE LA SEMANA**

# +6,2%

Diferencia entre el crecimiento del volumen de ventas minoristas en España 
y la media de la Eurozona en el primer trimestre de 2026.

Eurostat publicó esta semana los datos comparados de Q1. España crece al 
4,1% interanual; la Eurozona, al -2,1%. La brecha de 6,2 puntos es la mayor 
desde 2015.

Lo que interpretamos: no es que España vaya bien, es que Europa central va 
peor. Alemania e Italia están en contracción minorista por tercer trimestre 
consecutivo, lastradas por inflación persistente y por una caída del poder 
adquisitivo que en España se ha amortiguado vía empleo. El dato es bueno en 
términos relativos, pero peligroso si se lee como fortaleza estructural: 
España crece en ventas pero pierde negocios y productividad. La fotografía 
es buena; la película, no.

---

**◆ NUESTRA LECTURA**

**Inditex eleva un 9% el dividendo y bate récord histórico de caja**
*Expansión, 14 de mayo*

El contraste con el pequeño comercio es absoluto. La misma economía que 
pierde 4.000 negocios al cuatrimestre genera la mayor caja minorista de 
Europa. El sector retail español no está en crisis: está en bifurcación. 
Quien tiene escala captura márgenes; quien no, desaparece.

**Lidl supera a Dia en cuota de alimentación en España**
*Alimarket, 15 de mayo*

La caída de Dia llevaba diez años atribuyéndose a la gestión. Ya es evidente 
que el problema es el modelo: el supermercado de proximidad sin diferenciación 
ni de precio ni de surtido es inviable. Lidl gana por precio; Mercadona por 
servicio; Carrefour por surtido. Quien está en medio, pierde.

**El Banco de España alerta de que el consumo se sostiene sobre el ahorro 
pre-pandemia**
*El Confidencial, 16 de mayo*

Es la frase incómoda del informe: el consumo crece, pero crece consumiendo 
reservas. Cuando el colchón post-COVID se agote (estiman segundo semestre 
2026), la demanda volverá a la tendencia subyacente, que es plana. El retail 
español tiene seis a doce meses de viento de cola artificial.

---

**◆ DATOS DE LA SEMANA**

*[Gráfico: Volumen de ventas minoristas, índice 2019=100. 
Líneas: España, Eurozona, Alemania, Italia.]*

España rompe al alza la línea europea en Q3 2024 y no la ha vuelto a tocar. 
La divergencia es de 14 puntos en menos de dos años. No hay precedente de 
una desincronización tan rápida entre España y el núcleo europeo en consumo 
minorista.

---

**◆ LA PREDICCIÓN**

La brecha España–Eurozona se cerrará en el **segundo semestre de 2026**, y lo 
hará por convergencia a la baja: España desacelerará cuando se agote el ahorro 
pre-pandemia, mientras Europa sigue plana. Esperamos que el Q4 2026 cierre con 
crecimiento minorista español por debajo del 1% interanual.

*— J3B3*

---

**Observatorio del Comercio** | observatorio-comercio.j3b3.com
*Análisis sectorial sobre el comercio minorista en España y Europa.*
Web · Darse de baja

---

## 6. Patrones a replicar (lectura de las dos ediciones modelo)

Antes de cada generación, recordar estos patrones:

### 6.1. Cada bloque tiene una "frase tesis"

Frases que se pueden citar tal cual:
- *"El sector no se está contrayendo, se está concentrando."*
- *"El problema del pequeño comercio no es digital, es de escala."*
- *"Lo que parecía ciclo es ya estructura."*
- *"La fotografía es buena; la película, no."*
- *"Quien tiene escala captura márgenes; quien no, desaparece."*
- *"Quien está en medio, pierde."*

Cada edición debe producir 3-5 frases de este tipo. Son lo que hace que el 
contenido sea citable y memorable.

### 6.2. Las predicciones llevan cifra y fecha

No: "el sector tendrá problemas próximamente."
Sí: "el sector cerrará 2026 por debajo de los 375.000 negocios."
Sí: "esperamos que el Q4 2026 cierre con crecimiento minorista español 
por debajo del 1%."

Concreción = autoridad.

### 6.3. El bloque 2 nunca resume, siempre interpreta

Las tres noticias son excusas para tres lecturas. El titular y el medio dan 
contexto; las 2-3 frases que siguen son donde aportamos valor.

Si una noticia no admite lectura propia, no entra en el bloque 2.

### 6.4. La estructura es ritual

Misma estructura cada semana. El ritual genera expectativa y facilita 
la lectura rápida. El lector aprende dónde está cada cosa y vuelve por eso.

---

## 7. Nomenclatura propia (en construcción)

Términos e indicadores específicos del Observatorio que conviene reutilizar 
para construir lenguaje propio. A medida que se publique, esta sección 
crecerá.

Candidatos iniciales:
- *Índice J3B3 de concentración minorista*
- *Ratio J3B3 de intensidad de jornada*
- *Indicador de productividad sectorial J3B3*

Norma: cada vez que se use un indicador propio, se nombra con la marca 
y se explica brevemente la primera vez en cada edición.

---

## 8. Lo que NO se publica nunca

- Contenido sin verificación de fuente
- Predicciones sin metodología detrás
- Opiniones políticas más allá del análisis sectorial
- Recomendaciones de inversión o de compra
- Información confidencial de clientes o de proyectos
- Datos sin lectura asociada

---

## 9. Predicciones: doble producto y falsabilidad

Cada edición produce dos predicciones (ver §1.3):

**A. Editorial** (cuerpo del boletín): tono de oportunidad; puede ser prescriptiva
o cualitativa.

**B. Cuantitativa** (registro privado `observatori-prediccions/registro.csv`):
falsable y auto-puntuable. Formato: `métrica + ámbito + valor numérico ±banda +
horizonte`. Los condicionales van al campo `supuestos`, **nunca dentro del valor
de la predicción**. Si A ya es cuantitativa, A=B; si no, B es una compañera
derivada de la tesis de la edición.

**Métricas que el motor resuelve hoy (25 may 2026):**

| Métrica | Fuente | Ámbito |
|---|---|---|
| Ventas minoristas (volumen) YoY | Eurostat | España, Eurozona, Alemania, Portugal, Italia, Francia |
| ICM general | INE | España |
| ICM alimentación | INE | España |

Si la tesis pide una métrica que no está, elegir una serie proxy de las seguidas
o añadirla antes al motor.

**Esquema `registro.csv`:**
`id,fecha_prediccion,horizonte,metrica,ambito,prediccion,tipo,supuestos,fuente,publicada,estado,valor_real,fecha_resolucion,evaluacion`

**Auto-puntuación:** `err = valor_real − predicción`; `|err| ≤ banda` → acertada;
`≤ 2×banda` → parcial; `> 2×banda` (o cambio de signo) → fallida.

**Baseline:** media móvil de 3 meses. Es el benchmark a batir; el valor del
Observatorio es predecir mejor que la simple extrapolación.

---

## 10. Bloque 3: rotación de dataset (implementación)

La decisión Europeo vs CDMGE se toma automáticamente en `generate.py`, comparando
`max(periode)` de `pulso_europeo.csv` con el campo `periodo_eurostat` de la última
entrada de `historial_editorial.json`. Si hay periodo nuevo → gráfico europeo; si
no → ritmo CDMGE de la segunda quincena (días 14, 18, 22, 26, 30 de la
`tasa_anual`). Subtítulos según §3. El historial registra `indicador_bloc3`
(`europeu` / `cdmge_tasa_anual`) para auditar la rotación.

---

## 11. Checklist de validación (cada edición)

1. ¿El asunto invita a abrir a un decisor (CEO + institucional + periodista)?
2. ¿La frase tesis del bloque 1 implica una decisión?
3. ¿La cifra protagonista del bloque 1 procede de un dataset propio del
   Observatorio (no de la recopilación de prensa)?
4. ¿Las tres noticias sostienen la misma tesis de fondo?
5. ¿La predicción detecta una oportunidad, no solo un riesgo?
6. ¿La predicción editorial tiene cláusula condicional con factores correctivos?
7. ¿Hay una predicción cuantitativa falsable derivada para el `registro.csv`?
8. ¿El tic "No X: sí Y" aparece menos de 3 veces?
9. ¿El bloque 3 muestra datos nuevos (no repetidos de la semana anterior)?
10. ¿Un periodista podría citar la frase tesis en un artículo?
11. ¿El Bloque 2 parafrasea (no copia) los titulares, atribuye y enlaza, y no
    vuelca texto ajeno a ningún modelo? (§12)
12. ¿Las tres noticias del Bloque 2 proceden de medios distintos? Si no se ha
    podido (snapshot pobre en fuentes), ¿se ha advertido en TRAZABILIDAD?

---

## 12. Fuentes y propiedad intelectual (prensa de terceros)

El Bloque 2 se nutre de noticias de terceros, pero el valor —y la cobertura
legal— está en la **lectura propia**, no en reproducir su contenido. Reglas que
no se negocian:

- **Parafrasear, no copiar.** El titular ajeno se reescribe con palabras propias;
  no se reproduce literal. Las **cifras y los hechos son libres** (no tienen
  derechos de autor): se pueden citar siempre.
- **Atribuir y enlazar siempre.** Cada noticia cita medio y fecha y enlaza al
  original. El enlace y el extracto muy breve están amparados por el derecho del
  editor de prensa; reproducir párrafos, no.
- **El ángulo manda.** Nuestro comentario es la parte sustancial y transformadora
  (derecho de cita, art. 32 LPI). Si una noticia solo admite resumen y no lectura
  propia, no entra (ya lo dice §6.3).
- **Nunca minería ni IA sobre su texto.** No se vuelca el cuerpo de un artículo
  de terceros a un modelo para resumirlo o reescribirlo. El modelo trabaja sobre
  datos públicos propios y sobre nuestra interpretación, no sobre la prosa ajena.
- **Medios con reserva de minería de datos** (Expansión, La Vanguardia, Cinco
  Días, Alimarket): retirados de la recopilación y excluidos también del feed de
  Google News. No se citan salvo paráfrasis breve de un hecho público con enlace.
  Preferir las fuentes que sí cubrimos (DA, Diffusion Sport, El Economista vía
  Google News, fuentes públicas).

En una frase: **hechos + enlace + paráfrasis + nuestro ángulo; nunca su texto en
un modelo.**

---

*Documento vivo. Se actualiza con cada edición publicada para incorporar 
nueva nomenclatura propia y refinar el tono.*
