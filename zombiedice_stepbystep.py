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

Note: A "turn" is a single player's turn. A "round" is every player having one turn.
Note: Since all variables are public in Python, it is trivial to have a bot that hacks the tournament code. Inspect the bot code before running it.
Note: We don't use OOP for bots. A "zombie dice bot" simply implements a turn() method which calls a global roll() function as often as it likes. See documentation for details.
"""

import logging, random, sys, copy
logging.basicConfig(level=logging.ERROR, format='%(asctime)s - %(levelname)s - %(message)s')
logging.debug('Start of the Zombie Dice program.')

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

TOURNAMENT_STATE = None

def main():
    # pass runTournament() a list of bot objects
    bots = [ZombieBot_MonteCarlo('MonteCarlo', 40, 100),
            ZombieBot_MinNumShotgunsThenStops('Min2ShotgunsBot', 2),
            ZombieBot_RandomCoinFlip('RandomBot'),
            ]
    runTournament(bots, 1000)


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
    global TOURNAMENT_STATE
    TOURNAMENT_STATE = {'gameNumber': 0,
                        'wins': dict([(zombie.name, 0) for zombie in zombies]),
                        'ties': dict([(zombie.name, 0) for zombie in zombies])}

    print('Tournament of %s games started...' % (numGames))

    for TOURNAMENT_STATE['gameNumber'] in range(numGames):
        random.shuffle(zombies) # randomize the order
        endState = runGame(zombies) # use the same zombie objects so they can remember previous games.

        if endState is None:
            sys.exit('Error when running game.')

        ranking = sorted(endState[SCORES].items(), key=lambda x: x[1], reverse=True)
        highestScore = ranking[0][1]
        winners = [x[0] for x in ranking if x[1] == highestScore]
        if len(winners) == 1:
            TOURNAMENT_STATE['wins'][ranking[0][0]] += 1
        elif len(winners) > 1:
            for score in endState[SCORES].items():
                if score[1] == highestScore:
                    TOURNAMENT_STATE['ties'][score[0]] += 1

    TOURNAMENT_STATE['gameNumber'] += 1 # increment to show all games are finished

    # print out the tournament results in neatly-formatted columns.
    print('Tournament results:')
    maxNameLength = max([len(zombie.name) for zombie in zombies])

    winsRanking = sorted(TOURNAMENT_STATE['wins'].items(), key=lambda x: x[1], reverse=True)
    print('Wins:')
    for winnerName, winnerScore in winsRanking:
        print('    %s %s' % (winnerName.rjust(maxNameLength), str(winnerScore).rjust(len(str(numGames)))))

    tiesRanking = sorted(TOURNAMENT_STATE['ties'].items(), key=lambda x: x[1], reverse=True)
    print('Ties:')
    for tiedName, tiedScore in tiesRanking:
        print('    %s %s' % (tiedName.rjust(maxNameLength), str(tiedScore).rjust(len(str(numGames)))))


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



class ZombieBot_RandomCoinFlip(object):
    """After the first roll, this bot always has a fifty-fifty chance of deciding to roll again or stopping."""
    def __init__(self, name, profileImageFile=None):
        self.name = name
        self.profileImageFile = profileImageFile

    def turn(self, gameState):
        results = roll() # first roll

        while results and random.randint(0, 1) == 0:
            results = roll()


class ZombieBot_MinNumShotgunsThenStops(object):
    """This bot keeps rolling until it has rolled a minimum number of shotguns."""
    def __init__(self, name, minShotguns=2, profileImageFile=None):
        self.name = name
        self.profileImageFile = profileImageFile
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


class ZombieBot_HumanPlayer(object):
    """This "bot" actually calls raw_input() and print() to let a human player play Zombie Dice against the other bots."""
    def __init__(self, name, profileImageFile=None):
        self.name = name
        self.profileImageFile = profileImageFile

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
                response = raw_input()
                if response.upper().startswith('S'):
                    return
            else:
                print('Shotgunned! Press Enter to continue.')
                raw_input()
                return


class ZombieBot_RollsUntilInTheLead(object):
    """This bot's strategy is to keep rolling for brains until they are in the lead (plus an optional number of points). This is a high risk strategy, because if the opponent gets an early lead then this bot will take greater and greater risks to get in the lead in a single turn.

    However, once in the lead, this bot will just use Zombie_MinNumShotgunsThenStops's strategy."""
    def __init__(self, name, plusLead=0, profileImageFile=None):
        self.name = name
        self.profileImageFile = profileImageFile
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


class ZombieBot_MonteCarlo(object):
    """This bot does several experimental dice rolls with the current cup, and re-rolls if the chance of 3 shotguns is less than "riskiness".
    The bot doesn't care how many brains it has rolled or what the relative scores are, it just looks at the chance of death for the next roll given the current cup."""
    def __init__(self, name, riskiness=50, numExperiments=100, profileImageFile=None):
        self.name = name
        self.profileImageFile = profileImageFile
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



if __name__ == '__main__':
    main()
