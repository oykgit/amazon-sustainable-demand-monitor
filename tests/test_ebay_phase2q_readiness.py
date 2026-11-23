
"""Phase 2Q.4: Offline production-readiness gate tests.

No eBay calls, database connections, or production changes.
"""

import json
import subprocess
import sys
from pathlib import Path

import pytest

from ebay_phase2n import GATES, evaluate


VALID_REFERENCE = "audit-reference-2026-001"
MODULE_PATH = (
    Path(__file__).resolve().parents[1]
    / "ebay_phase2n.py"
)


def approved_item():
    return {
        "approved": True,
        "reference": VALID_REFERENCE,
    }


def complete_evidence():
    return {
        gate: approved_item()
        for gate in GATES
    }


def test_eight_required_gates():
    assert len(GATES) == 8

    assert set(GATES) == {
        "storage_inventory",
        "identity_erasure",
        "ebay_signature",
        "neon_transactions",
        "http_delivery",
        "hosting",
        "ebay_approval",
        "browse_api",
    }


def test_empty_evidence_fails_closed():
    result = evaluate({})

    assert result["evidence_complete"] is False
    assert result["production_ready"] is False

    for gate in result["gates"].values():
        assert gate["evidence_recorded"] is False


@pytest.mark.parametrize("evidence", [
    None,
    [],
    "approved",
    123,
    True,
])
def test_non_object_evidence_rejected(evidence):
    with pytest.raises(
        ValueError,
        match="evidence must be an object",
    ):
        evaluate(evidence)


def test_unknown_gate_rejected():
    with pytest.raises(
        ValueError,
        match="unknown gate",
    ):
        evaluate({
            "unauthorized_override": approved_item()
        })


@pytest.mark.parametrize("gate", list(GATES))
def test_each_missing_gate_blocks_completion(gate):
    evidence = complete_evidence()
    del evidence[gate]

    result = evaluate(evidence)

    assert result["evidence_complete"] is False
    assert result["production_ready"] is False
    assert result["gates"][gate]["evidence_recorded"] is False


@pytest.mark.parametrize("bad_item", [
    None,
    True,
    "approved",
    [],
    {},
    {"approved": False, "reference": VALID_REFERENCE},
    {"approved": 1, "reference": VALID_REFERENCE},
    {"approved": "true", "reference": VALID_REFERENCE},
    {"approved": True},
    {"approved": True, "reference": ""},
    {"approved": True, "reference": "short"},
    {"approved": True, "reference": 123456789012},
    {"approved": True, "reference": None},
    {"approved": True, "reference": " " * 20},
])
def test_invalid_evidence_never_passes(bad_item):
    evidence = complete_evidence()
    evidence["storage_inventory"] = bad_item

    result = evaluate(evidence)

    assert result["evidence_complete"] is False
    assert result["production_ready"] is False
    assert (
        result["gates"]["storage_inventory"]["evidence_recorded"]
        is False
    )


def test_reference_minimum_length():
    evidence = complete_evidence()

    evidence["storage_inventory"]["reference"] = "A" * 11
    assert evaluate(evidence)["evidence_complete"] is False

    evidence["storage_inventory"]["reference"] = "A" * 12
    assert evaluate(evidence)["evidence_complete"] is True


def test_partial_evidence_not_complete():
    evidence = {
        "storage_inventory": approved_item(),
        "ebay_signature": approved_item(),
    }

    result = evaluate(evidence)

    assert result["evidence_complete"] is False
    assert result["production_ready"] is False


def test_all_evidence_still_not_production_ready():
    result = evaluate(complete_evidence())

    assert result["evidence_complete"] is True
    assert result["production_ready"] is False
    assert result["kind"] == "operator_evidence_register"
    assert result["phase"] == "2N"

    assert all(
        gate["evidence_recorded"]
        for gate in result["gates"].values()
    )


def test_output_preserves_gate_descriptions():
    result = evaluate({})

    for gate, description in GATES.items():
        assert result["gates"][gate]["description"] == description


def test_evaluation_does_not_modify_input():
    evidence = complete_evidence()
    original = json.loads(json.dumps(evidence))

    evaluate(evidence)

    assert evidence == original


def test_cli_without_evidence():
    result = subprocess.run(
        [sys.executable, str(MODULE_PATH)],
        capture_output=True,
        text=True,
        timeout=10,
        check=True,
    )

    output = json.loads(result.stdout)

    assert output["evidence_complete"] is False
    assert output["production_ready"] is False


def test_cli_with_complete_evidence(tmp_path):
    evidence_file = tmp_path / "evidence.json"
    evidence_file.write_text(
        json.dumps(complete_evidence()),
        encoding="utf-8",
    )

    result = subprocess.run(
        [
            sys.executable,
            str(MODULE_PATH),
            "--evidence",
            str(evidence_file),
        ],
        capture_output=True,
        text=True,
        timeout=10,
        check=True,
    )

    output = json.loads(result.stdout)

    assert output["evidence_complete"] is True
    assert output["production_ready"] is False


def test_cli_rejects_unknown_gate(tmp_path):
    evidence_file = tmp_path / "invalid.json"
    evidence_file.write_text(
        json.dumps({
            "unknown_gate": approved_item()
        }),
        encoding="utf-8",
    )

    result = subprocess.run(
        [
            sys.executable,
            str(MODULE_PATH),
            "--evidence",
            str(evidence_file),
        ],
        capture_output=True,
        text=True,
        timeout=10,
    )

    assert result.returncode != 0
    assert "unknown gate" in result.stderr
