from pathlib import Path

import pandas as pd
import streamlit as st

from mdsite import runner
from mdsite.bundle import build_zip
from mdsite.steps_gromacs import STEPS as GMX_STEPS
from mdsite.steps_openmm import STEPS as OMM_STEPS

st.set_page_config(page_title="Your first MD", layout="centered")

ENGINES = {
    "OpenMM": ("openmm", OMM_STEPS),
    "GROMACS": ("gromacs", GMX_STEPS),
}


def init():
    st.session_state.setdefault("engine", None)
    st.session_state.setdefault("page", 0)
    st.session_state.setdefault("logs", {})
    st.session_state.setdefault("work", None)


def start(label):
    key, _ = ENGINES[label]
    st.session_state.update(engine=label, page=1, logs={}, work=str(runner.new_workdir(key)))


def read_xvg(path):
    xs, ys = [], []
    for line in path.read_text().splitlines():
        if line and line[0] not in "#@":
            a, b = line.split()[:2]
            xs.append(float(a))
            ys.append(float(b))
    return pd.DataFrame({"time (ps)": xs, path.stem: ys}).set_index("time (ps)")


def read_openmm_logs(work):
    cols = ["step", "potential energy", "temperature", "volume", "density"]
    frames = []
    for phase in ("nvt", "npt", "md"):
        f = work / (phase + "_log.csv")
        if f.exists():
            df = pd.read_csv(f, skiprows=1, names=cols)
            df["phase"] = phase
            frames.append(df)
    return pd.concat(frames, ignore_index=True) if frames else None


def show_analysis(label, work):
    if label == "GROMACS":
        for name, title in [("potential", "Potential energy, minimisation (kJ/mol)"),
                            ("temperature", "Temperature, NVT (K)"),
                            ("density", "Density, NPT (kg/m3)"),
                            ("pressure", "Pressure, NPT (bar)")]:
            f = work / (name + ".xvg")
            if f.exists():
                st.caption(title)
                st.line_chart(read_xvg(f))
    else:
        df = read_openmm_logs(work)
        if df is None:
            st.info("No logs found yet, run the earlier steps first.")
            return
        for col, title in [("temperature", "Temperature (K), all phases"),
                           ("potential energy", "Potential energy (kJ/mol), all phases"),
                           ("density", "Density (g/mL), all phases")]:
            st.caption(title)
            st.line_chart(df[col])


def welcome():
    st.title("Your first molecular dynamics simulation")
    st.write(
        "Lysozyme in water, step by step. Pick one engine, follow the steps, run a very short "
        "demo of each one, and download the Jupyter notebooks at the end to run longer "
        "simulations on your own computer."
    )
    label = st.radio(
        "Choose your MD engine",
        list(ENGINES),
        captions=[
            "Python API, gentle learning curve if you know Python.",
            "Command line tools, the most widely used MD package.",
        ],
        index=None,
    )
    if st.button("Start the tutorial", type="primary", disabled=label is None):
        start(label)
        st.rerun()


def tutorial():
    label = st.session_state.engine
    key, steps = ENGINES[label]
    page = st.session_state.page
    work = Path(st.session_state.work)
    total = len(steps) + 1

    st.progress(page / total, text="%s tutorial, step %d of %d" % (label, page, total))

    if page > len(steps):
        finish(label, key)
    else:
        step = steps[page - 1]
        st.header(step.title)
        st.markdown(step.explain)
        if step.code:
            st.code(step.code, language="python" if step.kind == "python" else "bash")
            st.caption("Same step in the original notebook: " + step.notebook)
        params = {}
        for name, (text, lo, hi, default, inc) in step.params.items():
            params[name] = st.slider(text, lo, hi, default, inc, key="%s_%s" % (step.key, name))

        log = st.session_state.logs.get(step.key)
        if step.code:
            if st.button("Run this step", type="primary", key="run_" + step.key):
                lines = []
                with st.status("Running...", expanded=True) as status:
                    box = st.empty()
                    try:
                        for line in runner.run_step(work, step.code, step.kind, params):
                            lines.append(line)
                            box.code("\n".join(lines[-15:]))
                        status.update(label="Done", state="complete")
                        st.session_state.logs[step.key] = "\n".join(lines[-runner.MAX_LOG_LINES:])
                    except RuntimeError as err:
                        status.update(label="Failed", state="error")
                        st.error(str(err))
                        st.session_state.logs.pop(step.key, None)
                log = st.session_state.logs.get(step.key)
            elif log:
                with st.expander("Output of the last run", expanded=True):
                    st.code(log)
        if step.analysis:
            if not step.code or step.key in st.session_state.logs:
                show_analysis(label, work)

    left, right, _ = st.columns([1, 1, 3])
    if left.button("Back", disabled=page <= 1):
        st.session_state.page -= 1
        st.rerun()
    done = page > len(steps) or steps[page - 1].key in st.session_state.logs or not steps[page - 1].code
    if page <= len(steps) and right.button("Next", disabled=not done, type="primary"):
        st.session_state.page += 1
        st.rerun()
    if page <= len(steps) and not done:
        st.caption("Run the step to continue.")
    if st.sidebar.button("Change engine / start over"):
        st.session_state.update(engine=None, page=0, logs={}, work=None)
        st.rerun()


def finish(label, key):
    st.header("Download the notebooks")
    st.write(
        "You have seen every stage of the workflow with short demo runs. The notebooks use the "
        "full settings, so run them on your own computer."
    )
    st.download_button(
        "Download %s notebook bundle (.zip)" % label,
        build_zip(key),
        file_name="MDtutorials_%s.zip" % key,
        mime="application/zip",
        type="primary",
    )
    st.markdown(
        "The zip holds the notebook, the structures, an `environment.yml` and a short README. "
        "Create the environment with `conda env create -f environment.yml`."
    )
    other = "GROMACS" if label == "OpenMM" else "OpenMM"
    other_key = ENGINES[other][0]
    st.download_button(
        "Also download the %s bundle" % other,
        build_zip(other_key),
        file_name="MDtutorials_%s.zip" % other_key,
        mime="application/zip",
    )


init()
if st.session_state.engine is None:
    welcome()
else:
    tutorial()
