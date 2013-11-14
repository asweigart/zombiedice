# Zombie Dice simulator by Al Sweigart (al@inventwithpython.com)
# Open BSD license

# Note: Don't ever reassign the CURRENT_GAME_STATE variable directly, or it won't be updated by the tournament code.

from zombiedice import *

class RandomCoinFlipZombie(object):
    """After the first roll, this bot always has a fifty-fifty chance of deciding to roll again or stopping."""
    def __init__(self, name):
        self.name = name

    def turn(self, gameState):
        results = roll() # first roll

        while results and random.randint(0, 1) == 0:
            results = roll()


class MinNumShotgunsThenStopsZombie(object):
    """This bot keeps rolling until it has rolled a minimum number of shotguns."""
    def __init__(self, name, minShotguns=2):
        self.name = name
        self.minShotguns = minShotguns

    def turn(self, gameState):
        shotguns = 0 # number of shotguns rolled this turn
        while shotguns < self.minShotguns:
            results = roll()
            if results == []:
                return
            for i in results:
                if i[ICON] == SHOTGUN:
                    shotguns += 1


class MinNumShotgunsThenStopsOneMoreZombie(object):
    """This bot keeps rolling until it has rolled a minimum number of shotguns, then it rolls one more time."""
    def __init__(self, name, minShotguns=2):
        self.name = name
        self.minShotguns = minShotguns

    def turn(self, gameState):
        shotguns = 0 # number of shotguns rolled this turn
        while shotguns < self.minShotguns:
            results = roll()
            if results == []:
                return
            for i in results:
                if i[ICON] == SHOTGUN:
                    shotguns += 1
        roll()


class HumanPlayerZombie(object):
    """This "bot" actually calls input() and print() to let a human player play Zombie Dice against the other bots."""
    def __init__(self, name):
        self.name = name

    def turn(self, gameState):
        brains = '' # number of brains rolled this turn
        shotguns = '' # number of shotguns rolled this turn
        print('Scores:')
        for zombieName, zombieScore in gameState[SCORES].items():
            print('\t%s - %s' % (zombieScore, zombieName))
        print()

        while True:
            results = roll()
            brains   += ''.join([x[COLOR][0].upper() for x in results if x[ICON] == BRAINS])
            shotguns += ''.join([x[COLOR][0].upper() for x in results if x[ICON] == SHOTGUN])

            print('Roll:')
            for i in range(3):
                print(results[i][COLOR], '\t', results[i][ICON])
            print()
            print('Brains  : %s\t\tShotguns: %s' % (brains, shotguns))
            if len(shotguns) < 3:
                print('Press Enter to roll again, or enter "S" to stop.')
                if platform.python_version().startswith('2.'):
                    response = raw_input() # python 2 code
                else:
                    response = input() # python 3 code
                if response.upper().startswith('S'):
                    return
            else:
                print('Shotgunned! Press Enter to continue.')
                if platform.python_version().startswith('2.'):
                    raw_input() # python 2 code
                else:
                    input() # python 3 code
                return


class RollsUntilInTheLeadZombie(object):
    """This bot's strategy is to keep rolling for brains until they are in the lead (plus an optional number of points). This is a high risk strategy, because if the opponent gets an early lead then this bot will take greater and greater risks to get in the lead in a single turn.

    However, once in the lead, this bot will just use Zombie_MinNumShotgunsThenStops's strategy."""
    def __init__(self, name, plusLead=0):
        self.name = name
        self.plusLead = plusLead
        self.altZombieStrategy = MinNumShotgunsThenStopsZombie(name + '_alt', 2)

    def turn(self, gameState):
        thisZombie = CURRENT_GAME_STATE['CURRENT_ZOMBIE']
        highestScoreThatIsntMine = max([zombieScore for zombieName, zombieScore in gameState[SCORES].items() if zombieName != thisZombie])

        if highestScoreThatIsntMine + self.plusLead >= gameState[SCORES][thisZombie]:
            results = roll() # roll at least once
            brains = len([True for result in results if result[ICON] == BRAINS])
            myScore = gameState[SCORES][thisZombie]

            while results != [] and myScore + brains <= highestScoreThatIsntMine + self.plusLead:
                results = roll()
                brains += len([True for result in results if result[ICON] == BRAINS])
        else:
            # already in the lead, so just use altZombieStrategy's turn()
            self.altZombieStrategy.turn(gameState)


class MonteCarloZombie(object):
    """This bot does several experimental dice rolls with the current cup, and re-rolls if the chance of 3 shotguns is less than "riskiness".
    The bot doesn't care how many brains it has rolled or what the relative scores are, it just looks at the chance of death for the next roll given the current cup."""
    def __init__(self, name, riskiness=50, numExperiments=100):
        self.name = name
        self.riskiness = riskiness
        self.numExperiments = numExperiments

    def turn(self, gameState):
        results = roll() # always do a first roll
        shotguns = len([True for i in results if i[ICON] == SHOTGUN]) # count shotguns from first roll

        if shotguns == 3:
            return # early exit if we rolled three shotguns on the first roll

        while True:
            # run experiments
            deaths = 0
            for i in range(self.numExperiments):
                if shotguns + self.simulatedRollShotguns() >= 3:
                    deaths += 1

            # roll if percentage of deaths < riskiness%
            if deaths / float(self.numExperiments) * 100 < self.riskiness:
                results = roll() # this will update the CURRENT_CUP and ROLLED_BRAINS globals that simulatedRollShotguns() uses.
                shotguns += len([True for i in results if i[ICON] == SHOTGUN])
                if shotguns >= 3:
                    return
            else:
                return

    def simulatedRollShotguns(self):
        """Calculates the number of shotguns rolled with the current cup and rolled brains. (Rolled brains is only used in the rare case that we run out of dice.)"""
        shotguns = 0
        cup = copy.copy(CURRENT_GAME_STATE['CURRENT_CUP'])
        rolledBrains = copy.copy(CURRENT_GAME_STATE['ROLLED_BRAINS'])

        # "ran out of dice", so put the rolled brains back into the cup
        if len(cup) < 3:
            cup.extend(rolledBrains)
            rolledBrains = []

        # add new dice to hand from cup until there are 3 dice in the hand
        hand = []
        for i in range(3):
            newDie = random.choice(cup)
            logging.debug('%s die added to hand from cup.' % (newDie))
            cup.remove(newDie)
            hand.append(newDie)

        # roll the dice
        results = []
        for die in hand:
            results.append(rollDie(die))

        # count the shotguns and remove them from the hand
        for result in results:
            if result[ICON] == SHOTGUN:
                shotguns += 1
                hand.remove(result[COLOR])

        return shotguns
