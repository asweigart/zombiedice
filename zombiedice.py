import copy, random, logging, sys
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# constants
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

    # game state set up
    playerScores = dict([(zombie.name, 0) for zombie in zombies])
    playerOrder = [zombie.name for zombie in zombies]
    logging.debug('Player order: ' + ', '.join(playerOrder))

    # validate zombie objects
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

    # create a new game state object
    gameState = {'order': playerOrder,
                 'scores': playerScores,
                 'round': 0}

    # call every zombie's newGame() method
    for zombie in zombies:
        if 'newGame' in dir(zombie):
            zombie.newGame()

    # set up for a new game
    lastRound = False
    tieBreakingRound = False
    highestScore = 0 # used for tie breaking round
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
            rolledBrains = []

            # run the turn (don't pass the original gameState)
            zombie.turn(copy.deepcopy(gameState))

            # count the scores
            if numShotgunsRolled < 3:
                gameState[SCORES][zombie.name] += numBrainsRolled

            if gameState[SCORES][zombie.name] >= 13:
                lastRound = True
                logging.debug('LAST ROUND')

        if tieBreakingRound:
            break

        if lastRound:
            # only zombies tied with the highest score play in the tie breaking round (if there is one)
            zombiesInPlay = []
            highestScore = 0
            for zombieScore in gameState[SCORES].values(): # get highest score
                if zombieScore > highestScore:
                    highestScore = zombieScore
            for zombie in zombies:
                if gameState[SCORES][zombie.name] == highestScore:
                    zombiesInPlay.append(zombie)

            # break out of the game loop if there is no tie
            if len(zombiesInPlay) == 1:
                break
            else:
                logging.debug('TIE BREAKING ROUND')
                tieBreakingRound = True

    # call every zombie's endGame() method
    for zombie in zombies:
        if 'endGame' in dir(zombie):
            zombie.endGame(copy.deepcopy(gameState))

    ranking = sorted(gameState[SCORES].items(), key=lambda x: x[1], reverse=True)
    highestScore = ranking[0][1]
    logging.debug('Ranking: %s' % (ranking))

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

    print('Tournament results:')
    maxNameLength = max([len(zombie.name) for zombie in zombies])

    winsRanking = sorted(tournamentState['wins'].items(), key=lambda x: x[1], reverse=True)
    print('Wins:')
    for winnerName, winnerScore in winsRanking:
        print('    %s %s' % (winnerName.rjust(maxNameLength), str(winnerScore).rjust(len(str(numGames)))))

    #tiesRanking = sorted(tournamentState['ties'].items(), key=lambda x: x[1], reverse=True)
    #print('Ties:')
    #for tiedName, tiedScore in tiesRanking:
    #    print('    %s %s' % (tiedName.rjust(maxNameLength), str(tiedScore).rjust(len(str(numGames)))))

def runOneOnOne(zombies, numGames):
    pass

def roll():
    global currentZombie, currentCup, currentHand, numShotgunsRolled, numBrainsRolled, rolledBrains

    # make sure zombie can actually roll
    if numShotgunsRolled >= 3:
        return []

    logging.debug(currentZombie + ' rolls. (brains: %s, shotguns: %s)' % (numBrainsRolled, numShotgunsRolled))

    # if we've run out of dice, put the rolled brain back into the cup
    if 3 - len(currentHand) > len(currentCup):
        logging.debug('Out of dice! Putting brains back into cup.')
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



# ==== GENERIC ZOMBIE BOTS =========================
class Zombie_MinNumBrainsThenStops(object):
    def __init__(self, name, minBrains):
        self.name = name
        self.minBrains = minBrains

    def turn(self, gameState):
        brains = 0
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
        shotguns = 0
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
        shotguns = 0
        brains = 0
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
    def __init__(self, name, plusLead=0):
        self.name = name
        self.plusLead = plusLead

    def turn(self, gameState):
        results = roll() # roll at least once
        brains = len([True for result in results if result[ICON] == BRAINS])
        myScore = gameState[SCORES][currentZombie]

        highestScoreThatIsntMine = 0
        for zombieName, zombieScore in gameState[SCORES].items():
            if zombieName != currentZombie and zombieScore > highestScoreThatIsntMine:
                highestScoreThatIsntMine = zombieScore

        while results != [] and myScore + brains <= highestScoreThatIsntMine + self.plusLead:
            results = roll()
            brains += len([True for result in results if result[ICON] == BRAINS])


class Zombie_MinGreenBrainsThenStops(object):
    def __init__(self, name, minGreenBrains, minAllBrains):
        self.name = name
        self.minGreenBrains = minGreenBrains
        self.minAllBrains = minAllBrains

    def turn(self, gameState):
        greenBrains = 0
        allBrains = 0
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
    def __init__(self, name):
        self.name = name

    def turn(self, gameState):
        roll() # first roll

        while random.randint(0, 1) == 0:
            roll()

class Zombie_HumanPlayer(object):
    def __init__(self, name):
        self.name = name

    def turn(self, gameState):
        brains = ''
        shotguns = ''
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

# ==== RUN TOURNAMENT ======================
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
zombies.append(Zombie_MinNumBrainsShotgunsThenStops('Min9b2s', 9, 2))
#zombies.append(Zombie_MinNumBrainsShotgunsThenStops('Min10b2s', 10, 2))
#zombies.append(Zombie_MinNumBrainsShotgunsThenStops('Min11b2s', 11, 2))
#zombies.append(Zombie_MinNumBrainsShotgunsThenStops('Min99b2s', 99, 2))
#zombies.append(Zombie_RollsUntilInTheLead('RollsUntilLead'))
#zombies.append(Zombie_RollsUntilInTheLead('RollsUntilLead+1', 1))
#zombies.append(Zombie_RandomCoinFlip('RandomCoinFlip'))
#zombies.append(Zombie_HumanPlayer('Al'))
runTournament(zombies, 1000)
