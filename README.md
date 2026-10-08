# Jupyter notebooks for your first MD

This repository provides tutorials for two different platforms used in Molecular Dynamics (MD) simulations: **Gromacs** and **OpenMM**.

The base tutorial for Gromacs is available here:  
[Lysozyme Tutorial on Gromacs](http://www.mdtutorials.com/gmx/lysozyme/01_pdb2gmx.html)

While **Gromacs** is a widely-used MD platform with a broad set of features, I find **OpenMM** to have a more intuitive learning curve, especially for those familiar with Python.

## Setting Up OpenMM

To use OpenMM, create a new environment with the following command:

`conda create -n openmm`

For OpenMM, you will need to install the following:

- **OpenMM**  
  `conda install -c conda-forge openmm`

- **NumPy**  
  `conda install numpy`

- **Matplotlib**  
  `conda install matplotlib`

- **Jupyter**  
  `conda install jupyter`

You can use `conda install` or `pip install`. I would like you to give it a try by your own, if it gets too complicated I will send you a line command to copy and paste.

Remember to select in anaconda the environment you want to use.

If you have any doubts just reach me.

## Streamlit website

`app.py` is a step by step website. Choose OpenMM or GROMACS, run a very short demo of each
stage, and download the notebooks at the end.

Local run (needs the `gmx` command for the GROMACS path):

`pip install -r requirements.txt` then `streamlit run app.py`

Deploy on Streamlit Community Cloud: point a new app to this repository and `app.py`.
`requirements.txt` installs OpenMM and `packages.txt` installs GROMACS with apt.
Demos run on a small shared CPU, so keep the step sliders low. Only two demo runs execute at the
same time, the others wait in a queue.
