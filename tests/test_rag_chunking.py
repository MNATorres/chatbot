"""Tests del chunker: agrupar parrafos respetando `max_chars`, con overlap
entre fragmentos consecutivos."""

from chatbot.rag.chunking import chunk_text


def test_un_solo_parrafo_corto_es_un_solo_chunk():
    text = "Este es un parrafo corto."
    assert chunk_text(text, max_chars=100, overlap_chars=0) == [text]


def test_agrupa_parrafos_mientras_entren_en_max_chars():
    text = "Parrafo uno.\n\nParrafo dos."
    chunks = chunk_text(text, max_chars=100, overlap_chars=0)
    assert chunks == ["Parrafo uno.\n\nParrafo dos."]


def test_corta_en_nuevo_chunk_al_superar_max_chars():
    text = "Parrafo uno.\n\nParrafo dos.\n\nParrafo tres."
    chunks = chunk_text(text, max_chars=25, overlap_chars=0)
    assert chunks == ["Parrafo uno.", "Parrafo dos.", "Parrafo tres."]


def test_overlap_repite_la_cola_del_chunk_anterior():
    text = "Parrafo uno con contenido.\n\nParrafo dos con contenido.\n\nParrafo tres con contenido."
    chunks = chunk_text(text, max_chars=30, overlap_chars=10)

    assert len(chunks) >= 2
    tail_of_first = chunks[0][-10:]
    assert chunks[1].startswith(tail_of_first)


def test_parrafo_mas_largo_que_max_chars_se_trunca():
    parrafo_largo = "palabra " * 50
    chunks = chunk_text(parrafo_largo.strip(), max_chars=20, overlap_chars=0)
    assert len(chunks[0]) <= 20
