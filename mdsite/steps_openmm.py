from .steps import Step

HEAD = """from openmm.app import *
from openmm import *
from openmm.unit import *
"""

FF = "forcefield = ForceField('amber14-all.xml', 'implicit/gbn2.xml')\n"

LOAD = """pdb = PDBFile('hydrogens.pdb')
system = XmlSerializer.deserialize(open('system.xml').read())
integrator = LangevinMiddleIntegrator(300*kelvin, 1/picosecond, 0.002*picoseconds)
simulation = Simulation(pdb.topology, system, integrator)
simulation.loadState('%s')
"""

NOTE = (
    " The demo uses implicit solvent (water as a continuum) so it runs in seconds. "
    "The notebook uses explicit water in a periodic box, with PME and a barostat."
)

STEPS = [
    Step(
        "prepare", "1. Clean the crystal structure",
        "The PDB file 1AKI comes from X ray crystallography and contains crystal waters. "
        "We remove them first. `Modeller` is the OpenMM object used to edit a topology and "
        "its positions.",
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
        "and electrostatics. Crystal structures have no hydrogens, so the force field is also "
        "used to add them. Here: AMBER14 with the GBn2 implicit solvent model." + NOTE,
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
        "minimize", "3. Energy minimisation",
        "Added hydrogens can sit too close to other atoms, which gives large forces. Before any "
        "dynamics we relax the structure by moving atoms downhill in energy. Constraints on "
        "bonds with hydrogen allow a 2 fs time step later.",
        HEAD + FF + """
pdb = PDBFile('hydrogens.pdb')
system = forcefield.createSystem(pdb.topology, nonbondedMethod=NoCutoff,
        constraints=HBonds)
integrator = LangevinMiddleIntegrator(300*kelvin, 1/picosecond, 0.002*picoseconds)
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
        params={"iters": ("Maximum minimisation iterations", 50, 500, 200, 50)},
        notebook="Cell 7 of the notebook",
    ),
    Step(
        "heat", "4. Heating",
        "We warm the protein from 50 K to 300 K in six stages with a Langevin thermostat, so the "
        "structure is not shocked by sudden motion. The notebook equilibrates for longer." + NOTE,
        HEAD + LOAD % "minimized.xml" + """
simulation.context.setVelocitiesToTemperature(50*kelvin)
simulation.reporters.append(StateDataReporter('heat_log.csv', 10, step=True,
        potentialEnergy=True, temperature=True))

stage = $nsteps // 6
for T in (50, 100, 150, 200, 250, 300):
    integrator.setTemperature(T*kelvin)
    print('Heating at', T, 'K for', stage, 'steps')
    simulation.step(stage)
simulation.saveState('heated.xml')
""",
        params={"nsteps": ("Total heating steps (2 fs each)", 60, 600, 120, 60)},
        notebook="Cells 8 and 9 of the notebook",
    ),
    Step(
        "production", "5. Production run",
        "At 300 K we now record the trajectory. In a real project this run lasts nanoseconds to "
        "microseconds. Coordinates are saved to a PDB file you can open in a viewer.",
        HEAD + LOAD % "heated.xml" + """
simulation.reporters.append(PDBReporter('OpenMM_output.pdb', 50))
simulation.reporters.append(StateDataReporter('md_log.csv', 10, step=True,
        potentialEnergy=True, temperature=True))

print('Running production for $nsteps steps')
simulation.step($nsteps)
""",
        params={"nsteps": ("Number of steps (2 fs each)", 50, 500, 100, 50)},
        notebook="Cells 8 to 10 of the notebook",
    ),
    Step(
        "analysis", "6. Analysis",
        "The log files hold potential energy and temperature as a function of step. Check that "
        "the temperature climbs to 300 K during heating and then fluctuates around it.",
        "", analysis=True, notebook="Cell 11 of the notebook",
    ),
]
