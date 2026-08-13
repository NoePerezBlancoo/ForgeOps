from pathlib import Path
from types import SimpleNamespace

from forgeops_agent.cli import build_parser, dispatch
from forgeops_agent.models import Risk, Task


class DelegateRecorder:
    def __init__(self) -> None:
        self.call = None

    def delegate(self, source: Path, **flags) -> Task:
        self.call = (source, flags)
        return Task(
            id="AI-0301",
            title="Persistence foundation",
            objective="Add persistence models.",
            allowed_paths=("backend/app/",),
            risk=Risk.MEDIUM,
        )


def test_delegate_accepts_and_forwards_explicit_risk_flags(tmp_path, capsys):
    source = tmp_path / "task.yaml"
    args = build_parser().parse_args(
        ["delegate", str(source), "--allow-medium-risk"]
    )
    orchestrator = DelegateRecorder()

    result = dispatch(args, SimpleNamespace(), orchestrator)

    assert result == 0
    assert orchestrator.call == (
        source.resolve(),
        {"allow_medium": True, "allow_high": False},
    )
    assert "STATUS: QUEUED" in capsys.readouterr().out
