import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.contract_guard import validate_change_proposal, validate_parse_result
from src.input_loader import load_text
from src.notice_diff_adapter import compare_parse_results
from src.parser_adapter import ParserAdapter


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


adapter = ParserAdapter()
old_request = read_json(ROOT / "samples/requests/NOTICE-004-V1.request.json")
new_request = read_json(ROOT / "samples/requests/NOTICE-004-V2.request.json")
old_result = adapter.parse(old_request, load_text(ROOT / "samples/input/NOTICE-004-V1.md"))
new_result = adapter.parse(new_request, load_text(ROOT / "samples/input/NOTICE-004-V2.md"))
task_map = read_json(ROOT / "samples/task-map-N07.json")
proposal = compare_parse_results(old_result, new_result, task_map)

validate_parse_result(old_result)
validate_parse_result(new_result)
validate_change_proposal(proposal)

write_json(ROOT / "samples/outputs/NOTICE-004-V1.parse-result.json", old_result)
write_json(ROOT / "samples/outputs/NOTICE-004-V2.parse-result.json", new_result)
write_json(ROOT / "samples/outputs/NOTICE-004.change-proposal.json", proposal)
print("Generated NOTICE-004 v1/v2 ParseResult and ChangeProposal")
