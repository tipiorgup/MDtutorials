"""Run tutorial steps as subprocesses inside a per session work directory."""
import importlib.util
import os
import shutil
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path
from string import Template

ROOT = Path(__file__).resolve().parent.parent
STEP_TIMEOUT = 150  # seconds per step
MAX_LOG_LINES = 300
THREADS = "2"

# Energy and log output is written every 50 steps in the demo, instead of 1000.
DEMO_MDP_EDITS = (
    r"s/^nstenergy .*/nstenergy = 50/;"
    r"s/^nstlog .*/nstlog = 50/;"
    r"s/^nstxout-compressed .*/nstxout-compressed = 50/"
)

_gate = threading.BoundedSemaphore(1)


def new_workdir(engine):
    """Create a fresh work directory with the structures and MDP scripts."""
    base = Path(tempfile.gettempdir()) / "mdtutorials_sessions"
    base.mkdir(exist_ok=True)
    now = time.time()
    for old in base.iterdir():  # drop sessions older than 3 hours
        if now - old.stat().st_mtime > 3 * 3600:
            shutil.rmtree(old, ignore_errors=True)
    work = Path(tempfile.mkdtemp(prefix=engine + "_", dir=base))
    shutil.copytree(ROOT / "structures", work / "structures")
    if engine == "gromacs":
        shutil.copytree(ROOT / "GROMACS" / "scripts", work / "scripts")
        for mdp in (work / "scripts").glob("*.mdp"):
            subprocess.run(["sed", "-i", DEMO_MDP_EDITS, str(mdp)], check=True)
    return work


def ensure_openmm():
    """Install OpenMM into the running environment if the platform build skipped it."""
    if importlib.util.find_spec("openmm"):
        return
    yield "OpenMM is not installed here, installing it now (first run only, about a minute)..."
    installers = (
        [sys.executable, "-m", "pip", "install", "openmm"],
        ["uv", "pip", "install", "--python", sys.executable, "openmm"],
    )
    for cmd in installers:
        try:
            done = subprocess.run(cmd, capture_output=True, text=True, timeout=240)
        except (OSError, subprocess.TimeoutExpired) as err:
            yield "%s failed: %s" % (cmd[0], err)
            continue
        yield "\n".join(((done.stdout or "") + (done.stderr or "")).splitlines()[-4:])
        if done.returncode == 0:
            importlib.invalidate_caches()
            return
    raise RuntimeError(
        "OpenMM could not be installed. Check that requirements.txt contains openmm "
        "and read the app build log."
    )


def render(code, params):
    return Template(code).substitute(**params)


def run_step(work, code, kind, params):
    """Yield output lines of one step. kind is 'python' or 'bash'."""
    script = render(code, params)
    env = dict(
        os.environ,
        GMX_MAXBACKUP="-1",
        OMP_NUM_THREADS=THREADS,
        OPENMM_CPU_THREADS=THREADS,
        PYTHONUNBUFFERED="1",
    )
    waited = 0
    while not _gate.acquire(timeout=1):
        waited += 1
        yield "Waiting for a free slot (%d s), other students are running..." % waited
    try:
        if kind == "python":
            yield from ensure_openmm()
            cmd = [sys.executable, "-u", "-c", script]
        else:
            cmd = ["bash", "-e", "-o", "pipefail", "-c", script]
        proc = subprocess.Popen(
            cmd, cwd=work, env=env, stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT, text=True, bufsize=1,
        )
        timer = threading.Timer(STEP_TIMEOUT, proc.kill)
        timer.start()
        try:
            for line in proc.stdout:
                yield line.rstrip("\n")
            rc = proc.wait()
        finally:
            timer.cancel()
        if rc < 0:
            raise RuntimeError(
                "Step stopped after %d s (killed). Lower the number of steps and try again." % STEP_TIMEOUT
            )
        if rc != 0:
            raise RuntimeError("Step failed with exit code %d, see the output above." % rc)
    finally:
        _gate.release()
