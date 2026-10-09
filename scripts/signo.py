"""Clasifica el signo de una edición (positivo / negativo / mixto) sobre el
TEXTO FINAL, el que se envía.

Lo usa schedule.py justo antes de crear la campaña y escribe el resultado en
el campo `signo` del historial. Se calcula aquí y no en generate.py por la
misma razón que el ROADMAP da para el resto de campos del historial: el
borrador se corrige a mano después de generate.py, y el signo de la edición
es el del texto que sale, no el del primer borrador.

El campo lo lee `format_historial_para_prompt()` (generate.py) para aplicar la
regla 24 de `config/estil_editorial.md` (alternancia de signo).

Es una ayuda, no un gate: si la llamada falla, schedule.py avisa y deja el
campo como estaba. Un signo mal clasificado se corrige a mano en el historial
(`signo_estado: "pendiente de confirmación"` marca los dudosos).
"""
from __future__ import annotations

import re

SIGNOS = ("positivo", "negativo", "mixto")

_PROMPT = """Lee la apertura de esta edición de un boletín sobre el comercio \
minorista (titular, cifra protagonista y su lectura) y clasifica el signo del \
hallazgo principal con UNA palabra.

- positivo: el hallazgo principal es una mejora real frente a su base de \
comparación (la misma serie un año antes, o la UE-27), aunque lleve cautelas.
- negativo: el hallazgo principal es un deterioro, una brecha que se mantiene \
o se abre, o una pérdida.
- mixto: el hallazgo principal contiene a la vez una mejora y un deterioro de \
peso comparable, o relativiza una mala noticia sin que haya mejora.

Juzga el hallazgo de la cifra protagonista, no el tono de las noticias ni la \
predicción. Responde solo con: positivo, negativo o mixto.

<APERTURA>
{texto}
</APERTURA>"""


def apertura(md_text: str, limite: int = 6000) -> str:
    """Bloque 1 del texto final: desde el principio hasta NUESTRA LECTURA.

    Si no encuentra el marcador devuelve el principio del texto, para que la
    clasificación no falle por un cambio de formato."""
    from compose import strip_trazabilidad  # import tardío: evita ciclos

    texto = strip_trazabilidad(md_text)
    m = re.search(r"NUESTRA LECTURA", texto)
    return (texto[: m.start()] if m else texto)[:limite].strip()


def clasifica_signo(client, modelo: str, md_text: str) -> str | None:
    """Devuelve 'positivo', 'negativo' o 'mixto', o None si no se puede."""
    texto = apertura(md_text)
    if not texto:
        return None
    r = client.messages.create(
        model=modelo,
        max_tokens=10,
        temperature=0.0,
        messages=[{"role": "user", "content": _PROMPT.format(texto=texto)}],
    )
    out = "".join(b.text for b in r.content if b.type == "text").strip().lower()
    out = re.sub(r"[^a-z]", "", out)
    return out if out in SIGNOS else None
