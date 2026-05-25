# Marca — Observatorio del Comercio Minorista

Identidad visual de J3B3 Consulting aplicada al producto Observatorio del Comercio Minorista. Estos activos son la fuente de verdad para newsletter, web, infografías y comunicaciones externas.

## Variantes

| Variante | Cuándo usar |
|---|---|
| `logo-observatorio` | Versión principal. Sobre fondos blancos o claros (#FFFFFF a #DDDDDD). |
| `logo-observatorio-blanc` | Versión blanca. Sobre fondos oscuros (#555555 o más oscuro). |
| `logo-observatorio-icon` | Solo símbolo. Favicons, avatares, espacios cuadrados < 100 px. |

## Formatos y resoluciones

```
svg/
  logo-observatorio.svg            (440×84 viewBox, navy)
  logo-observatorio-blanc.svg      (440×84 viewBox, blanco)
  logo-observatorio-icon.svg       (72×72 viewBox, navy)
png/
  logo-observatorio@1x.png         (440×84)
  logo-observatorio@2x.png         (880×168)
  logo-observatorio@3x.png         (1320×252)
  logo-observatorio-blanc@1x.png   (440×84)
  logo-observatorio-blanc@2x.png   (880×168)
  logo-observatorio-blanc@3x.png   (1320×252)
  logo-icon@1x.png                 (72×72)
  logo-icon@2x.png                 (144×144)
  logo-icon@3x.png                 (216×216)
favicon/
  favicon.ico                      (multi-res: 16, 32, 48)
  favicon-16.png                   (16×16)
  favicon-32.png                   (32×32)
  apple-touch-icon.png             (180×180)
  og-image.png                     (1200×630, logo centrado sobre blanco)
```

## Qué fichero usar según el contexto

| Contexto | Fichero |
|---|---|
| Email HTML (newsletter) | PNG `@2x` (compatibilidad universal, retina-ready) |
| Web del observatorio | SVG (calidad infinita, peso mínimo) |
| Infografías / LinkedIn | PNG `@3x` o SVG |
| Pitch decks / impresos | SVG |
| Favicon de navegador | `favicon.ico` (multi-res) + `favicon-32.png` |
| Pantalla home iOS / Android | `apple-touch-icon.png` |
| Tarjetas Open Graph / Twitter | `og-image.png` |

## Colores

| Rol | HEX | RGB | CMYK aprox |
|---|---|---|---|
| Navy principal | `#1B2A4A` | 27 / 42 / 74 | 95 / 85 / 35 / 35 |
| Azul-gris secundario (subtítulo) | `#4A6080` | 74 / 96 / 128 | 75 / 55 / 25 / 10 |
| Separador interno | `#E8EAF0` | 232 / 234 / 240 | — |

El logo **no existe en otros colores**. No generar variantes en rojo, verde u otros tonos.

## Tipografía

Familia: **Inter** (open-source, SIL Open Font License).

| Peso | Uso |
|---|---|
| 300 (Light) | Subtítulo "del Comercio Minorista" |
| 400 (Regular) | "J3B3 CONSULTING" (caps con tracking) |
| 600 (SemiBold) | Wordmark principal "Observatorio" |

Stack de respaldo (cuando Inter no esté disponible): `-apple-system, BlinkMacSystemFont, 'Helvetica Neue', Arial, sans-serif`.

## Reglas de uso

- **Tamaño mínimo horizontal**: 120 px de ancho. Por debajo de 120 px, usar la variante icon.
- **Tamaño mínimo icon**: 24 px.
- **Zona de protección**: dejar libre alrededor del logo un margen equivalente a la altura del símbolo (≈ 84 px en la versión completa, ≈ 72 px en la icon). No invadir esa zona con texto, gráficos ni bordes.
- **No deformar**: mantener proporción 5,24 : 1 (horizontal) o 1 : 1 (icon).
- **No recolorear**: usar las variantes navy o blanca según contraste del fondo.
- **No añadir efectos**: sombras, degradados, contornos o rotaciones.

## Hosting

Los PNG y SVG se sirven públicamente vía GitHub Pages del repo `observatori-comerc`:

```
https://jordi-j3b3.github.io/observatori-comerc/brand/png/{archivo}.png
https://jordi-j3b3.github.io/observatori-comerc/brand/svg/{archivo}.svg
```

La copia que vive en este repo (`j3b3-newsletter/assets/brand/`) es de referencia local; la fuente de servicio público es la del repo `observatori-comerc`. Cualquier cambio de marca debe replicarse en ambos repos.

## Regenerar PNG desde los SVG

Requiere `librsvg` y la familia Inter instalada en el sistema:

```bash
brew install librsvg
brew install --cask font-inter
```

Después, desde `assets/brand/`:

```bash
for v in "" "-blanc"; do
  for s in 440:1x 880:2x 1320:3x; do
    w="${s%:*}"; n="${s#*:}"
    rsvg-convert -w "$w" "svg/logo-observatorio${v}.svg" -o "png/logo-observatorio${v}@${n}.png"
  done
done
for s in 72:1x 144:2x 216:3x; do
  w="${s%:*}"; n="${s#*:}"
  rsvg-convert -w "$w" "svg/logo-observatorio-icon.svg" -o "png/logo-icon@${n}.png"
done
```
