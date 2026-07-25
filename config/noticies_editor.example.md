# Notícies seleccionades per l'editor
#
# Còpia aquest fitxer com a config/noticies_editor.md (sense el .example) i
# omple-hi les notícies que vols fer arribar al Bloc 2 de la propera edició.
# snapshot.py el llegeix, fa fetch de cada URL (títol + primer paràgraf) i
# les afegeix a recopilacion_prensa.md amb el tag [EDITOR] perquè Sonnet
# les tingui en compte.
#
# DOS NIVELLS DE PRIORITAT (segons el prefix de la primera línia):
#
#   - URL: <url>         → PRIORITÀRIA però DESCARTABLE. Sonnet la prioritza
#                          per al Bloc 2, però pot descartar-la si té bon
#                          criteri editorial (p.ex. desplaça una notícia de
#                          proximitat o trenca la diversitat de segments).
#                          Si n'hi ha 3 o més amb contingut real, les usa totes.
#
#   - FORCE-URL: <url>   → INCLUSIÓ OBLIGATÒRIA al Bloc 2. Sonnet NO la pot
#                          descartar per criteri editorial: ocupa una de les 3
#                          places sí o sí. Única excepció: si el fetch de la URL
#                          falla (403/404/sense contingut), NO s'afegeix al
#                          recull i per tant no es força —la barrera
#                          anti-al·lucinació de la capa de dades mana sempre
#                          (mai es cita ni s'inventa contingut no verificat).
#
# La resta de camps (Angle, Segment) són idèntics en tots dos casos.
#
# Després d'una generació exitosa, config/noticies_editor.md es renombra a
# noticies_editor.used.md perquè no s'apliqui a una edició futura per error.
# Cada notícia [EDITOR] citada literalment al borrador final es registra a
# config/historial_editorial_noticies.jsonl — el perfil editorial de
# l'editor al llarg del temps.
#
# Només s'usen les entrades de la secció "## Setmana YYYY-MM-DD" que
# coincideix amb la data de --semana passada a snapshot.py.

## Setmana 2026-07-13

- FORCE-URL: https://exemple.com/noticia-imprescindible
  Angle: aquesta notícia ha d'anar al Bloc 2 sí o sí
  Segment: macro

- URL: https://exemple.com/noticia-1
  Angle: el format experiencial resisteix quan el consum frena
  Segment: centres_comercials

- URL: https://via-empresa.cat/mercaurants
  Angle: innovació de format en alimentació
  Segment: petit_comerc
