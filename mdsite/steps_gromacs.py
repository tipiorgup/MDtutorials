from .steps import Step

MPI = "-ntmpi 1"

STEPS = [
    Step(
        "prepare", "1. Clean the crystal structure",
        "The PDB file 1AKI contains crystal waters, which are `HETATM` records. "
        "We delete those lines because GROMACS will place its own water later.",
        "grep -v HETATM structures/1aki.pdb > clean.pdb\ngrep -c '^ATOM' clean.pdb\n",
        kind="bash",
        notebook="Cell 3 of the notebook",
    ),
    Step(
        "topology", "2. Topology with pdb2gmx",
        "`gmx pdb2gmx` chooses the force field (CHARMM27) and water model (TIP4P), adds the "
        "hydrogens and writes the topology `topol.top`, which lists every atom, bond and angle.",
        "gmx pdb2gmx -f clean.pdb -o processed.gro -water tip4p -p topol.top -ff charmm27 2>&1 | tail -25\n"
        "cp topol.top topol_base.top   # clean copy, so the next steps can be rerun\n",
        kind="bash",
        notebook="Cell 5 of the notebook",
    ),
    Step(
        "box", "3. Define the box",
        "`gmx editconf` places the protein in a cubic box with at least 1 nm between the protein "
        "and the box edge, so it does not interact with its own periodic image.",
        "echo Protein | gmx editconf -f processed.gro -o boxed.gro -bt cubic -d 1.0 -c -princ 2>&1 | tail -15\n",
        kind="bash",
        notebook="Cell 6 of the notebook",
    ),
    Step(
        "solvate", "4. Add water",
        "`gmx solvate` fills the empty box with TIP4P water and updates the number of water "
        "molecules in the topology.",
        "cp topol_base.top topol.top   # solvate edits topol.top, start from the clean copy\n"
        "gmx solvate -cp boxed.gro -cs tip4p.gro -p topol.top -o solvated.gro 2>&1 | tail -12\n"
        "cp topol.top topol_solvated.top\n",
        kind="bash",
        notebook="Cell 7 of the notebook",
    ),
    Step(
        "ions", "5. Add ions",
        "Lysozyme has a net charge. `grompp` prepares a run input file and `genion` replaces water "
        "molecules by Na+ and Cl- ions until the system is neutral.",
        "cp topol_solvated.top topol.top   # genion edits topol.top, start from the solvated copy\n"
        "gmx grompp -f scripts/ions.mdp -c solvated.gro -p topol.top -o ions.tpr -maxwarn 1 2>&1 | tail -15\n"
        "echo SOL | gmx genion -s ions.tpr -o solvated_ions.gro -p topol.top -pname NA -nname CL -neutral 2>&1 | tail -12\n",
        kind="bash",
        notebook="Cells 8 and 9 of the notebook",
    ),
    Step(
        "minimize", "6. Energy minimisation",
        "Steepest descent removes bad contacts. It stops when the largest force is below "
        "1000 kJ/mol/nm, which takes a few hundred steps.",
        "gmx grompp -f scripts/minim.mdp -c solvated_ions.gro -p topol.top -o emin.tpr 2>&1 | tail -15\n"
        "gmx mdrun -deffnm emin " + MPI + " 2>&1 | grep -E 'Steepest|Potential Energy|Maximum force|converged'\n",
        kind="bash",
        notebook="Cell 10 of the notebook",
    ),
    Step(
        "nvt", "7. NVT equilibration",
        "Constant volume and temperature, with position restraints on the protein so the solvent "
        "relaxes around it. The mdp file asks for 10000 steps of 2 fs, `-nsteps` shortens it for the demo.",
        "gmx grompp -f scripts/nvt.mdp -c emin.gro -r emin.gro -p topol.top -o nvt.tpr 2>&1 | tail -15\n"
        "gmx mdrun -deffnm nvt " + MPI + " -nsteps $nsteps 2>&1 | tail -6\n",
        kind="bash",
        params={"nsteps": ("Number of steps (2 fs each)", 200, 2000, 500, 100)},
        notebook="Cell 11 of the notebook",
    ),
    Step(
        "npt", "8. NPT equilibration",
        "Pressure coupling is switched on (Parrinello Rahman barostat), so the box adjusts until "
        "the density is right.",
        "gmx grompp -f scripts/npt.mdp -c nvt.gro -r nvt.gro -t nvt.cpt -p topol.top -o npt.tpr 2>&1 | tail -15\n"
        "gmx mdrun -deffnm npt " + MPI + " -nsteps $nsteps 2>&1 | tail -6\n",
        kind="bash",
        params={"nsteps": ("Number of steps (2 fs each)", 200, 2000, 500, 100)},
        notebook="Cell 12 of the notebook",
    ),
    Step(
        "production", "9. Production run",
        "Restraints are removed and we record the trajectory. A real project runs nanoseconds or more.",
        "gmx grompp -f scripts/md.mdp -c npt.gro -t npt.cpt -p topol.top -o md.tpr 2>&1 | tail -15\n"
        "gmx mdrun -deffnm md " + MPI + " -nsteps $nsteps 2>&1 | tail -6\n",
        kind="bash",
        params={"nsteps": ("Number of steps (2 fs each)", 200, 2000, 500, 100)},
        notebook="Cell 13 of the notebook",
    ),
    Step(
        "analysis", "10. Analysis",
        "`gmx energy` extracts time series from the `.edr` energy files. Plots below show the "
        "potential energy of the minimisation, and temperature, pressure and density later on.",
        "printf 'Potential\\n0\\n' | gmx energy -f emin.edr -o potential.xvg > /dev/null 2>&1\n"
        "printf 'Temperature\\n0\\n' | gmx energy -f nvt.edr -o temperature.xvg > /dev/null 2>&1\n"
        "printf 'Density\\n0\\n' | gmx energy -f npt.edr -o density.xvg > /dev/null 2>&1\n"
        "printf 'Pressure\\n0\\n' | gmx energy -f npt.edr -o pressure.xvg > /dev/null 2>&1\n"
        "ls *.xvg\n",
        kind="bash",
        analysis=True,
        notebook="Cells 14 and 15 of the notebook",
    ),
]
