from .steps import Step

HEAD = """from openmm.app import *
from openmm import *
from openmm.unit import *
"""

FF = "forcefield = ForceField('charmm36.xml', 'charmm36/spce.xml')\n"

LOAD = """pdb = PDBFile('solvated.pdb')
system = XmlSerializer.deserialize(open('%s').read())
integrator = LangevinMiddleIntegrator(300*kelvin, 1/picosecond, 0.004*picoseconds)
simulation = Simulation(pdb.topology, system, integrator)
simulation.loadState('%s')
"""

REPORT = """simulation.reporters.append(StateDataReporter('%s', 10, step=True,
        potentialEnergy=True, temperature=True, volume=True, density=True))
"""

STEPS = [
    Step(
        "prepare", "1. Clean the crystal structure",
        "The PDB file 1AKI comes from X ray crystallography and contains crystal waters. "
        "We remove them, because we will add our own water box later. "
        "`Modeller` is the OpenMM object used to edit a topology and its positions.",
        HEAD + """
pdb = PDBFile('structures/1aki.pdb')
modeller = Modeller(pdb.topology, pdb.positions)
modeller.deleteWater()

PDBFile.writeFile(modeller.topology, modeller.positions, open('clean.pdb', 'w'))
print('Atoms after removing water:', modeller.topology.getNumAtoms())
""",
        notebook="Cell 3 of the notebook",
    ),
    Step(
        "forcefield", "2. Force field and hydrogens",
        "A force field defines the energy of the system: bonds, angles, dihedrals, van der Waals "
        "and electrostatics. Here we use CHARMM36 with the SPC/E water model. "
        "Crystal structures have no hydrogens, so the force field is also used to add them.",
        HEAD + FF + """
pdb = PDBFile('clean.pdb')
modeller = Modeller(pdb.topology, pdb.positions)
modeller.addHydrogens(forcefield)

PDBFile.writeFile(modeller.topology, modeller.positions, open('hydrogens.pdb', 'w'))
print('Atoms with hydrogens:', modeller.topology.getNumAtoms())
""",
        notebook="Cell 4 of the notebook",
    ),
    Step(
        "solvate", "3. Box, water and ions",
        "`addSolvent` builds a periodic box with at least `padding` nm between the protein and the box "
        "edge (the notebook uses 1.0 nm, the demo less, to stay fast), fills it with water and adds ions to neutralise the net charge of lysozyme. "
        "Periodic boundary conditions mean the protein never sees a vacuum surface.",
        HEAD + FF + """from collections import Counter

pdb = PDBFile('hydrogens.pdb')
modeller = Modeller(pdb.topology, pdb.positions)
modeller.addSolvent(forcefield, padding=$padding*nanometer)

PDBFile.writeFile(modeller.topology, modeller.positions, open('solvated.pdb', 'w'))
print('Total atoms:', modeller.topology.getNumAtoms())
print('Box vectors (nm):', modeller.topology.getPeriodicBoxVectors())
names = Counter(r.name for r in modeller.topology.residues())
print('Water molecules:', names['HOH'], ' Na+:', names['NA'], ' Cl-:', names['CL'])
""",
        params={"padding": ("Water padding in nm", 0.4, 1.0, 0.5, 0.1)},
        notebook="Cell 5 of the notebook",
    ),
    Step(
        "minimize", "4. Energy minimisation",
        "The added water and hydrogens can overlap, which gives huge forces. Before any dynamics "
        "we relax the structure by moving atoms downhill in energy. In the demo we cap the number "
        "of iterations, a full minimisation takes longer.",
        HEAD + FF + """
pdb = PDBFile('solvated.pdb')
system = forcefield.createSystem(pdb.topology, nonbondedMethod=PME,
        nonbondedCutoff=1.0*nanometer, constraints=HBonds)
integrator = LangevinMiddleIntegrator(300*kelvin, 1/picosecond, 0.004*picoseconds)
simulation = Simulation(pdb.topology, system, integrator)
simulation.context.setPositions(pdb.positions)

e0 = simulation.context.getState(getEnergy=True).getPotentialEnergy()
print('Energy before:', e0)
simulation.minimizeEnergy(maxIterations=$iters)
e1 = simulation.context.getState(getEnergy=True).getPotentialEnergy()
print('Energy after: ', e1)

simulation.saveState('minimized.xml')
open('system.xml', 'w').write(XmlSerializer.serialize(system))
""",
        params={"iters": ("Maximum minimisation iterations", 5, 100, 20, 5)},
        notebook="Cells 6 and 7 of the notebook",
    ),
    Step(
        "nvt", "5. NVT equilibration",
        "NVT means constant number of atoms, volume and temperature. A Langevin thermostat heats "
        "the system to 300 K. The notebook uses 10000 steps of 4 fs (40 ps), here you choose a "
        "much shorter run.",
        HEAD + LOAD % ("system.xml", "minimized.xml") + """simulation.context.setVelocitiesToTemperature(300*kelvin)
""" + REPORT % "nvt_log.csv" + """
print('Running NVT for $nsteps steps')
simulation.step($nsteps)
simulation.saveState('nvt.xml')
""",
        params={"nsteps": ("Number of steps (4 fs each)", 50, 500, 100, 50)},
        notebook="Cells 8 and 9 of the notebook",
    ),
    Step(
        "npt", "6. NPT equilibration",
        "NPT keeps pressure constant too. A Monte Carlo barostat changes the box volume so that the "
        "water reaches the right density at 1 bar.",
        HEAD + LOAD % ("system.xml", "nvt.xml") + """system.addForce(MonteCarloBarostat(1*bar, 300*kelvin))
simulation.context.reinitialize(preserveState=True)
""" + REPORT % "npt_log.csv" + """
print('Running NPT for $nsteps steps')
simulation.step($nsteps)
simulation.saveState('npt.xml')
open('system_npt.xml', 'w').write(XmlSerializer.serialize(system))
""",
        params={"nsteps": ("Number of steps (4 fs each)", 50, 500, 100, 50)},
        notebook="Cell 10 of the notebook",
    ),
    Step(
        "production", "7. Production run",
        "Now the system is equilibrated and we collect data. In a real project this run lasts "
        "nanoseconds to microseconds. Coordinates are saved to a PDB trajectory.",
        HEAD + LOAD % ("system_npt.xml", "npt.xml") + """simulation.reporters.append(PDBReporter('OpenMM_output.pdb', 50))
""" + REPORT % "md_log.csv" + """
print('Running production for $nsteps steps')
simulation.step($nsteps)
""",
        params={"nsteps": ("Number of steps (4 fs each)", 50, 500, 100, 50)},
        notebook="Cells 8 to 10 of the notebook",
    ),
    Step(
        "analysis", "8. Analysis",
        "The log files hold potential energy, temperature, volume and density as a function of step. "
        "Check that the temperature stays near 300 K and the density of the system settles.",
        "", analysis=True, notebook="Cell 11 of the notebook",
    ),
]
