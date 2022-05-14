from . import ICON, SHOTGUN, COLOR, BRAINS, roll, rollDie
import copy
import logging
import platform
import random

if platform.python_version().startswith('2.'):
    input = raw_input # python 2 code


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
            diceRollResults = roll()

            if diceRollResults is None:
                return

            shotguns += diceRollResults[SHOTGUN] # increase shotguns by the number of shotgun die rolls.


class MinNumShotgunsThenStopsOneMoreZombie(object):
    """This bot keeps rolling until it has rolled a minimum number of shotguns, then it rolls one more time."""
    def __init__(self, name, minShotguns=2):
        self.name = name
        self.minShotguns = minShotguns

    def turn(self, gameState):
        shotguns = 0 # number of shotguns rolled this turn
        while shotguns < self.minShotguns:
            diceRollResults = roll()

            if diceRollResults is None:
                return

            shotguns += diceRollResults[SHOTGUN] # increase shotguns by the number of shotgun die rolls.
        roll() # Roll one more time.


class HumanPlayerZombie(object):
    """This "bot" actually calls input() and print() to let a human player play Zombie Dice against the other bots."""
    def __init__(self, name):
        self.name = name

    def turn(self, gameState):
        brains = '' # brains rolled this turn
        shotguns = '' # shotguns rolled this turn
        print('Scores:')
        for zombieName, zombieScore in gameState['SCORES'].items():
            print('\t%s - %s' % (zombieScore, zombieName))
        print()

        while True:
            diceRollResults = roll()
            brains   += ''.join([x[COLOR][0].upper() for x in diceRollResults['rolls'] if x[ICON] == BRAINS])
            shotguns += ''.join([x[COLOR][0].upper() for x in diceRollResults['rolls'] if x[ICON] == SHOTGUN])

            print('Roll:')
            for i in range(3):
                print(diceRollResults['rolls'][i][COLOR], '\t', diceRollResults['rolls'][i][ICON])
            print()
            print('Brains  : %s\t\tShotguns: %s' % (brains, shotguns))
            if len(shotguns) < 3:
                print('Press Enter to roll again, or enter "S" to stop.')
                response = input()
                if response.upper().startswith('S'):
                    return
            else:
                print('Shotgunned! Press Enter to continue.')
                input()
                return


class RollsUntilInTheLeadZombie(object):
    """This bot's strategy is to keep rolling for brains until they are in the lead (plus an optional number of points). This is a high risk strategy, because if the opponent gets an early lead then this bot will take greater and greater risks to get in the lead in a single turn.

    However, once in the lead, this bot will just use MinNumShotgunsThenStopsZombie's strategy."""
    def __init__(self, name, plusLead=0):
        self.name = name
        self.plusLead = plusLead
        self.altZombieStrategy = MinNumShotgunsThenStopsZombie(name + '_alt', 2)

    def turn(self, gameState):
        thisZombie = gameState['CURRENT_ZOMBIE']
        highestScoreThatIsntMine = max([zombieScore for zombieName, zombieScore in gameState['SCORES'].items() if zombieName != thisZombie])

        if highestScoreThatIsntMine + self.plusLead >= gameState['SCORES'][thisZombie]:
            diceRollResults = roll() # roll at least once
            brains = diceRollResults[BRAINS]
            myScore = gameState['SCORES'][thisZombie]

            while myScore + brains <= highestScoreThatIsntMine + self.plusLead:
                diceRollResults = roll()
                if diceRollResults is None:
                    return
                brains += diceRollResults[BRAINS]
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
        diceRollResults = roll() # always do a first roll
        shotguns = diceRollResults[SHOTGUN]

        if shotguns == 3:
            return # early exit if we rolled three shotguns on the first roll

        while True:
            # run experiments
            deaths = 0
            for i in range(self.numExperiments):
                if shotguns + self.simulatedRollShotguns(copy.deepcopy(gameState)) >= 3:
                    deaths += 1

            # roll if percentage of deaths < riskiness%
            if deaths / float(self.numExperiments) * 100 < self.riskiness:
                diceRollResults = roll() # this will update the CURRENT_CUP and ROLLED_BRAINS_DETAILS globals that simulatedRollShotguns() uses.
                shotguns += diceRollResults[SHOTGUN]
                if shotguns >= 3:
                    return
            else:
                return

    def simulatedRollShotguns(self, gameState):
        """Calculates the number of shotguns rolled with the current cup and rolled brains. (Rolled brains is only used in the rare case that we run out of dice.)"""
        shotguns = 0
        cup = gameState['CURRENT_CUP'] # cup is just a list of 'red', 'green', 'yellow' strings for the types of dice in it
        rolledBrains = gameState['ROLLED_BRAINS_DETAILS']

        # "ran out of dice", so put the rolled brains back into the cup
        if len(cup) < 3:
            cup.extend(rolledBrains)
            rolledBrains = []

        # add new dice to hand from cup until there are 3 dice in the hand
        hand = [] # hand is just a list of 'red', 'green', 'yellow' strings for the types of dice in it
        for i in range(3):
            newDie = random.choice(cup)
            logging.debug('%s die added to hand from cup.' % (newDie))
            cup.remove(newDie)
            hand.append(newDie)

        # roll the dice
        dieRollResults = []
        for die in hand:
            dieRollResults.append(rollDie(die))

        # count the shotguns and remove them from the hand
        for result in dieRollResults:
            if result[ICON] == SHOTGUN:
                shotguns += 1
                hand.remove(result[COLOR])

        return shotguns


class CrashZombie(object):
    """This bot simply crashes. This tests the exception-handling code in the tournament program."""
    def __init__(self, name):
        self.name = name

    def turn(self, gameState):
        42 / 0 # divide-by-zero roll


class SlowZombie(object):
    """This zombie simply takes too long. This tests the MAX_TURN_TIME code in the tournament program."""
    def __init__(self, name):
        self.name = name

    def turn(self, gameState):
        import time
        time.sleep(2)
        roll() # just rolls once


class AlwaysRollsTwiceZombie(object):
    # This example zombie bot always rolls exactly twice on its turn.
    def __init__(self, name):
        self.name = name

    def turn(self, gameState):
        roll()
        roll()
