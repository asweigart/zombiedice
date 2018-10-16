from zombiedice import runTournament, runWebGui
import zombiedice

zombies = (
    zombiedice.examples.RandomCoinFlipZombie(name='Random'),
    zombiedice.examples.MonteCarloZombie(name='Monte Carlo', riskiness=40, numExperiments=20),
    zombiedice.examples.MinNumShotgunsThenStopsZombie(name='Min 2 Shotguns', minShotguns=2)
    # Add any other zombie players here.
)

# Uncomment one of the following lines to run in CLI or Web GUI mode:
#runTournament(zombies=zombies, numGames=100, verbose=False)
runWebGui(zombies=zombies, numGames=100, verbose=False)

