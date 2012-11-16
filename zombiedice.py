"""

.,:,:::~::::...................,,...................................................................
.ID=.......8MM,...............,M.:..................................................................
.+M?.......M,M,.N,............M..M...........,......................................................
.,MM.........M,M,,MN,.MMMO...:M..7..........M,M7........:......,MMMN..DM............................
.~M.........D$M.~....MM...M..M.=.Z..,,~8N~..M..M....$MM.MM.....M........M....... ............MMM....
.,~8:~ZMM..,MM:......$M,,.M..M...M.MD.....M:M..MMMN..DMNM......M........?N.ZZM, .=MM,...8MMO.~NM....
,.....,M,..MM8:...M~.MM8..I.I8I..MM........MM..MM...~MM.......~8...MMM8..M.M.,D.M,...MMN...,,M,.....
......M+.7M:MM...M.D..MM...7M.~:.M.M.:M~...MM.,MM.M~..,.... ..Z+..MZ..O=.M.M.,NM....:O8M..M8.... ...
.....OD.M=.N:M.,,MMM.,MM...MM..8.M,M......8+8.:NM.MMZ...M.....N:..M....M.M.M.+M...MM?ND.8,MMM$MM....
....I,.M...M7M..M,,M.:MM...M8?MM.M,M.I....N=,.O+M....DM.......O=..=...$=.,D8.8M..M......?.,..M?... .
..,8M.M,...M.M,.M,N,.IMM...,..MM.M,M..?ZM..M..MM..NMMMMN.=MM..Z?... ..M.~,D~.MM.,NMM.MMM..MMMM~.~MN.
.,M~..$MM:.~NMN..MM..MMD..$.+,MM.Z?M..MM..,M..M,M.D....MN.MM..=D.,..NM..:MM..MM,..~$M..M.,8...MN.M$.
.D=......:M~MIM......MM8.?M..M,M..MM.DM..ZM~..M8M......MM~.....M.,M7....,MM..MM..8MM=.MM......NM:...
+M....:....M:?M.....I8M=.MM.DM.M..MM.D.,M..~..MMN8M.MM=........M........M.M..MM.M..7M+.M..M?M7......
M?.,.......O..,M...MM.N:?MD.M,.M..MM..M,...,..M.M:$............M.......M..M..N.MM8D~. ..MM.... .....
.8M...MNM.M.....MM+...?$MM.M:...MZ?.MI......?M,...............7?...,MMM,..II,:  ....................
..~MM?..,MZ,...........MM.......MM..........MM.................M.DM........M?.......................
.......................+M.......................................MM..................................

Zombie Dice is by Steve Jackson Games
http://zombiedice.sjgames.com/


Zombie Dice simulator by Al Sweigart (al@inventwithpython.com)
(I'm not affiliated with SJ Games. This is a hobby project.)

TODO - add instructions for writing bots.

Note: A "turn" is a single player's turn. A "round" is every player having one turn.
Note: Since all variables are public in Python, it is trivial to have a bot that hacks the tournament code. Inspect the bot code before running it.
Note: We don't use OOP for bots. A "zombie dice bot" simply implements a turn() method which calls a global roll() function as often as it likes. See documentation for details.
"""


import copy, random, logging, sys, itertools
logging.basicConfig(level=logging.ERROR, format='%(asctime)s - %(levelname)s - %(message)s')
logging.debug('Start of the program.')

# constants, to keep a typo in a string from making weird errors
COLOR = 'color'
ICON = 'icon'
RED = 'red'
GREEN = 'green'
YELLOW = 'yellow'
SHOTGUN = 'shotgun'
BRAINS = 'brains'
FOOTSTEPS = 'footsteps'
SCORES = 'scores'

VERBOSE = False # if True, program outputs the actions that happen during the game

def runGame(zombies):
    """Runs a single game of zombie dice. zombies is a list of zombie dice bot objects."""
    global CURRENT_ZOMBIE # string of the zombie whose turn it is currently
    global CURRENT_CUP # list of dice strings (i.e. 'red', 'yellow', 'green')
    global CURRENT_HAND # list of dice being rolled (should always be three)
    global NUM_SHOTGUNS_ROLLED # number of shotguns rolled this turn
    global NUM_BRAINS_ROLLED # number of brains rolled this turn
    global ROLLED_BRAINS # list of dice strings for each brain rolled, used in the rare event we run out of brain dice

    # create a new game state object
    playerScores = dict([(zombie.name, 0) for zombie in zombies])
    playerOrder = [zombie.name for zombie in zombies]
    logging.debug('Player order: ' + ', '.join(playerOrder))
    gameState = {'order': playerOrder,
                 'scores': playerScores,
                 'round': 0}

    # validate zombie objects, return None to signify an aborted game
    if len(playerOrder) != len(set(playerOrder)): # set() will get rid of any duplicates
        logging.error('Zombies must have unique names.')
        return
    if len(playerOrder) < 2:
        logging.error('Need at least two zombies to play.')
        return
    for zombie in zombies:
        if 'turn' not in dir(zombie):
            logging.error('All zombies need a turn() method.')
        if 'name' not in dir(zombie):
            logging.error('All zombies need a name member.')

    # call every zombie's newGame() method, if it has one
    for zombie in zombies:
        if 'newGame' in dir(zombie):
            zombie.newGame()

    # set up for a new game
    lastRound = False # True when a player has reached 13 brains
    tieBreakingRound = False # True when the "last round" ended in a tie
    zombiesInPlay = copy.copy(zombies) # all zombies play
    while True: # game loop
        gameState['round'] += 1
        logging.debug('ROUND #%s, scores: %s' % (gameState['round'], gameState[SCORES]))
        if VERBOSE: print('Round #%s' % (gameState['round']))
        for zombie in zombiesInPlay:
            CURRENT_ZOMBIE = zombie.name
            logging.debug('NEW TURN: %s' % (CURRENT_ZOMBIE))
            if VERBOSE: print("%s's turn." % (CURRENT_ZOMBIE))

            # set up for a new turn
            CURRENT_CUP = [RED] * 3 + [YELLOW] * 4 + [GREEN] * 6
            random.shuffle(CURRENT_CUP)
            CURRENT_HAND = []
            NUM_SHOTGUNS_ROLLED = 0
            NUM_BRAINS_ROLLED = 0
            ROLLED_BRAINS = [] # list of dice colors, in case of "ran out of dice"

            # run the turn (don't pass the original gameState)
            zombie.turn(copy.deepcopy(gameState))
            if VERBOSE and NUM_SHOTGUNS_ROLLED < 3: print('%s stops.' % (CURRENT_ZOMBIE))
            if VERBOSE and NUM_SHOTGUNS_ROLLED >= 3: print('%s is shotgunned.' % (CURRENT_ZOMBIE))

            # add brains to the score
            if NUM_SHOTGUNS_ROLLED < 3:
                gameState[SCORES][zombie.name] += NUM_BRAINS_ROLLED

            if gameState[SCORES][zombie.name] >= 13:
                # once a player reaches 13 brains, it becomes the last round
                lastRound = True
                logging.debug('LAST ROUND')
                if VERBOSE: print('%s has reached 13 brains.' % (zombie.name))

        if tieBreakingRound:
            break # there is only one tie-breaking round, so after it end the game

        if lastRound:
            # only zombies tied with the highest score go on to the tie-breaking round (if there is one)
            zombiesInPlay = []
            highestScore = max(gameState[SCORES].values()) # used for tie breaking round
            # zombiesInPlay will now only have the zombies tied with the highest score:
            zombiesInPlay = [zombie for zombie in zombies if gameState[SCORES][zombie.name] == highestScore]

            if len(zombiesInPlay) == 1:
                # only one winner, so end the game
                break
            else:
                # multiple winners, so go on to the tie-breaking round.
                logging.debug('TIE BREAKING ROUND')
                if VERBOSE: print('Tie breaking round with %s' % (', '.join([zombie.name for zombie in zombiesInPlay])))
                tieBreakingRound = True

    # call every zombie's endGame() method, if it has one
    for zombie in zombies:
        if 'endGame' in dir(zombie):
            zombie.endGame(copy.deepcopy(gameState))

    # rank bots by score
    ranking = sorted(gameState[SCORES].items(), key=lambda x: x[1], reverse=True)
    highestScore = ranking[0][1]
    logging.debug('Ranking: %s' % (ranking))
    if VERBOSE: print('Final Scores: %s' % (', '.join(['%s %s' % (x[0], x[1]) for x in ranking])))     #(', '.join(['%s %s' % (name, score) for name, score in ranking.items()])))

    # winners are the bot(s) with the highest score
    winners = [x[0] for x in ranking if x[1] == highestScore]
    logging.debug('Winner(s): %s' % (winners))
    if VERBOSE: print('Winner%s: %s' % ((len(winners) != 1 and 's' or ''), ', '.join(winners)))

    return gameState

def runTournament(zombies, numGames):
    """A tournament is one or more games of Zombie Dice. The bots are re-used between games, so they can remember previous games.
    zombies is a list of zombie bot objects. numGames is an int of how many games to run."""
    tournamentState = {'wins': dict([(zombie.name, 0) for zombie in zombies]),
                       'ties': dict([(zombie.name, 0) for zombie in zombies])}

    for i in range(numGames):
        random.shuffle(zombies) # randomize the order
        endState = runGame(zombies) # use the same zombie objects so they can remember previous games.

        if endState is None:
            sys.exit('Error when running game.')

        ranking = sorted(endState[SCORES].items(), key=lambda x: x[1], reverse=True)
        highestScore = ranking[0][1]
        winners = [x[0] for x in ranking if x[1] == highestScore]
        if len(winners) == 1:
            tournamentState['wins'][ranking[0][0]] += 1
        elif len(winners) > 1:
            for score in endState[SCORES].items():
                if score[1] == highestScore:
                    tournamentState['ties'][score[0]] += 1

    # print out the tournament results in neatly-formatted columns.
    print('Tournament results:')
    maxNameLength = max([len(zombie.name) for zombie in zombies])

    winsRanking = sorted(tournamentState['wins'].items(), key=lambda x: x[1], reverse=True)
    print('Wins:')
    for winnerName, winnerScore in winsRanking:
        print('    %s %s' % (winnerName.rjust(maxNameLength), str(winnerScore).rjust(len(str(numGames)))))

    tiesRanking = sorted(tournamentState['ties'].items(), key=lambda x: x[1], reverse=True)
    print('Ties:')
    for tiedName, tiedScore in tiesRanking:
        print('    %s %s' % (tiedName.rjust(maxNameLength), str(tiedScore).rjust(len(str(numGames)))))

def runOneOnOne(zombies, numGames):
    # have each zombie play every other zombie in a one-on-one match
    pass # TODO

def roll():
    """This global function is called by a zombie bot object to indicate that they wish to roll the dice.
    The state of the game and previous rolls are held in global variables."""
    global CURRENT_ZOMBIE, CURRENT_CUP, CURRENT_HAND, NUM_SHOTGUNS_ROLLED, NUM_BRAINS_ROLLED, ROLLED_BRAINS

    # make sure zombie can actually roll
    if NUM_SHOTGUNS_ROLLED >= 3:
        return []

    logging.debug(CURRENT_ZOMBIE + ' rolls. (brains: %s, shotguns: %s)' % (NUM_BRAINS_ROLLED, NUM_SHOTGUNS_ROLLED))
    if VERBOSE: print('%s rolls. (brains: %s, shotguns: %s)' % (CURRENT_ZOMBIE, NUM_BRAINS_ROLLED, NUM_SHOTGUNS_ROLLED))

    # "ran out of dice", so put the rolled brains back into the cup
    if 3 - len(CURRENT_HAND) > len(CURRENT_CUP):
        logging.debug('Out of dice! Putting rolled brains back into cup.')
        CURRENT_CUP.extend(ROLLED_BRAINS)
        ROLLED_BRAINS = []

    # add new dice to hand from cup until there are 3 dice in the hand
    while len(CURRENT_HAND) < 3:
        newDie = random.choice(CURRENT_CUP)
        logging.debug('%s die added to hand from cup.' % (newDie))
        CURRENT_CUP.remove(newDie)
        CURRENT_HAND.append(newDie)

    # roll the dice
    logging.debug('Hand is %s' % (', '.join(CURRENT_HAND)))
    logging.debug('Cup has %s: %s' % (len(CURRENT_CUP), ', '.join(CURRENT_CUP)))
    results = []
    for die in CURRENT_HAND:
        results.append(rollDie(die))
    resultStr = ['%s_%s' % (result[COLOR][0].upper(), result[ICON][:2]) for result in results]
    logging.debug('%s rolled %s' % (CURRENT_ZOMBIE, ', '.join(resultStr)))
    if VERBOSE: print(', '.join(['%s %s' % (result[COLOR].title(), result[ICON]) for result in results]))

    # count the shotguns and remove them from the hand
    for result in results:
        if result[ICON] == SHOTGUN:
            NUM_SHOTGUNS_ROLLED += 1
            logging.debug('Removing ' + result[COLOR] + ' from hand for shotgun.')
            CURRENT_HAND.remove(result[COLOR])

    # count the brains and remove them from the hand
    for result in results:
        if result[ICON] == BRAINS:
            ROLLED_BRAINS.append(result[COLOR])
            NUM_BRAINS_ROLLED += 1
            logging.debug('Removing ' + result[COLOR] + ' from hand for brains.')
            CURRENT_HAND.remove(result[COLOR])

    return results


def rollDie(die):
    """Returns the result of a single die roll as a dictionary with keys 'color' and 'icon'.
    The die parameter is a string of the color of the die (i.e. 'green', 'yellow', 'red').
    The 'color' values in the return dict are one of 'green', 'yellow', 'red'.
    The 'icon' values are one of 'shotgun', 'footsteps', 'brains'."""
    roll = random.randint(1, 6)
    if die == RED:
        if roll in (1, 2, 3):
            return {COLOR: RED, ICON: SHOTGUN}
        elif roll in (4, 5):
            return {COLOR: RED, ICON: FOOTSTEPS}
        elif roll in (6,):
            return {COLOR: RED, ICON: BRAINS}
    elif die == YELLOW:
        if roll in (1, 2):
            return {COLOR: YELLOW, ICON: SHOTGUN}
        elif roll in (3, 4):
            return {COLOR: YELLOW, ICON: FOOTSTEPS}
        elif roll in (5, 6):
            return {COLOR: YELLOW, ICON: BRAINS}
    elif die == GREEN:
        if roll in (1,):
            return {COLOR: GREEN, ICON: SHOTGUN}
        elif roll in (2, 3):
            return {COLOR: GREEN, ICON: FOOTSTEPS}
        elif roll in (4, 5, 6):
            return {COLOR: GREEN, ICON: BRAINS}



# ==== SIMPLE ZOMBIE BOTS =========================
class ZombieBot_MinNumBrainsThenStops(object):
    """This bot keeps rolling until it has acquired a minimum number of brains."""
    def __init__(self, name, minBrains):
        self.name = name
        self.minBrains = minBrains

    def turn(self, gameState):
        brains = 0 # number of brains rolled this turn
        while brains < self.minBrains:
            results = roll()
            if results == []:
                return
            for i in results:
                if i[ICON] == BRAINS:
                    brains += 1

class ZombieBot_MinNumShotgunsThenStops(object):
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


class ZombieBot_MinNumBrainsShotgunsThenStops(object):
    """This bot keeps rolling until it has rolled a minimum number of brains OR shotguns."""
    def __init__(self, name, minBrains, minShotguns):
        self.name = name
        self.minBrains = minBrains
        self.minShotguns = minShotguns

    def turn(self, gameState):
        shotguns = 0 # number of shotguns rolled this turn
        brains = 0 # number of brains rolled this turn
        while shotguns < self.minShotguns and brains < self.minBrains:
            results = roll()
            if results == []:
                return
            for i in results:
                if i[ICON] == SHOTGUN:
                    shotguns += 1
                elif i[ICON] == BRAINS:
                    brains += 1

class ZombieBot_RollsUntilInTheLead(object):
    """This bot's strategy is to keep rolling for brains until they are in the lead (plus an optional number of points). This is a high risk strategy, because if the opponent gets an early lead then this bot will take greater and greater risks to get in the lead in a single turn.

    However, once in the lead, this bot will just use Zombie_MinNumShotgunsThenStops's strategy."""
    def __init__(self, name, plusLead=0):
        self.name = name
        self.plusLead = plusLead
        self.altZombieStrategy = ZombieBot_MinNumShotgunsThenStops(name + '_alt', 2)

    def turn(self, gameState):
        highestScoreThatIsntMine = max([zombieScore for zombieName, zombieScore in gameState[SCORES].items() if zombieName != CURRENT_ZOMBIE])

        if highestScoreThatIsntMine + self.plusLead >= gameState[SCORES][CURRENT_ZOMBIE]:
            results = roll() # roll at least once
            brains = len([True for result in results if result[ICON] == BRAINS])
            myScore = gameState[SCORES][CURRENT_ZOMBIE]

            while results != [] and myScore + brains <= highestScoreThatIsntMine + self.plusLead:
                results = roll()
                brains += len([True for result in results if result[ICON] == BRAINS])
        else:
            # already in the lead, so just use altZombieStrategy's turn()
            self.altZombieStrategy.turn(gameState)


class ZombieBot_MinGreenBrainsThenStops(object):
    """This bot will keep rolling until it has BOTH a minimum number of brains and a minimum number of green brains. The idea being that if the bot has rolled several non-green brains, there are still green brains out there that give it good odds to roll in the future.

    This bot ignores how many shotguns it has rolled."""
    def __init__(self, name, minGreenBrains, minAllBrains):
        self.name = name
        self.minGreenBrains = minGreenBrains
        self.minAllBrains = minAllBrains

    def turn(self, gameState):
        greenBrains = 0 # number of GREEN brains rolled this turn
        allBrains = 0 # number of brains rolled this turn
        while greenBrains < self.minGreenBrains or allBrains < self.minAllBrains:
            results = roll()
            if results == []:
                return
            for i in results:
                if i[ICON] == BRAINS and i[COLOR] == GREEN:
                    greenBrains += 1
                if i[ICON] == BRAINS:
                    allBrains += 1


class ZombieBot_RandomCoinFlip(object):
    """After the first roll, this bot always has a fifty-fifty chance of deciding to roll again or stopping."""
    def __init__(self, name):
        self.name = name

    def turn(self, gameState):
        results = roll() # first roll

        while results and random.randint(0, 1) == 0:
            results = roll()


class ZombieBot_HumanPlayer(object):
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
                response = input()
                if response.upper().startswith('S'):
                    return
            else:
                print('Shotgunned! Press Enter to continue.')
                input()
                return


class ZombieBot_MonteCarlo(object):
    """This bot does several experimental dice rolls with the current cup, and re-rolls if the chance of 3 shotguns is less than "riskiness".
    The bot doesn't care how many brains it has rolled or what the relative scores are, it just looks at the chance of death for the next roll given the current cup."""
    def __init__(self, name, riskiness=50, numExperiments=10):
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
        cup = copy.copy(CURRENT_CUP)
        rolledBrains = copy.copy(ROLLED_BRAINS)

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


class ZombieBot_Calculate(object):
    """This bot does calculates the odds of dying with the current cup, and re-rolls if the chance of 3 shotguns is less than "riskiness".
    The bot doesn't care how many brains it has rolled or what the relative scores are, it just looks at the chance of death for the next roll given the current cup."""

    pass

    # TODO - finsih
    """
    RED_SHOTGUN_CHANCE    = 3.0 / 6.0
    YELLOW_SHOTGUN_CHANCE = 2.0 / 6.0
    GREEN_SHOTGUN_CHANCE  = 1.0 / 6.0
    SHOTGUN_CHANCE = {RED:    RED_SHOTGUN_CHANCE,
                      YELLOW: YELLOW_SHOTGUN_CHANCE,
                      GREEN:  GREEN_SHOTGUN_CHANCE}
    NONSHOTGUN_CHANCE = {RED:    1.0 - RED_SHOTGUN_CHANCE,
                         YELLOW: 1.0 - YELLOW_SHOTGUN_CHANCE,
                         GREEN:  1.0 - GREEN_SHOTGUN_CHANCE}

    def __init__(self, name, riskiness=50):
        self.name = name
        self.riskiness = riskiness

    def turn(self, gameState):
        results = roll() # always do a first roll
        shotguns = len([True for i in results if i[ICON] == SHOTGUN]) # count shotguns from first roll

        if shotguns == 3:
            return # early exit if we rolled three shotguns on the first roll

        while True:
            cup = copy.copy(CURRENT_CUP)
            rolledBrains = copy.copy(ROLLED_BRAINS)
            # "ran out of dice", so put the rolled brains back into the cup
            if len(cup) < 3:
                cup.extend(rolledBrains)

            # calculate chance of death
            chanceDeath = 0.0
            totalRolls = 0
            for dice in itertools.permutations(cup):
                dice = dice[:3] # only use first three dice
                numRedDice =    len([True for die in dice if die == RED])
                numGreenDice =  len([True for die in dice if die == GREEN])
                numYellowDice = len([True for die in dice if die == YELLOW])

                # find chance of 1 and only 1 shotgun
                oneShotgun = (SHOTGUN_CHANCE[dice[0]] * NONSHOTGUN_CHANCE[dice[1]] * NONSHOTGUN_CHANCE[dice[2]]) + \
                             (NONSHOTGUN_CHANCE[dice[0]] * SHOTGUN_CHANCE[dice[1]] * NONSHOTGUN_CHANCE[dice[2]]) + \
                             (NONSHOTGUN_CHANCE[dice[0]] * NONSHOTGUN_CHANCE[dice[1]] * SHOTGUN_CHANCE[dice[2]])

                # find chance of 2 and only 2 shotguns
                twoShotgunsChance = (SHOTGUN_CHANCE[dice[0]] * NONSHOTGUN_CHANCE[dice[1]] * NONSHOTGUN_CHANCE[dice[2]]) + \
                                    (NONSHOTGUN_CHANCE[dice[0]] * SHOTGUN_CHANCE[dice[1]] * NONSHOTGUN_CHANCE[dice[2]]) + \
                                    (NONSHOTGUN_CHANCE[dice[0]] * NONSHOTGUN_CHANCE[dice[1]] * SHOTGUN_CHANCE[dice[2]])

                # find chance of 3 and only 3 shotguns
                threeShotgunsChance = SHOTGUN_CHANCE[dice[0]] + SHOTGUN_CHANCE[dice[1]] + SHOTGUN_CHANCE[dice[2]]

                chanceDeath += (numRedDice * (3/6.0)) + (numYellowDice * (2/6.0)) + (numGreenDice * (1/6.0))
                totalRolls += 1
            # TODO - ACK! This is wrong, this is the chance of a shotgun. There can be multiple shotguns, and we need to factor in the shotguns the player already has.
            print('>>>>> Chance of death: %s' % (chanceDeath/totalRolls)
    """


# ==== RUN TOURNAMENT CODE ======================
def main():
    global VERBOSE
    VERBOSE = False

    # fill up the zombies list with different bot objects, and then pass to runTournament()
    zombies = []
    #zombies.append(ZombieBot_MinNumBrainsThenStops('Min2brains', 2))
    #zombies.append(ZombieBot_MinNumBrainsThenStops('Min3brains', 3))
    #zombies.append(ZombieBot_MinNumShotgunsThenStops('Min1shotguns', 1))
    zombies.append(ZombieBot_MinNumShotgunsThenStops('Min2shotguns', 2))
    #zombies.append(ZombieBot_MinGreenBrainsThenStops('Min3brains1green', 1, 3))
    #zombies.append(ZombieBot_MinNumBrainsShotgunsThenStops('Min3b2s', 3, 2))
    #zombies.append(ZombieBot_MinNumBrainsShotgunsThenStops('Min4b2s', 4, 2))
    #zombies.append(ZombieBot_MinNumBrainsShotgunsThenStops('Min5b2s', 5, 2))
    #zombies.append(ZombieBot_MinNumBrainsShotgunsThenStops('Min6b2s', 6, 2))
    #zombies.append(ZombieBot_MinNumBrainsShotgunsThenStops('Min7b2s', 7, 2))
    #zombies.append(ZombieBot_MinNumBrainsShotgunsThenStops('Min8b2s', 8, 2))
    #zombies.append(ZombieBot_MinNumBrainsShotgunsThenStops('Min9b2s', 9, 2))
    #zombies.append(ZombieBot_MinNumBrainsShotgunsThenStops('Min10b2s', 10, 2))
    #zombies.append(ZombieBot_MinNumBrainsShotgunsThenStops('Min11b2s', 11, 2))
    #zombies.append(ZombieBot_MinNumBrainsShotgunsThenStops('Min99b2s', 99, 2))
    #zombies.append(ZombieBot_RollsUntilInTheLead('RollsUntilLead'))
    #zombies.append(ZombieBot_RollsUntilInTheLead('RollsUntilLead+1', 1))
    zombies.append(ZombieBot_RandomCoinFlip('RandomCoinFlip'))
    #zombies.append(ZombieBot_HumanPlayer('Al'))
    #zombies.append(ZombieBot_MonteCarlo('MonteCarlo100', 50, 100))
    #zombies.append(ZombieBot_MonteCarlo('MonteCarlo200', 50, 200))
    #zombies.append(ZombieBot_Calculate('Calculate50', 50))
    runTournament(zombies, 1000)

if __name__ == '__main__':
    main()
