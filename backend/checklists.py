"""Load expected quantities from a simple, editable JSON config."""
import json
from backend import config
from backend.schemas import Checklist


def list_checklists() -> list[Checklist]:
    with config.CHECKLIST_PATH.open(encoding="utf-8") as handle:
        raw = json.load(handle)
    output = []
    for row in raw["checklists"]:
        checklist = Checklist.model_validate(row)
        if not checklist.items or any(not item.strip() or type(count) is not int or count < 1
                                      for item, count in checklist.items.items()):
            raise ValueError(f"Invalid checklist: {checklist.id}")
        output.append(checklist)
    return output


def get_checklist(checklist_id: str) -> Checklist | None:
    return next((item for item in list_checklists() if item.id == checklist_id), None)
