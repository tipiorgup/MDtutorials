"""Build the zip that students download at the end."""
import io
import zipfile

from .runner import ROOT

NOTEBOOKS = {"openmm": "OPENMM", "gromacs": "GROMACS"}

ENVS = {
    "openmm": """name: openmm
channels:
  - conda-forge
dependencies:
  - python=3.11
  - openmm
  - numpy
  - matplotlib
  - jupyter
""",
    "gromacs": """name: gromacs
channels:
  - conda-forge
dependencies:
  - python=3.11
  - gromacs
  - numpy
  - matplotlib
  - mdtraj
  - jupyter
  - pip
  - pip:
      - GromacsWrapper
""",
}

README = """MD tutorial bundle ({engine})

1. Create the environment:   conda env create -f environment.yml
2. Activate it:             conda activate {engine}
3. Start Jupyter:           jupyter notebook
4. Open {folder}/{notebook} and run the cells from top to bottom.

Keep the folder layout: the notebook reads ../structures/1aki.pdb.
Tutorial base: http://www.mdtutorials.com/gmx/lysozyme/index.html
"""


def build_zip(engine):
    folder = NOTEBOOKS[engine]
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for path in (ROOT / folder).rglob("*"):
            if path.is_file():
                z.write(path, "MDtutorials/%s/%s" % (folder, path.relative_to(ROOT / folder)))
        for path in (ROOT / "structures").rglob("*"):
            if path.is_file():
                z.write(path, "MDtutorials/structures/%s" % path.name)
        z.writestr("MDtutorials/environment.yml", ENVS[engine])
        z.writestr(
            "MDtutorials/README.txt",
            README.format(engine=engine, folder=folder, notebook="%s_playground.ipynb" % folder),
        )
    return buf.getvalue()
