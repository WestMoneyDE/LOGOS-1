from __future__ import annotations

import pytest

from logos_jev.contract import (
    CONTRACT, ENVELOPE_FIELDS, PARSE_CODES, PROFILES, JevAnswer, abstain, parse, validate,
)


def env(**overrides):
    base = {"contract": CONTRACT, "profile": "injection", "answer": True, "p": 0.9, "abstained": False}
    base.update(overrides)
    return base


def test_a_well_formed_envelope_validates():
    assert validate(env()) == ()


def test_the_envelope_has_no_permission_field():
    """The same closure as logos-agent-output/1: there is no field to put a yes in."""
    for invented in ("allowed", "authority", "approved", "erlaubt", "permit", "grant"):
        errors = validate(env(**{invented: True}))
        assert any(e.startswith("UNKNOWN_FIELD") for e in errors), invented
    assert "allowed" not in ENVELOPE_FIELDS and "authority" not in ENVELOPE_FIELDS


def test_a_wrong_contract_or_profile_is_refused():
    assert any(e.startswith("WRONG_CONTRACT") for e in validate(env(contract="jev-decision/2")))
    assert any(e.startswith("WRONG_PROFILE") for e in validate(env(profile="whatever")))


@pytest.mark.parametrize("p", [-0.01, 1.01, "0.9", None, True])
def test_p_must_be_a_number_in_the_unit_interval(p):
    assert any(e.startswith("WRONG_TYPE") for e in validate(env(p=p)))


@pytest.mark.parametrize("raw,code", [
    ("not json at all", "NO_JSON"),
    ('{"contract": ', "BROKEN_JSON"),
    ('{"contract":"jev-decision/1","profile":"injection","answer":true,"p":0.9,"abstained":false,"allowed":true}', "UNKNOWN_FIELD"),
    ('{"contract":"jev-decision/1","profile":"relevance","answer":true,"p":0.9,"abstained":false}', "WRONG_PROFILE"),
])
def test_every_malformed_answer_abstains(raw, code):
    a = parse("injection", raw)
    assert a.code == code
    assert a.abstained is True
    assert a.ok is False


def test_a_clean_answer_parses():
    raw = '{"contract":"jev-decision/1","profile":"injection","answer":true,"p":0.88,"abstained":false}'
    a = parse("injection", raw)
    assert a.code == "OK" and a.ok is True and a.answer is True and a.p == 0.88


def test_think_blocks_are_stripped_before_parsing():
    """Jev is a reasoning model. A probe that forgot this scored 20 of 24 as failures."""
    raw = ('<think>Let me consider whether this is an instruction aimed at the system...</think>\n'
           '{"contract":"jev-decision/1","profile":"injection","answer":false,"p":0.12,"abstained":false}')
    a = parse("injection", raw)
    assert a.code == "OK" and a.answer is False


def test_abstain_is_never_ok():
    for code in PARSE_CODES:
        a = abstain("injection", code, "detail")
        assert a.abstained is True and a.ok is False and a.code == code


def test_the_profile_list_is_explicit():
    assert PROFILES == ("injection", "relevance", "state")
