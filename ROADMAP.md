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
