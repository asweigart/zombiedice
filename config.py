import zombiedice
import zombiebotexamples

bots = (
    zombiebotexamples.RandomCoinFlipZombie(name='Random Bot'),
    zombiebotexamples.MonteCarloZombie(name='Monte Carlo Bot', riskiness=40, numExperiments=20),
    zombiebotexamples.MinNumShotgunsThenStopsZombie(name='Min 2 Shotguns Bot', minShotguns=2)
)
zombiedice(games=100, bots=bots, ui='web')