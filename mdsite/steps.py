from dataclasses import dataclass, field


@dataclass
class Step:
    key: str
    title: str
    explain: str
    code: str = ""
    kind: str = "python"          # 'python' or 'bash'
    params: dict = field(default_factory=dict)   # name -> (label, min, max, default, step)
    notebook: str = ""            # equivalent cell of the notebook
    analysis: bool = False
