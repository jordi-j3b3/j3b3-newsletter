# Notícies seleccionades per l'editor
#
# Còpia aquest fitxer com a config/noticies_editor.md (sense el .example) i
# omple-hi les notícies que vols garantir al Bloc 2 de la propera edició.
# snapshot.py el llegeix, fa fetch de cada URL (títol + primer paràgraf) i
# les afegeix a recopilacion_prensa.md amb el tag [EDITOR] perquè Sonnet
# les prioritzi (generate.py les usa totes si n'hi ha 3 o més).
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

- URL: https://exemple.com/noticia-1
  Angle: el format experiencial resisteix quan el consum frena
  Segment: centres_comercials

- URL: https://via-empresa.cat/mercaurants
  Angle: innovació de format en alimentació
  Segment: petit_comerc
