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


Zombie Dice simulator


Note: A "turn" is a single player's turn. A "round" is every player having one turn.

Note: Since all variables are public in Python, it is trivial to have a bot that hacks the tournament code. Inspect the bot code before running it.
"""


import copy, random, logging, sys
logging.basicConfig(level=logging.ERROR, format='%(asctime)s - %(levelname)s - %(message)s')

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


def runGame(zombies):
    global currentZombie, currentCup, currentHand, numShotgunsRolled, numBrainsRolled, rolledBrains

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
        for zombie in zombiesInPlay:
            currentZombie = zombie.name
            logging.debug('NEW TURN: %s' % (currentZombie))

            # set up for a new turn
            currentCup = [RED] * 3 + [YELLOW] * 4 + [GREEN] * 6
            random.shuffle(currentCup)
            currentHand = []
            numShotgunsRolled = 0
            numBrainsRolled = 0
            rolledBrains = [] # list of dice colors, in case of "ran out of dice"

            # run the turn (don't pass the original gameState)
            zombie.turn(copy.deepcopy(gameState))

            # add brains to the score
            if numShotgunsRolled < 3:
                gameState[SCORES][zombie.name] += numBrainsRolled

            if gameState[SCORES][zombie.name] >= 13:
                # once a player reaches 13 brains, it becomes the last round
                lastRound = True
                logging.debug('LAST ROUND')

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
                tieBreakingRound = True

    # call every zombie's endGame() method, if it has one
    for zombie in zombies:
        if 'endGame' in dir(zombie):
            zombie.endGame(copy.deepcopy(gameState))

    # rank bots by score
    ranking = sorted(gameState[SCORES].items(), key=lambda x: x[1], reverse=True)
    highestScore = ranking[0][1]
    logging.debug('Ranking: %s' % (ranking))

    # winners are the bot(s) with the highest score
    winners = [x[0] for x in ranking if x[1] == highestScore]
    logging.debug('Winner(s): %s' % (winners))

    return gameState

def runTournament(zombies, numGames):
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
    global currentZombie, currentCup, currentHand, numShotgunsRolled, numBrainsRolled, rolledBrains

    # make sure zombie can actually roll
    if numShotgunsRolled >= 3:
        return []

    logging.debug(currentZombie + ' rolls. (brains: %s, shotguns: %s)' % (numBrainsRolled, numShotgunsRolled))

    # "ran out of dice", so put the rolled brains back into the cup
    if 3 - len(currentHand) > len(currentCup):
        logging.debug('Out of dice! Putting rolled brains back into cup.')
        currentCup.extend(rolledBrains)
        rolledBrains = []

    # add new dice to hand from cup until there are 3 dice in the hand
    while len(currentHand) < 3:
        newDie = random.choice(currentCup)
        logging.debug('%s die added to hand from cup.' % (newDie))
        currentCup.remove(newDie)
        currentHand.append(newDie)

    # roll the dice
    logging.debug('Hand is %s' % (', '.join(currentHand)))
    logging.debug('Cup has %s: %s' % (len(currentCup), ', '.join(currentCup)))
    results = []
    for die in currentHand:
        results.append(rollDie(die))
    resultStr = ['%s_%s' % (result[COLOR][0].upper(), result[ICON][:2]) for result in results]
    logging.debug('%s rolled %s' % (currentZombie, ', '.join(resultStr)))

    # count the shotguns and remove them from the hand
    for result in results:
        if result[ICON] == SHOTGUN:
            numShotgunsRolled += 1
            logging.debug('Removing ' + result[COLOR] + ' from hand for shotgun.')
            currentHand.remove(result[COLOR])

    # count the brains and remove them from the hand
    for result in results:
        if result[ICON] == BRAINS:
            rolledBrains.append(result[COLOR])
            numBrainsRolled += 1
            logging.debug('Removing ' + result[COLOR] + ' from hand for brains.')
            currentHand.remove(result[COLOR])

    return results


def rollDie(die):
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
class Zombie_MinNumBrainsThenStops(object):
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

class Zombie_MinNumShotgunsThenStops(object):
    def __init__(self, name, minShotguns):
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


class Zombie_MinNumBrainsShotgunsThenStops(object):
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

class Zombie_RollsUntilInTheLead(object):
    """This bot's strategy is to keep rolling for brains until they are in the lead (plus an optional number of points). This is a high risk strategy, because if the opponent gets an early lead then this bot will take greater and greater risks to get in the lead in a single turn.

    However, once in the lead, this bot will just use Zombie_MinNumShotgunsThenStops's strategy."""
    def __init__(self, name, plusLead=0):
        self.name = name
        self.plusLead = plusLead
        self.altZombieStrategy = Zombie_MinNumShotgunsThenStops(name + '_alt', 2)

    def turn(self, gameState):
        highestScoreThatIsntMine = max([zombieScore for zombieName, zombieScore in gameState[SCORES].items() if zombieName != currentZombie])

        if highestScoreThatIsntMine + self.plusLead >= gameState[SCORES][currentZombie]:
            results = roll() # roll at least once
            brains = len([True for result in results if result[ICON] == BRAINS])
            myScore = gameState[SCORES][currentZombie]

            while results != [] and myScore + brains <= highestScoreThatIsntMine + self.plusLead:
                results = roll()
                brains += len([True for result in results if result[ICON] == BRAINS])
        else:
            # already in the lead, so just use altZombieStrategy's turn()
            self.altZombieStrategy.turn(gameState)


class Zombie_MinGreenBrainsThenStops(object):
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


class Zombie_RandomCoinFlip(object):
    """After the first roll, this bot always has a fifty-fifty chance of deciding to roll again or stopping."""
    def __init__(self, name):
        self.name = name

    def turn(self, gameState):
        results = roll() # first roll

        while random.randint(0, 1) == 0 and results != []:
            results = roll()

class Zombie_HumanPlayer(object):
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

# ==== RUN TOURNAMENT CODE ======================
def main():
    zombies = []
    #zombies.append(Zombie_MinNumBrainsThenStops('Min2brains', 2))
    #zombies.append(Zombie_MinNumBrainsThenStops('Min3brains', 3))
    #zombies.append(Zombie_MinNumShotgunsThenStops('Min1shotguns', 1))
    zombies.append(Zombie_MinNumShotgunsThenStops('Min2shotguns', 2))
    #zombies.append(Zombie_MinGreenBrainsThenStops('Min3brains1green', 1, 3))
    #zombies.append(Zombie_MinNumBrainsShotgunsThenStops('Min3b2s', 3, 2))
    #zombies.append(Zombie_MinNumBrainsShotgunsThenStops('Min4b2s', 4, 2))
    #zombies.append(Zombie_MinNumBrainsShotgunsThenStops('Min5b2s', 5, 2))
    #zombies.append(Zombie_MinNumBrainsShotgunsThenStops('Min6b2s', 6, 2))
    #zombies.append(Zombie_MinNumBrainsShotgunsThenStops('Min7b2s', 7, 2))
    #zombies.append(Zombie_MinNumBrainsShotgunsThenStops('Min8b2s', 8, 2))
    #zombies.append(Zombie_MinNumBrainsShotgunsThenStops('Min9b2s', 9, 2))
    #zombies.append(Zombie_MinNumBrainsShotgunsThenStops('Min10b2s', 10, 2))
    #zombies.append(Zombie_MinNumBrainsShotgunsThenStops('Min11b2s', 11, 2))
    #zombies.append(Zombie_MinNumBrainsShotgunsThenStops('Min99b2s', 99, 2))
    zombies.append(Zombie_RollsUntilInTheLead('RollsUntilLead'))
    #zombies.append(Zombie_RollsUntilInTheLead('RollsUntilLead+1', 1))
    zombies.append(Zombie_RandomCoinFlip('RandomCoinFlip'))
    #zombies.append(Zombie_HumanPlayer('Al'))

    runTournament(zombies, 1000)

if __name__ == '__main__':
    main()