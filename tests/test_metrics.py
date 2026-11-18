"""Pruebas de las métricas de recuperación (funciones puras, sin modelos)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from rag_normainst.metrics import (abstention_outcome, aggregate, coverage, first_hit_rank, forbidden_found,
                                   group_by, hit_at_k, load_golden, normalize, recall_at_k, reciprocal_rank,
                                   score_generation, unit_of)

RETRIEVED = ["RITE:IT-4.2.1#1", "RITE:IT-4.2.1#2", "RITE:art-31#1", "RITE:IT-4.3.1", "RITE:IT-3.3#1"]


def test_unit_of_quita_el_numero_de_pieza():
    assert unit_of("RITE:IT-3.8#2") == "RITE:IT-3.8"
    assert unit_of("RITE:art-1") == "RITE:art-1"


def test_rango_cuenta_chunks_y_compara_por_unidad():
    # Caso real de q03: la IT 4.3.1 salió 4.ª
    assert first_hit_rank(RETRIEVED, ["RITE:IT-4.3.1"]) == 4
    # Cualquier pieza de la unidad cuenta como acierto
    assert first_hit_rank(RETRIEVED, ["RITE:IT-4.2.1"]) == 1
    assert first_hit_rank(RETRIEVED, ["RITE:IT-1.1.1"]) is None


def test_hit_at_k():
    exp = ["RITE:IT-4.3.1"]
    assert hit_at_k(RETRIEVED, exp, 1) == 0.0
    assert hit_at_k(RETRIEVED, exp, 3) == 0.0
    assert hit_at_k(RETRIEVED, exp, 5) == 1.0


def test_recall_distingue_varias_correctas():
    exp = ["RITE:IT-4.3.1", "RITE:IT-1.1.4.1.2"]   # solo llega una de las dos
    assert hit_at_k(RETRIEVED, exp, 5) == 1.0
    assert recall_at_k(RETRIEVED, exp, 5) == 0.5
    # Dos piezas de la misma unidad no cuentan doble
    assert recall_at_k(RETRIEVED, ["RITE:IT-4.2.1"], 5) == 1.0


def test_reciprocal_rank():
    assert reciprocal_rank(RETRIEVED, ["RITE:IT-4.3.1"]) == pytest.approx(0.25)
    assert reciprocal_rank(RETRIEVED, ["RITE:IT-4.2.1"]) == 1.0
    assert reciprocal_rank(RETRIEVED, ["RITE:IT-9.9"]) == 0.0


def test_mrr_de_la_semilla_es_085():
    # Rangos de q01, q02, q03, q04 (por id) y q06 del 16/11
    rows = [{"rr": 1.0}, {"rr": 1.0}, {"rr": 0.25}, {"rr": 1.0}, {"rr": 1.0}]
    assert aggregate(rows, ["rr"])["rr"] == pytest.approx(0.85)


def test_group_by_hace_medias_por_tipo():
    rows = [{"type": "a", "x": 1.0}, {"type": "a", "x": 0.0}, {"type": "b", "x": 1.0}]
    g = group_by(rows, "type", ["x"])
    assert g["a"] == {"n": 2, "x": 0.5}
    assert g["b"] == {"n": 1, "x": 1.0}


def test_el_golden_set_real_esta_bien_formado():
    path = Path(__file__).parents[1] / "eval" / "golden_set.jsonl"
    qs = load_golden(path)
    assert 30 <= len(qs) <= 50
    assert len({q["id"] for q in qs}) == len(qs)            # ids únicos
    for q in qs:
        assert {"id", "type", "split", "question", "expected", "expected_answer", "must_contain"} <= q.keys()
        assert q["split"] in {"dev", "holdout"}
        assert all("#" not in e for e in q["expected"])       # por unidad, no por chunk
        assert (q["type"] == "sin_respuesta") == (q["expected"] == [])


# --- generación ---------------------------------------------------------------

Q06 = {"expected": ["RITE:IT-1.1.4.1.2", "RITE:IT-3.8"], "must_contain": ["21", "23"]}
Q05 = {"expected": [], "must_contain": ["No consta en el RITE."]}
Q37 = {"expected": ["RITE:IT-1.1.4.3.1"], "must_contain": ["legionelosis"], "must_not_contain": ["60 °C"]}


def test_normalize_iguala_decimales_y_grados():
    assert normalize("12.5 dm3/s a 21 ºC") == "12,5 dm3/s a 21 °c"
    assert coverage("Caudal de 12.5 dm³/s", ["12,5"]) == 1.0


def test_coverage_cuenta_los_datos_presentes():
    assert coverage("Entre 21 y 23 °C [1]", ["21", "23"]) == 1.0
    assert coverage("Unos 21 °C [1]", ["21", "23"]) == 0.5
    assert coverage("cualquier cosa", []) == 1.0


def test_forbidden_detecta_la_invencion():
    assert forbidden_found("Debe estar a 60 ºC", ["60 °C"]) == ["60 °C"]
    assert forbidden_found("Remite a la legislación", ["60 °C"]) == []


def test_las_cuatro_casillas_de_no_consta():
    assert abstention_outcome(["RITE:art-1"], False) == "responde_cuando_consta"
    assert abstention_outcome(["RITE:art-1"], True) == "no_consta_indebido"
    assert abstention_outcome([], True) == "no_consta_correcto"
    assert abstention_outcome([], False) == "inventa"


def test_respuesta_correcta_y_completa():
    r = score_generation(Q06, "Entre 21 y 23 °C [1]; en uso, no más de 21 °C [2].", False,
                         ["RITE:IT-1.1.4.1.2#1", "RITE:IT-3.8#2"], [], ["RITE:IT-1.1.4.1.2#1", "RITE:IT-3.8#2"])
    assert r["correct"] and r["complete"] and r["diagnosis"] == "ok" and r["cites_expected"]


def test_correcta_pero_incompleta_si_no_cita_la_it_3_8():
    # El caso real de la Fase 1: 21-23 °C bien, pero sin la IT 3.8
    r = score_generation(Q06, "Entre 21 y 23 °C [1].", False, ["RITE:IT-1.1.4.1.2#1"], [],
                         ["RITE:IT-1.1.4.1.2#1", "RITE:IT-3.8#2"])
    assert r["correct"] and not r["complete"] and r["citation_recall"] == 0.5


def test_incompleta_es_fallo_de_generacion_si_el_contexto_llego():
    r = score_generation(Q06, "21 °C [1].", False, ["RITE:IT-1.1.4.1.2#1"], [], ["RITE:IT-1.1.4.1.2#1"])
    assert not r["correct"] and r["coverage"] == 0.5 and r["diagnosis"] == "fallo_generacion"


def test_sin_contexto_es_fallo_de_recuperacion():
    r = score_generation(Q06, "No consta en el RITE.", True, [], [], ["RITE:IT-3.3#1"])
    assert r["abstention"] == "no_consta_indebido" and r["diagnosis"] == "fallo_recuperacion"


def test_inventar_cuando_no_consta_es_fallo():
    r = score_generation(Q05, "La sección mínima es 2,5 mm² [1].", False, ["RITE:IT-1.2.4.2.2#1"], [], [])
    assert r["abstention"] == "inventa" and not r["correct"] and r["diagnosis"] == "fallo_generacion"


def test_dato_prohibido_tumba_la_respuesta():
    r = score_generation(Q37, "Según la legionelosis, a 60 ºC [1].", False, ["RITE:IT-1.1.4.3.1"], [],
                         ["RITE:IT-1.1.4.3.1"])
    assert r["forbidden"] == ["60 °C"] and not r["correct"]


def test_alternativas_en_los_datos_obligatorios():
    must = [["calidad media", "buena calidad"]]
    assert coverage("IDA 2 es aire de calidad media [1]", must) == 1.0
    assert coverage("IDA 2 es aire de buena calidad [1]", must) == 1.0
    assert coverage("IDA 2 es aire bueno", must) == 0.0


def test_diagnostico_por_datos_en_el_contexto():
    # q13 real: llega un trozo de la IT 3.3, pero no el de la tabla con los «2 años»
    q13 = {"expected": ["RITE:IT-3.3"], "must_contain": ["2 años"]}
    r = score_generation(q13, "No consta en el RITE.", True, [], [], ["RITE:IT-3.3#4"],
                         context="Para instalaciones de más de 70 kW ...")
    assert r["context_hit"] and r["context_coverage"] == 0.0 and r["diagnosis"] == "fallo_recuperacion"
    r = score_generation(q13, "No consta en el RITE.", True, [], [], ["RITE:IT-3.3#1"],
                         context="Calderas murales a gas Pn ≤ 70 kW. 2 años. Anual.")
    assert r["diagnosis"] == "fallo_generacion"
