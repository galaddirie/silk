"""Verify stable semantic contracts for every deliberately invalid type case."""

from __future__ import annotations

import argparse
import ast
import json
import re
import subprocess
import sys
from collections import defaultdict
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from importlib import metadata
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Literal, TypeAlias

ROOT = Path(__file__).resolve().parents[2]
FIXTURES = ROOT / "tests" / "typecheck"
CONTRACT_PATH = FIXTURES / "bad_diagnostics_snapshot.json"
PYTHON_VERSION = f"{sys.version_info.major}.{sys.version_info.minor}"
SUPPORTED_PYTHON_VERSIONS = ("3.11", "3.13")
CHECKERS = ("mypy", "pyright")
MESSAGE_NORMALIZATION = (
    "Trim and collapse every Unicode whitespace run to one ASCII space; "
    "the selected primary rule and full normalized message must match exactly."
)
CASE_MARKER = re.compile(
    r"^(?P<indent>[ ]*)# typecheck-case: " r"(?P<case_id>[a-z][a-z0-9_.-]*)[ ]*$"
)
MYPY_ERROR = re.compile(
    r"^(?P<file>.+):(?P<line>[1-9][0-9]*):(?P<column>[1-9][0-9]*): "
    r"error: (?P<message>.+)  \[(?P<rule>[^]]+)]$"
)
NOISY_PRIMARY_RULES = frozenset(
    {
        "reportUnknownMemberType",
        "reportUnknownVariableType",
        "reportUnusedVariable",
        "unused-coroutine",
    }
)

Checker: TypeAlias = Literal["mypy", "pyright"]
JSONValue: TypeAlias = (
    None | bool | int | float | str | list["JSONValue"] | dict[str, "JSONValue"]
)


class ContractFailure(AssertionError):
    """A checker, marker, or semantic expectation violated the contract."""


@dataclass(frozen=True, slots=True)
class Diagnostic:
    """One normalized checker error."""

    path: Path
    line: int
    rule: str
    message: str


@dataclass(frozen=True, slots=True)
class DiagnosticIdentity:
    """The stable semantic portion of one checker diagnostic."""

    rule: str
    message: str


@dataclass(frozen=True, slots=True)
class CaseRegion:
    """One marker and the AST statement it directly declares invalid."""

    case_id: str
    path: Path
    start_line: int
    end_line: int


@dataclass(frozen=True, slots=True)
class CaseContract:
    """Required primary diagnostic semantics for one marked invalid case."""

    case_id: str
    path: Path
    mypy: DiagnosticIdentity
    pyright: DiagnosticIdentity

    def expectation(self, checker: Checker) -> DiagnosticIdentity:
        """Return this case's expectation for one supported checker."""

        if checker == "mypy":
            return self.mypy
        return self.pyright


@dataclass(frozen=True, slots=True)
class Contract:
    """Validated checker pins and semantic case contracts."""

    checker_versions: dict[Checker, str]
    python_versions: tuple[str, ...]
    cases: tuple[CaseContract, ...]


@dataclass(frozen=True, slots=True)
class Options:
    """Validated command-line options."""

    python_version: str
    all_python_versions: bool
    self_test_only: bool
    write_contract: bool


def normalize_message(message: str) -> str:
    """Apply the contract's only permitted message normalization."""

    return " ".join(message.split())


def normalized_path(value: str, *, cwd: Path) -> Path:
    """Resolve checker paths without assuming absolute output."""

    path = Path(value)
    if not path.is_absolute():
        path = cwd / path
    return path.resolve()


def checker_name(value: str, *, label: str) -> Checker:
    """Narrow a decoded checker name to the supported checker set."""

    if value == "mypy":
        return "mypy"
    if value == "pyright":
        return "pyright"
    raise ContractFailure(f"{label} has unsupported checker {value!r}")


def json_mapping(value: JSONValue, *, label: str) -> dict[str, JSONValue]:
    """Require one JSON object without type casts or ignored checks."""

    if not isinstance(value, dict):
        raise ContractFailure(f"{label} is not a JSON object")
    return value


def json_list(value: JSONValue, *, label: str) -> list[JSONValue]:
    """Require one JSON list without type casts or ignored checks."""

    if not isinstance(value, list):
        raise ContractFailure(f"{label} is not a JSON list")
    return value


def required_string(
    mapping: dict[str, JSONValue],
    key: str,
    *,
    label: str,
) -> str:
    """Read one required string from a validated JSON object."""

    value = mapping.get(key)
    if not isinstance(value, str):
        raise ContractFailure(f"{label}.{key} is not a string")
    return value


def required_int(
    mapping: dict[str, JSONValue],
    key: str,
    *,
    label: str,
    minimum: int = 0,
) -> int:
    """Read one required non-boolean integer from a JSON object."""

    value = mapping.get(key)
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        raise ContractFailure(f"{label}.{key} is not an integer >= {minimum}")
    return value


def fixture_path(value: str, *, label: str) -> Path:
    """Resolve a contract fixture and forbid paths outside typecheck/."""

    path = (ROOT / value).resolve()
    if path.parent != FIXTURES or not path.name.endswith("_bad.py"):
        raise ContractFailure(f"{label} has invalid fixture path {value!r}")
    return path


def parse_expectation(
    value: JSONValue,
    *,
    label: str,
) -> DiagnosticIdentity:
    """Parse one exact rule plus semantic primary-message expectation."""

    item = json_mapping(value, label=label)
    if set(item) != {"rule", "message"}:
        raise ContractFailure(f"{label} has unexpected fields")
    rule = required_string(item, "rule", label=label)
    message = required_string(item, "message", label=label)
    if not rule or not message or normalize_message(message) != message:
        raise ContractFailure(
            f"{label} rule/message is empty or not canonically normalized"
        )
    return DiagnosticIdentity(rule=rule, message=message)


def load_contract(path: Path = CONTRACT_PATH) -> Contract:
    """Load the marker-keyed semantic contract generated by this harness."""

    decoded: JSONValue = json.loads(path.read_text(encoding="utf-8"))
    root = json_mapping(decoded, label="contract")
    if required_int(root, "schema_version", label="contract") != 2:
        raise ContractFailure("unsupported semantic contract schema")
    if (
        required_string(root, "message_normalization", label="contract")
        != MESSAGE_NORMALIZATION
    ):
        raise ContractFailure("contract message normalization changed")

    raw_versions = json_mapping(
        root.get("checker_versions"),
        label="contract.checker_versions",
    )
    versions: dict[Checker, str] = {}
    for raw_checker in CHECKERS:
        checker = checker_name(raw_checker, label="contract.checker_versions")
        versions[checker] = required_string(
            raw_versions,
            raw_checker,
            label="contract.checker_versions",
        )
    if set(raw_versions) != set(CHECKERS):
        raise ContractFailure("contract must pin exactly mypy and Pyright")

    raw_targets = json_list(
        root.get("python_versions"),
        label="contract.python_versions",
    )
    targets: list[str] = []
    for index, value in enumerate(raw_targets):
        if not isinstance(value, str):
            raise ContractFailure(f"contract.python_versions[{index}] is not a string")
        targets.append(value)
    if tuple(targets) != SUPPORTED_PYTHON_VERSIONS:
        raise ContractFailure(
            "contract Python targets must be exactly " f"{SUPPORTED_PYTHON_VERSIONS!r}"
        )

    raw_cases = json_list(root.get("cases"), label="contract.cases")
    cases: list[CaseContract] = []
    for index, value in enumerate(raw_cases):
        label = f"contract.cases[{index}]"
        item = json_mapping(value, label=label)
        if set(item) != {"id", "fixture", "expectations"}:
            raise ContractFailure(f"{label} has unexpected fields")
        case_id = required_string(item, "id", label=label)
        if CASE_MARKER.fullmatch(f"# typecheck-case: {case_id}") is None:
            raise ContractFailure(f"{label}.id is not a valid marker ID")
        path_value = fixture_path(
            required_string(item, "fixture", label=label),
            label=label,
        )
        expectations = json_mapping(
            item.get("expectations"),
            label=f"{label}.expectations",
        )
        if set(expectations) != set(CHECKERS):
            raise ContractFailure(f"{label} must require both mypy and Pyright")
        cases.append(
            CaseContract(
                case_id=case_id,
                path=path_value,
                mypy=parse_expectation(
                    expectations.get("mypy"),
                    label=f"{label}.expectations.mypy",
                ),
                pyright=parse_expectation(
                    expectations.get("pyright"),
                    label=f"{label}.expectations.pyright",
                ),
            )
        )

    case_count = required_int(root, "case_count", label="contract")
    if case_count != len(cases):
        raise ContractFailure("contract.case_count does not match its cases")
    if cases != sorted(cases, key=lambda case: case.case_id):
        raise ContractFailure("contract cases are not stably sorted by ID")
    if len({case.case_id for case in cases}) != len(cases):
        raise ContractFailure("contract contains duplicate case IDs")
    if set(root) != {
        "schema_version",
        "checker_versions",
        "python_versions",
        "message_normalization",
        "case_count",
        "cases",
    }:
        raise ContractFailure("contract has unexpected root fields")
    return Contract(
        checker_versions=versions,
        python_versions=tuple(targets),
        cases=tuple(cases),
    )


def discover_case_regions_from_source(
    path: Path,
    source: str,
) -> tuple[CaseRegion, ...]:
    """Associate every standalone marker with its next same-indent AST statement."""

    try:
        tree = ast.parse(source, filename=str(path))
    except SyntaxError as error:
        raise ContractFailure(f"cannot parse marked fixture {path}: {error}") from error
    lines = source.splitlines()
    statements = [node for node in ast.walk(tree) if isinstance(node, ast.stmt)]
    markers: list[tuple[int, int, str]] = []
    for line_number, line in enumerate(lines, start=1):
        match = CASE_MARKER.fullmatch(line)
        if match is not None:
            markers.append(
                (
                    line_number,
                    len(match.group("indent")),
                    match.group("case_id"),
                )
            )
        elif "# typecheck-case:" in line:
            raise ContractFailure(
                f"malformed or inline typecheck marker at {path}:{line_number}"
            )
    if not markers:
        raise ContractFailure(f"negative fixture has no case markers: {path}")
    if len({case_id for _line, _indent, case_id in markers}) != len(markers):
        raise ContractFailure(f"negative fixture has duplicate case IDs: {path}")

    regions: list[CaseRegion] = []
    for marker_index, (line_number, indent, case_id) in enumerate(markers):
        next_marker_line = (
            markers[marker_index + 1][0]
            if marker_index + 1 < len(markers)
            else len(lines) + 1
        )
        candidates = [
            node
            for node in statements
            if node.lineno > line_number
            and node.lineno < next_marker_line
            and node.col_offset == indent
        ]
        if not candidates:
            raise ContractFailure(
                f"marker {case_id!r} at {path}:{line_number} does not declare "
                "a following same-indent statement"
            )
        first_line = min(node.lineno for node in candidates)
        first_statements = [node for node in candidates if node.lineno == first_line]
        statement = min(
            first_statements,
            key=lambda node: getattr(node, "end_lineno", node.lineno) - node.lineno,
        )
        intervening_end = first_line - 1
        intervening = lines[line_number:intervening_end]
        if any(
            line.strip() and not line.lstrip().startswith("#") for line in intervening
        ):
            raise ContractFailure(
                f"marker {case_id!r} at {path}:{line_number} is detached "
                "from its statement"
            )
        end_line = getattr(statement, "end_lineno", statement.lineno)
        if next_marker_line <= end_line:
            raise ContractFailure(
                f"marker {case_id!r} at {path}:{line_number} overlaps "
                "the following marker"
            )
        regions.append(
            CaseRegion(
                case_id=case_id,
                path=path.resolve(),
                start_line=statement.lineno,
                end_line=end_line,
            )
        )
    return tuple(regions)


def discover_case_regions() -> tuple[CaseRegion, ...]:
    """Discover every marked case in every negative fixture."""

    fixtures = sorted(path.resolve() for path in FIXTURES.glob("*_bad.py"))
    if not fixtures:
        raise ContractFailure("no negative fixtures were discovered")
    regions: list[CaseRegion] = []
    for fixture in fixtures:
        regions.extend(
            discover_case_regions_from_source(
                fixture,
                fixture.read_text(encoding="utf-8"),
            )
        )
    case_ids = [region.case_id for region in regions]
    if len(set(case_ids)) != len(case_ids):
        raise ContractFailure("case IDs must be globally unique")
    return tuple(regions)


def verify_contract_coverage(
    contract: Contract,
    regions: Sequence[CaseRegion],
) -> None:
    """Require a one-to-one path-stable contract for all declared markers."""

    marked = {region.case_id: region.path for region in regions}
    declared = {case.case_id: case.path for case in contract.cases}
    if marked != declared:
        missing_markers = sorted(set(declared) - set(marked))
        unconsumed_markers = sorted(set(marked) - set(declared))
        wrong_paths = sorted(
            case_id
            for case_id in set(marked) & set(declared)
            if marked[case_id] != declared[case_id]
        )
        raise ContractFailure(
            "marker/contract coverage mismatch: "
            f"missing_markers={missing_markers!r}, "
            f"unconsumed_markers={unconsumed_markers!r}, "
            f"wrong_paths={wrong_paths!r}"
        )


def installed_checker_versions() -> dict[Checker, str]:
    """Return exact installed checker versions."""

    return {
        "mypy": metadata.version("mypy"),
        "pyright": metadata.version("pyright"),
    }


def verify_checker_versions(contract: Contract) -> None:
    """Reject checker drift before comparing pinned semantic messages."""

    installed = installed_checker_versions()
    if installed != contract.checker_versions:
        raise ContractFailure(
            f"checker version mismatch: installed={installed!r}, "
            f"contract={contract.checker_versions!r}"
        )


def parse_mypy_output(output: str, *, cwd: Path) -> tuple[Diagnostic, ...]:
    """Parse every mypy error while ignoring non-diagnostic notes."""

    diagnostics: list[Diagnostic] = []
    error_lines = [line for line in output.splitlines() if ": error:" in line]
    for line in error_lines:
        match = MYPY_ERROR.fullmatch(line)
        if match is None:
            raise ContractFailure(f"unparsed mypy error line: {line}")
        diagnostics.append(
            Diagnostic(
                path=normalized_path(match.group("file"), cwd=cwd),
                line=int(match.group("line")),
                rule=match.group("rule"),
                message=normalize_message(match.group("message")),
            )
        )
    if not diagnostics:
        raise ContractFailure(f"mypy produced no parseable errors:\n{output}")
    return tuple(diagnostics)


def parse_pyright_output(output: str) -> tuple[Diagnostic, ...]:
    """Parse every Pyright error and require a clean non-error summary."""

    decoded: JSONValue = json.loads(output)
    report = json_mapping(decoded, label="Pyright report")
    raw_diagnostics = json_list(
        report.get("generalDiagnostics"),
        label="Pyright report.generalDiagnostics",
    )
    diagnostics: list[Diagnostic] = []
    for index, value in enumerate(raw_diagnostics):
        label = f"Pyright diagnostic {index}"
        item = json_mapping(value, label=label)
        severity = required_string(item, "severity", label=label)
        if severity != "error":
            raise ContractFailure(
                f"{label} has unexpected non-error severity {severity!r}"
            )
        raw_range = json_mapping(item.get("range"), label=f"{label}.range")
        start = json_mapping(
            raw_range.get("start"),
            label=f"{label}.range.start",
        )
        zero_based_line = required_int(
            start,
            "line",
            label=f"{label}.range.start",
        )
        diagnostics.append(
            Diagnostic(
                path=Path(required_string(item, "file", label=label)).resolve(),
                line=zero_based_line + 1,
                rule=required_string(item, "rule", label=label),
                message=normalize_message(
                    required_string(item, "message", label=label)
                ),
            )
        )

    summary = json_mapping(report.get("summary"), label="Pyright report.summary")
    error_count = required_int(summary, "errorCount", label="Pyright summary")
    warning_count = required_int(
        summary,
        "warningCount",
        label="Pyright summary",
    )
    information_count = required_int(
        summary,
        "informationCount",
        label="Pyright summary",
    )
    if error_count != len(diagnostics) or warning_count or information_count:
        raise ContractFailure(
            "Pyright summary does not match the complete parsed error set: "
            f"errors={error_count}, warnings={warning_count}, "
            f"information={information_count}, parsed={len(diagnostics)}"
        )
    if not diagnostics:
        raise ContractFailure("Pyright produced no error diagnostics")
    return tuple(diagnostics)


def run_mypy(fixture: Path, *, python_version: str) -> tuple[Diagnostic, ...]:
    """Run strict pinned mypy for one negative fixture and target."""

    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "mypy",
            "--strict",
            "--no-incremental",
            "--show-error-codes",
            "--show-column-numbers",
            "--no-error-summary",
            "--no-pretty",
            "--no-color-output",
            "--python-version",
            python_version,
            str(fixture),
        ],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    output = completed.stdout + completed.stderr
    if completed.returncode != 1:
        raise ContractFailure(
            f"mypy returned {completed.returncode} for {fixture.name}:\n{output}"
        )
    return parse_mypy_output(output, cwd=ROOT)


def run_pyright(
    fixture: Path,
    *,
    python_version: str,
) -> tuple[Diagnostic, ...]:
    """Run strict pinned Pyright for one negative fixture and target."""

    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "pyright",
            "--pythonpath",
            sys.executable,
            "--pythonversion",
            python_version,
            "--outputjson",
            str(fixture),
        ],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode != 1:
        raise ContractFailure(
            f"Pyright returned {completed.returncode} for {fixture.name}:\n"
            f"stdout:\n{completed.stdout}\nstderr:\n{completed.stderr}"
        )
    return parse_pyright_output(completed.stdout)


def partition_diagnostics(
    *,
    checker: Checker,
    fixture: Path,
    regions: Sequence[CaseRegion],
    diagnostics: Sequence[Diagnostic],
) -> dict[str, tuple[Diagnostic, ...]]:
    """Confine every diagnostic to exactly one marked AST statement."""

    by_case: dict[str, list[Diagnostic]] = defaultdict(list)
    outside: list[Diagnostic] = []
    ambiguous: list[Diagnostic] = []
    for diagnostic in diagnostics:
        matches = [
            region
            for region in regions
            if diagnostic.path == region.path
            and region.start_line <= diagnostic.line <= region.end_line
        ]
        if not matches:
            outside.append(diagnostic)
        elif len(matches) > 1:
            ambiguous.append(diagnostic)
        else:
            by_case[matches[0].case_id].append(diagnostic)
    if outside or ambiguous:
        details = [
            f"{checker} emitted diagnostics outside exactly one marked case "
            f"for {fixture.name}"
        ]
        details.extend(
            f"  outside {item.path}:{item.line}: " f"{item.message} [{item.rule}]"
            for item in outside
        )
        details.extend(
            f"  ambiguous {item.path}:{item.line}: " f"{item.message} [{item.rule}]"
            for item in ambiguous
        )
        raise ContractFailure("\n".join(details))

    unconsumed = [region.case_id for region in regions if not by_case[region.case_id]]
    if unconsumed:
        raise ContractFailure(
            f"{checker} did not reject marked cases in {fixture.name}: "
            f"{unconsumed!r}"
        )
    return {
        case_id: tuple(case_diagnostics)
        for case_id, case_diagnostics in by_case.items()
    }


def verify_fixture_contract(
    *,
    checker: Checker,
    fixture: Path,
    regions: Sequence[CaseRegion],
    cases: dict[str, CaseContract],
    diagnostics: Sequence[Diagnostic],
) -> int:
    """Require one semantic primary match per case and confine all cascades."""

    partitioned = partition_diagnostics(
        checker=checker,
        fixture=fixture,
        regions=regions,
        diagnostics=diagnostics,
    )
    cascade_count = 0
    for region in regions:
        case = cases.get(region.case_id)
        if case is None:
            raise ContractFailure(f"unconsumed marker {region.case_id!r}")
        expectation = case.expectation(checker)
        identities = {
            DiagnosticIdentity(rule=item.rule, message=item.message)
            for item in partitioned[region.case_id]
        }
        if expectation not in identities:
            actual = sorted(
                f"{identity.message} [{identity.rule}]" for identity in identities
            )
            raise ContractFailure(
                f"{checker} semantic mismatch for {region.case_id}: "
                f"expected={expectation.message!r} [{expectation.rule}], "
                f"actual={actual!r}"
            )
        cascade_count += len(partitioned[region.case_id]) - 1
    return cascade_count


def case_contract_index(contract: Contract) -> dict[str, CaseContract]:
    """Index validated case contracts by stable ID."""

    return {case.case_id: case for case in contract.cases}


def fixture_regions(
    regions: Sequence[CaseRegion],
    fixture: Path,
) -> tuple[CaseRegion, ...]:
    """Select marked regions for one fixture."""

    return tuple(region for region in regions if region.path == fixture)


def choose_primary(
    *,
    checker: Checker,
    case_id: str,
    target_diagnostics: Sequence[Sequence[Diagnostic]],
) -> DiagnosticIdentity:
    """Choose one meaningful diagnostic common to both Python targets."""

    common: set[DiagnosticIdentity] | None = None
    for diagnostics in target_diagnostics:
        identities = {
            DiagnosticIdentity(rule=item.rule, message=item.message)
            for item in diagnostics
        }
        common = identities if common is None else common & identities
    if not common:
        raise ContractFailure(
            f"{checker} case {case_id!r} has no common semantic diagnostic "
            "across Python 3.11 and 3.13"
        )
    return min(
        common,
        key=lambda identity: (
            identity.rule in NOISY_PRIMARY_RULES,
            len(identity.message),
            identity.rule,
            identity.message,
        ),
    )


def contract_payload(
    regions: Sequence[CaseRegion],
) -> dict[str, JSONValue]:
    """Observe both targets and build a truthful semantic contract payload."""

    per_case: dict[tuple[str, Checker], list[tuple[Diagnostic, ...]]] = defaultdict(
        list
    )
    fixtures = sorted({region.path for region in regions})
    for python_version in SUPPORTED_PYTHON_VERSIONS:
        for fixture in fixtures:
            selected_regions = fixture_regions(regions, fixture)
            for checker in CHECKERS:
                narrowed_checker = checker_name(checker, label="contract writer")
                diagnostics = (
                    run_mypy(fixture, python_version=python_version)
                    if narrowed_checker == "mypy"
                    else run_pyright(fixture, python_version=python_version)
                )
                partitioned = partition_diagnostics(
                    checker=narrowed_checker,
                    fixture=fixture,
                    regions=selected_regions,
                    diagnostics=diagnostics,
                )
                for region in selected_regions:
                    per_case[(region.case_id, narrowed_checker)].append(
                        partitioned[region.case_id]
                    )

    raw_cases: list[JSONValue] = []
    for region in sorted(regions, key=lambda item: item.case_id):
        expectations: dict[str, JSONValue] = {}
        for checker in CHECKERS:
            narrowed_checker = checker_name(checker, label="contract writer")
            primary = choose_primary(
                checker=narrowed_checker,
                case_id=region.case_id,
                target_diagnostics=per_case[(region.case_id, narrowed_checker)],
            )
            expectations[narrowed_checker] = {
                "rule": primary.rule,
                "message": primary.message,
            }
        raw_cases.append(
            {
                "id": region.case_id,
                "fixture": str(region.path.relative_to(ROOT)),
                "expectations": expectations,
            }
        )
    versions: dict[str, JSONValue] = {}
    for checker, version in installed_checker_versions().items():
        versions[checker] = version
    return {
        "schema_version": 2,
        "checker_versions": versions,
        "python_versions": list(SUPPORTED_PYTHON_VERSIONS),
        "message_normalization": MESSAGE_NORMALIZATION,
        "case_count": len(regions),
        "cases": raw_cases,
    }


def write_contract(regions: Sequence[CaseRegion]) -> None:
    """Atomically replace the artifact with observations from both targets."""

    payload = contract_payload(regions)
    temporary_path = CONTRACT_PATH.with_suffix(".json.tmp")
    temporary_path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    temporary_path.replace(CONTRACT_PATH)
    generated = load_contract()
    verify_checker_versions(generated)
    verify_contract_coverage(generated, regions)


def expect_contract_failure(action: Callable[[], object]) -> None:
    """Assert one deliberately corrupted semantic contract is rejected."""

    try:
        action()
    except ContractFailure:
        return
    raise ContractFailure("matcher accepted a deliberately corrupted contract")


def synthetic_case(
    path: Path,
    region: CaseRegion,
    *,
    mypy: DiagnosticIdentity,
    pyright: DiagnosticIdentity,
) -> CaseContract:
    """Construct one path-consistent synthetic case contract."""

    return CaseContract(
        case_id=region.case_id,
        path=path.resolve(),
        mypy=mypy,
        pyright=pyright,
    )


def self_test_semantic_matching() -> None:
    """Adversarially prove marker stability and strict diagnostic consumption."""

    mypy_identity = DiagnosticIdentity(
        rule="arg-type",
        message='incompatible type "str"; expected "Target"',
    )
    pyright_identity = DiagnosticIdentity(
        rule="reportArgumentType",
        message='Argument cannot be assigned to parameter "value" of type "Target"',
    )
    unformatted = (
        "def probe(value: str)->None:\n"
        "    # typecheck-case: synthetic.rejected\n"
        "    reject( value )\n"
    )

    with TemporaryDirectory(prefix="silk-type-contract-") as directory:
        path = (Path(directory) / "synthetic_bad.py").resolve()
        path.write_text(unformatted, encoding="utf-8")
        completed = subprocess.run(
            [sys.executable, "-m", "black", "--quiet", str(path)],
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
        )
        if completed.returncode != 0:
            raise ContractFailure(
                "Black formatter regression probe failed:\n"
                f"{completed.stdout}{completed.stderr}"
            )
        formatted = path.read_text(encoding="utf-8")

    original_regions = discover_case_regions_from_source(path, unformatted)
    formatted_regions = discover_case_regions_from_source(path, formatted)
    moved_regions = discover_case_regions_from_source(
        path,
        "\n\n# moved without changing semantics\n" + formatted,
    )
    original = original_regions[0]
    case = synthetic_case(
        path,
        original,
        mypy=mypy_identity,
        pyright=pyright_identity,
    )
    cases = {case.case_id: case}
    for regions in (original_regions, formatted_regions, moved_regions):
        region = regions[0]
        diagnostic = Diagnostic(
            path=path,
            line=region.start_line,
            rule=mypy_identity.rule,
            message=mypy_identity.message,
        )
        verify_fixture_contract(
            checker="mypy",
            fixture=path,
            regions=regions,
            cases=cases,
            diagnostics=(diagnostic,),
        )

    two_case_source = (
        formatted + "\n# typecheck-case: synthetic.second\n" + 'reject("second")\n'
    )
    two_regions = discover_case_regions_from_source(path, two_case_source)
    second = synthetic_case(
        path,
        two_regions[1],
        mypy=mypy_identity,
        pyright=pyright_identity,
    )
    synthetic_contract = Contract(
        checker_versions={"mypy": "test", "pyright": "test"},
        python_versions=SUPPORTED_PYTHON_VERSIONS,
        cases=(case, second),
    )
    verify_contract_coverage(synthetic_contract, two_regions)

    expect_contract_failure(
        lambda: verify_contract_coverage(synthetic_contract, original_regions)
    )
    expect_contract_failure(
        lambda: verify_fixture_contract(
            checker="mypy",
            fixture=path,
            regions=original_regions,
            cases=cases,
            diagnostics=(),
        )
    )

    original_diagnostic = Diagnostic(
        path=path,
        line=original.start_line,
        rule=mypy_identity.rule,
        message=mypy_identity.message,
    )
    wrong_rule = synthetic_case(
        path,
        original,
        mypy=DiagnosticIdentity(
            rule="wrong-rule",
            message=mypy_identity.message,
        ),
        pyright=pyright_identity,
    )
    wrong_message = synthetic_case(
        path,
        original,
        mypy=DiagnosticIdentity(
            rule=mypy_identity.rule,
            message="different semantic message",
        ),
        pyright=pyright_identity,
    )

    def reject_corrupted_semantics(corrupted: CaseContract) -> None:
        expect_contract_failure(
            lambda: verify_fixture_contract(
                checker="mypy",
                fixture=path,
                regions=original_regions,
                cases={corrupted.case_id: corrupted},
                diagnostics=(original_diagnostic,),
            )
        )

    for corrupted in (wrong_rule, wrong_message):
        reject_corrupted_semantics(corrupted)

    outside_line = 1
    if original.start_line == outside_line:
        outside_line = original.end_line + 1
    unmarked = Diagnostic(
        path=path,
        line=outside_line,
        rule=mypy_identity.rule,
        message=mypy_identity.message,
    )
    expect_contract_failure(
        lambda: verify_fixture_contract(
            checker="mypy",
            fixture=path,
            regions=original_regions,
            cases=cases,
            diagnostics=(original_diagnostic, unmarked),
        )
    )

    second_diagnostic = Diagnostic(
        path=path,
        line=two_regions[1].start_line,
        rule=mypy_identity.rule,
        message=mypy_identity.message,
    )
    expect_contract_failure(
        lambda: verify_fixture_contract(
            checker="mypy",
            fixture=path,
            regions=two_regions,
            cases={case.case_id: case, second.case_id: second},
            diagnostics=(second_diagnostic,),
        )
    )

    cascade = Diagnostic(
        path=path,
        line=original.end_line,
        rule="secondary-cascade",
        message="secondary detail confined to the marked statement",
    )
    if (
        verify_fixture_contract(
            checker="mypy",
            fixture=path,
            regions=original_regions,
            cases=cases,
            diagnostics=(original_diagnostic, cascade),
        )
        != 1
    ):
        raise ContractFailure("confined secondary cascade was not counted")

    parsed_mypy = parse_mypy_output(
        f"{path}:7:3: error: {mypy_identity.message}  [{mypy_identity.rule}]",
        cwd=ROOT,
    )
    parsed_pyright = parse_pyright_output(
        json.dumps(
            {
                "generalDiagnostics": [
                    {
                        "file": str(path),
                        "severity": "error",
                        "message": pyright_identity.message,
                        "rule": pyright_identity.rule,
                        "range": {"start": {"line": 6}},
                    }
                ],
                "summary": {
                    "errorCount": 1,
                    "warningCount": 0,
                    "informationCount": 0,
                },
            }
        )
    )
    if (
        DiagnosticIdentity(parsed_mypy[0].rule, parsed_mypy[0].message) != mypy_identity
        or DiagnosticIdentity(parsed_pyright[0].rule, parsed_pyright[0].message)
        != pyright_identity
    ):
        raise ContractFailure("checker parsers lost semantic rule/message identity")
    if normalize_message("  target\n\tvalue\u00a0 ") != "target value":
        raise ContractFailure("message whitespace normalization drifted")

    print(
        "semantic matcher self-test passed: movement/Black stability, missing "
        "rejections, changed semantics, unmarked diagnostics, unconsumed "
        "markers, and confined cascades"
    )


def parse_args(argv: Sequence[str] | None = None) -> Options:
    """Parse and validate target, writer, and matcher-only modes."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--python-version",
        choices=SUPPORTED_PYTHON_VERSIONS,
        default=PYTHON_VERSION,
    )
    parser.add_argument("--all-python-versions", action="store_true")
    parser.add_argument("--self-test-only", action="store_true")
    parser.add_argument("--write-contract", action="store_true")
    arguments = parser.parse_args(argv)
    python_version = arguments.python_version
    all_python_versions = arguments.all_python_versions
    self_test_only = arguments.self_test_only
    should_write_contract = arguments.write_contract
    if (
        not isinstance(python_version, str)
        or not isinstance(all_python_versions, bool)
        or not isinstance(self_test_only, bool)
        or not isinstance(should_write_contract, bool)
    ):
        raise ContractFailure("argument parser returned invalid values")
    if self_test_only and should_write_contract:
        raise ContractFailure("self-test-only and write-contract are incompatible")
    return Options(
        python_version=python_version,
        all_python_versions=all_python_versions,
        self_test_only=self_test_only,
        write_contract=should_write_contract,
    )


def verify_target(
    *,
    python_version: str,
    contract: Contract,
    regions: Sequence[CaseRegion],
) -> None:
    """Verify all fixtures for one configured Python target."""

    cases = case_contract_index(contract)
    fixtures = sorted({region.path for region in regions})
    totals: dict[Checker, int] = {"mypy": 0, "pyright": 0}
    cascades: dict[Checker, int] = {"mypy": 0, "pyright": 0}
    for fixture in fixtures:
        selected_regions = fixture_regions(regions, fixture)
        mypy_diagnostics = run_mypy(fixture, python_version=python_version)
        mypy_cascades = verify_fixture_contract(
            checker="mypy",
            fixture=fixture,
            regions=selected_regions,
            cases=cases,
            diagnostics=mypy_diagnostics,
        )
        pyright_diagnostics = run_pyright(
            fixture,
            python_version=python_version,
        )
        pyright_cascades = verify_fixture_contract(
            checker="pyright",
            fixture=fixture,
            regions=selected_regions,
            cases=cases,
            diagnostics=pyright_diagnostics,
        )
        totals["mypy"] += len(mypy_diagnostics)
        totals["pyright"] += len(pyright_diagnostics)
        cascades["mypy"] += mypy_cascades
        cascades["pyright"] += pyright_cascades
        print(
            f"semantic cases passed: {fixture.name} "
            f"(cases={len(selected_regions)}, mypy={len(mypy_diagnostics)}, "
            f"Pyright={len(pyright_diagnostics)})"
        )
    print(
        f"semantic negative contract passed for Python {python_version}: "
        f"cases={len(regions)}, mypy_diagnostics={totals['mypy']}, "
        f"Pyright_diagnostics={totals['pyright']}, "
        f"confined_secondary_cascades="
        f"{cascades['mypy'] + cascades['pyright']}, unexpected=0"
    )


def main(argv: Sequence[str] | None = None) -> None:
    """Run adversarial self-tests, then generate or verify semantic contracts."""

    options = parse_args(argv)
    self_test_semantic_matching()
    if options.self_test_only:
        return

    regions = discover_case_regions()
    if options.write_contract:
        write_contract(regions)
        print(
            f"wrote semantic contract for {len(regions)} stable cases across "
            f"Python {SUPPORTED_PYTHON_VERSIONS!r}"
        )
        return

    contract = load_contract()
    verify_checker_versions(contract)
    verify_contract_coverage(contract, regions)
    targets = (
        contract.python_versions
        if options.all_python_versions
        else (options.python_version,)
    )
    for python_version in targets:
        if python_version not in contract.python_versions:
            raise ContractFailure(
                f"Python target {python_version} is not pinned in the contract"
            )
        verify_target(
            python_version=python_version,
            contract=contract,
            regions=regions,
        )


if __name__ == "__main__":
    main()
