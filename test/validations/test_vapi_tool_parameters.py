"""Keep the published Vapi tool parameters aligned with server validation."""

import json
from pathlib import Path

from app.validations.patient import PatientCreate


def test_vapi_tool_parameters_match_patient_contract():
    path = Path(__file__).resolve().parents[2] / "app/prompts/vapi_tool_parameters.json"
    schemas = json.loads(path.read_text(encoding="utf-8"))
    registration = schemas["register_patient"]
    assert set(registration["properties"]) == set(PatientCreate.model_fields)
    assert set(registration["required"]) == {
        name
        for name, field in PatientCreate.model_fields.items()
        if field.is_required()
    }
    lookup = schemas["lookup_patient"]
    assert set(lookup["properties"]) == {"last_name", "date_of_birth"}
    assert set(lookup["required"]) == set(lookup["properties"])
