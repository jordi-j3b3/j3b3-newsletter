# Diccionario de datos — Observatorio del Comercio

> Documento de referencia. Se inyecta en el prompt del modelo en cada
> generación. Define el significado exacto de cada campo de las fuentes de
> datos. **El modelo NUNCA debe inferir el significado de un campo: si no
> aparece aquí, no se publica.**

---

## 1. Pulso diario — `pulso_diario.csv`

**Fuente**: INE, *Medición del Comercio Diario al por Menor de Grandes
Empresas* (CDMGE). Tabla INE 37808. Estadística experimental publicada
mensualmente desde enero de 2019, con detalle diario.

**Ámbito**: comportamiento de **grandes cadenas minoristas** españolas
(Mercadona, Inditex, El Corte Inglés, Carrefour, Lidl y similares).

**Frecuencia**: publicación mensual, granularidad diaria.

**Lag típico**: 25-55 días entre la fecha del dato y su publicación.

### Esquema

| Columna | Tipo | Descripción |
|---|---|---|
| `data` | fecha ISO `YYYY-MM-DD` | Día al que se refiere la observación |
| `indicador` | string | Uno de los 5 indicadores listados abajo |
| `valor` | float | Valor del indicador para ese día, en porcentaje |

### Significado de cada indicador

- **`tasa_anual`**: tasa anual de las ventas diarias acumuladas. Variación
  porcentual respecto al mismo periodo del año anterior. **Es el indicador
  principal del Observatorio** (es el que se muestra por defecto en la
  página "Pols diari"). Es el más comparable con datos macro.

- **`tasa_mensual`**: tasa mensual de las ventas diarias acumuladas.
  Variación porcentual respecto al mes anterior. Útil para detectar
  inflexiones a corto plazo, pero ruidoso por estacionalidad.

- **`pct_sobre_mes`**: porcentaje diario de ventas acumuladas sobre las
  ventas totales del mismo mes. Indica cuánto del mes se ha vendido a fecha
  i. Por construcción tiende a 100 al final del mes. **No usar como
  indicador de crecimiento**: es una métrica de progresión, no de variación.

- **`pct_vs_anterior_anual`**: porcentaje diario de ventas acumuladas al
  día i sobre las ventas totales del mismo mes del año anterior. Es una
  proyección parcial respecto al año previo.

- **`pct_vs_anterior_mensual`**: porcentaje diario de ventas acumuladas al
  día i sobre las ventas totales del mes anterior. Equivalente al anterior
  pero contra el mes precedente.

### Aviso interpretativo crítico (citar siempre que se use)

> La serie CDMGE refleja **grandes cadenas**, que son **menos sensibles a
> las desaceleraciones cíclicas** que el pequeño comercio (efecto refugio
> en precio, fidelización, programas de marca). En recesiones, el pequeño
> comercio sufre más. Por tanto, el CDMGE puede ser un **indicador de
> suelo del ciclo, no de la media sectorial**.

Implicación editorial: si la newsletter usa CDMGE como "termómetro del
comercio español", debe contextualizarse que mide **el comportamiento del
oligopolio retail**, no del comercio en su conjunto.

---

## 2. Pulso europeo — `pulso_europeo.csv`

**Fuente**: Eurostat, serie `sts_trtu_m` (Turnover and volume of sales in
wholesale and retail trade). Variable: `index_volum` (índice de volumen
de ventas minoristas, base 2021 = 100).

**Ámbito**: ventas minoristas excluyendo vehículos de motor
(NACE Rev. 2, G47).

**Frecuencia**: mensual.

**Lag típico**: 40-50 días.

### Esquema

| Columna | Tipo | Descripción |
|---|---|---|
| `pais` | string (catalán) | Nombre del país: `Espanya`, `Alemanya`, `Franca`, `Italia`, `Eurozona`, `Paisos Baixos`, `Belgica`, `Portugal`, `UE-27` |
| `pais_codi` | string | Código Eurostat: `ES`, `DE`, `FR`, `IT`, `EA20`, `NL`, `BE`, `PT`, `EU27_2020` |
| `periode` | string `YYYY-MM` | Mes al que se refiere la observación |
| `index_volum` | float | Índice de volumen de ventas, base 2021 = 100 |
| `yoy` | float o vacío | Variación interanual en porcentaje. Vacío en los primeros 12 meses de la serie |

### Norma de localización al castellano

| Catalán (CSV) | Castellano (newsletter) |
|---|---|
| Espanya | España |
| Alemanya | Alemania |
| Franca | Francia |
| Italia | Italia |
| Paisos Baixos | Países Bajos |
| Belgica | Bélgica |
| Portugal | Portugal |
| Eurozona | Eurozona |
| UE-27 | UE-27 |

---

## 3. Recopilación de prensa — `recopilacion_prensa.md`

**Fuente**: agregación de 12 feeds RSS sectoriales y generalistas, capturados
en vivo por `modules/press.py` del Observatorio en el momento del snapshot.

**Frecuencia**: real-time. El snapshot congela la ventana de los últimos
7 días desde la fecha de captura.

### Campos de cada entrada

| Campo | Descripción |
|---|---|
| `data` | Fecha de publicación de la noticia (`YYYY-MM-DD`) |
| `font` | Nombre legible del medio |
| `font_id` | Identificador interno del feed |
| `area` | `multisector`, `alimentacio` o `institucional` |
| `tipus` | `sectorial`, `generalista`, `institucional` o `agregador` |
| `titol` | Titular original (no modificable) |
| `snippet` | Extracto o resumen del feed (limitado a ~240 caracteres) |
| `link` | URL canónica de la noticia |

### Regla de citación en la newsletter

- El titular se cita **literalmente**, sin reformular.
- El medio se cita por su `font` (nombre legible).
- La fecha se cita en formato "DD de mes" (ej.: "8 de mayo").
- **Si el titular original no admite lectura editorial propia, la noticia
  no entra en el bloque 2**.

### Fuentes posiblemente incompletas

- **Modaes**: feed omitido por anti-bot. La moda se cubre vía Alimarket
  non-food, Diffusion Sport y Google News.
- **Google News (agregadores)**: a veces devuelve fragmentos vacíos.
- **El Economista**: solo accesible vía Google News.

**Consecuencia editorial**: si una semana hay menos de 3 noticias con
ángulo editorial defendible, **placeholder explícito** en el bloque 2 (no
rellenar con noticias de calidad inferior).

---

## 4. Productivitat — `productivitat.csv`

**Fuente**: INE, *Encuesta Anual de Empresas* + *Cuentas de las empresas*, sector CNAE 47.

**Ámbito**: totes les empreses del comerç minorista espanyol.

**Frecuencia**: anual. Lag típico: 12-18 mesos.

### Columnes rellevants per a la newsletter

| Columna | Tipus | Descripció |
|---|---|---|
| `any` | int | Any |
| `cost_laboral_per_ocupat` | float | Cost laboral mitjà per ocupat (€/any) |
| `cost_laboral_hora` | float | Cost laboral per hora treballada (€/hora) |
| `quota_salarial` | float | Proporció del cost laboral sobre el valor afegit (0-1) |
| `marge_brut` | float | Marge brut sobre vendes (0-1) |
| `productivitat_va_hora` | float | Valor afegit per hora treballada (€/hora) |
| `gastos_personal_constants` | float | Despeses de personal en euros constants |

### Avís interpretatiu

La `quota_salarial` indica quant de cada euro de valor afegit va a costos laborals. Si creix, o els marges cauen o la productivitat ha de compensar. Dada estructural, no coyuntural. Citar com "INE, comptabilitat d'empreses" — sense mencionar el codi de l'enquesta.

---

## 5. Ocupació — `ocupacio_comerc.csv`

**Fuente**: Eurostat, *Labour Force Survey* (LFS), sector NACE G47.

**Ámbito**: ocupats al comerç minorista per país, sexe i tram d'edat.

**Frecuencia**: anual.

### Esquema

| Columna | Tipus | Descripció |
|---|---|---|
| `pais` | string (català) | Nom del país |
| `pais_codi` | string | Codi Eurostat (`ES`, `EU27_2020`, etc.) |
| `any` | int | Any |
| `sex` | string | `F` (dones), `M` (homes), `T` (total) |
| `edat` | string | Tram d'edat (p.ex. `15-24`, `25-54`, `65+`) |
| `ocupats_milers` | float | Ocupats en milers |

### Norma d'ús

Filtrar sempre `pais_codi='ES'` i `sex='T'` per al total espanyol. Dada d'estructura, no de cicle curt. Citar com "Eurostat, enquesta de força de treball".

---

## 6. IPC — `ipc.csv`

**Fuente**: INE, *Índice de Precios de Consumo* — índex general espanyol.

**Ámbito**: economia espanyola en conjunt (no específic del sector retail).

**Frecuencia**: mensual.

### Esquema

| Columna | Tipus | Descripció |
|---|---|---|
| `any` | int | Any |
| `mes` | int | Mes (1-12) |
| `ipc` | float | Índex (base de referència fixa) |

### Avís d'ús

Útil per comparar l'evolució de costos laborals amb la inflació general. No citar com "IPC del comerç": és l'índex general. Citar com "INE, IPC general".

---

## 7. Reglas editoriales de referencia a las fuentes

Las referencias técnicas y metodológicas (códigos de serie, bases de índice,
números de tabla) **no se citan en el cuerpo de los bloques editoriales**.

La fuente se nombra siempre por su forma legible:
- "Eurostat" (no "Eurostat sts_trtu_m" ni "Eurostat, base 2021=100")
- "INE" (no "INE tabla 37808" ni "INE CDMGE")
- El nombre legible del medio para las noticias, tal como aparece en `font`
  (Distribución Actualidad, Expansión, Cinco Días, etc.)

El detalle técnico se reserva al pie de "Fuentes" al final del email, que
compose.py compone automáticamente. El redactor no debe escribirlo en el
cuerpo.

### Ejemplos

- ❌ "según Eurostat (serie sts_trtu_m, índice base 2021=100)"
- ❌ "el CDMGE de INE (tabla 37808) muestra..."
- ✅ "según Eurostat"
- ✅ "el indicador del INE sobre grandes cadenas muestra..."

---

*Documento vivo. Se actualiza si la estructura de los datos cambia en el
Observatorio o si se añaden nuevas fuentes.*
