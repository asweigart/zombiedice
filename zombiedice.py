"""
Zombie Dice is by Steve Jackson Games
http://zombiedice.sjgames.com/


Zombie Dice simulator by Al Sweigart (al@inventwithpython.com)
(I'm not affiliated with SJ Games. This is a hobby project.)

Note: A "turn" is a single player's turn. A "round" is every player having one turn.
Note: Since all variables are public in Python, it is trivial to have a bot that hacks the tournament code. Inspect the bot code before running it.

Instructions for making your own bot can be found here: http://inventwithpython.com/blog/2012/11/21/how-to-make-ai-bots-for-zombie-dice
"""


VERBOSE = False # if True, program outputs the actions that happen during the game
EXCEPTIONS_LOSE_GAME = False  # if True, errors in bot code won't stop the tournament code but instead result in the bot losing that game. Leave on False for debugging.
MAX_TURN_TIME = None # number of seconds bot can take per turn. Violating this results in the bot losing the game.



import logging, random, sys, copy, platform
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

TOURNAMENT_STATE = None

CURRENT_GAME_STATE = { # Just so that this dict is shareable for user's bot code, don't reassign this variable ever. (Poor design, but it's made for implementation simplicity for newbie programmers.)
    'CURRENT_ZOMBIE': None, # string of the zombie whose turn it is currently
    'CURRENT_CUP': None, # list of dice strings (i.e. 'red', 'yellow', 'green')
    'CURRENT_HAND': None, # list of dice being rolled (should always be length of three)
    'NUM_SHOTGUNS_ROLLED': None, # number of shotguns rolled this turn
    'NUM_BRAINS_ROLLED': None, # number of brains rolled this turn
    'ROLLED_BRAINS': None, # list of dice strings for each brain rolled, used in the rare event we run out of brain dice
}


def main():
    import zombieBotExamples

    # pass runTournament() a list of bot objects
    bots = [zombieBotExamples.MonteCarloZombie('MonteCarlo', 40, 100),
            zombieBotExamples.MinNumShotgunsThenStopsZombie('Min2ShotgunsBot', 2),
            zombieBotExamples.RandomCoinFlipZombie('RandomBot'),
            ]
    runTournament(bots, 100)


def runGame(zombies):
    """Runs a single game of zombie dice. zombies is a list of zombie dice bot objects."""
    global CURRENT_GAME_STATE

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
    crashedBots = [] # list of bots that had exceptions
    while True: # game loop
        gameState['round'] += 1
        logging.debug('ROUND #%s, scores: %s' % (gameState['round'], gameState[SCORES]))
        if VERBOSE: print('Round #%s' % (gameState['round']))
        for zombie in zombiesInPlay:
            if zombie in crashedBots:
                continue
            CURRENT_GAME_STATE['CURRENT_ZOMBIE'] = zombie.name
            logging.debug('NEW TURN: %s' % (CURRENT_GAME_STATE['CURRENT_ZOMBIE']))
            if VERBOSE: print("%s's turn." % (CURRENT_GAME_STATE['CURRENT_ZOMBIE']))

            # set up for a new turn
            CURRENT_GAME_STATE['CURRENT_CUP'] = [RED] * 3 + [YELLOW] * 4 + [GREEN] * 6
            random.shuffle(CURRENT_GAME_STATE['CURRENT_CUP'])
            CURRENT_GAME_STATE['CURRENT_HAND'] = []
            CURRENT_GAME_STATE['NUM_SHOTGUNS_ROLLED'] = 0
            CURRENT_GAME_STATE['NUM_BRAINS_ROLLED'] = 0
            CURRENT_GAME_STATE['ROLLED_BRAINS'] = [] # list of dice colors, in case of "ran out of dice"

            # run the turn
            try:
                zombie.turn(copy.deepcopy(gameState)) # (don't pass the original gameState)
            except Exception:
                crashedBots.append(zombie)
                if EXCEPTIONS_LOSE_GAME:
                    # if the bot code has an unhandled exception, it
                    # automatically loses this game
                    gameState[SCORES][zombie.name] = -1
                    if VERBOSE:
                        print('%s has lost the game due to a raised exception.' % (CURRENT_GAME_STATE['CURRENT_ZOMBIE']))
                else:
                    raise # crash the tournament program (good for debugging)
            if VERBOSE and CURRENT_GAME_STATE['NUM_SHOTGUNS_ROLLED'] < 3: print('%s stops.' % (CURRENT_GAME_STATE['CURRENT_ZOMBIE']))
            if VERBOSE and CURRENT_GAME_STATE['NUM_SHOTGUNS_ROLLED'] >= 3: print('%s is shotgunned. Lose all brains.' % (CURRENT_GAME_STATE['CURRENT_ZOMBIE']))

            # add brains to the score
            if CURRENT_GAME_STATE['NUM_SHOTGUNS_ROLLED'] < 3:
                gameState[SCORES][zombie.name] += CURRENT_GAME_STATE['NUM_BRAINS_ROLLED']

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
    global CURRENT_GAME_STATE

    # make sure zombie can actually roll
    if CURRENT_GAME_STATE['NUM_SHOTGUNS_ROLLED'] >= 3:
        return []

    logging.debug(CURRENT_GAME_STATE['CURRENT_ZOMBIE'] + ' rolls. (brains: %s, shotguns: %s)' % (CURRENT_GAME_STATE['NUM_BRAINS_ROLLED'], CURRENT_GAME_STATE['NUM_SHOTGUNS_ROLLED']))
    if VERBOSE: print('%s rolls. (brains: %s, shotguns: %s)' % (CURRENT_GAME_STATE['CURRENT_ZOMBIE'], CURRENT_GAME_STATE['NUM_BRAINS_ROLLED'], CURRENT_GAME_STATE['NUM_SHOTGUNS_ROLLED']))

    # "ran out of dice", so put the rolled brains back into the cup
    if 3 - len(CURRENT_GAME_STATE['CURRENT_HAND']) > len(CURRENT_GAME_STATE['CURRENT_CUP']):
        logging.debug('Out of dice! Putting rolled brains back into cup.')
        CURRENT_GAME_STATE['CURRENT_CUP'].extend(CURRENT_GAME_STATE['ROLLED_BRAINS'])
        CURRENT_GAME_STATE['ROLLED_BRAINS'] = []

    # add new dice to hand from cup until there are 3 dice in the hand
    while len(CURRENT_GAME_STATE['CURRENT_HAND']) < 3:
        newDie = random.choice(CURRENT_GAME_STATE['CURRENT_CUP'])
        logging.debug('%s die added to hand from cup.' % (newDie))
        CURRENT_GAME_STATE['CURRENT_CUP'].remove(newDie)
        CURRENT_GAME_STATE['CURRENT_HAND'].append(newDie)

    # roll the dice
    logging.debug('Hand is %s' % (', '.join(CURRENT_GAME_STATE['CURRENT_HAND'])))
    logging.debug('Cup has %s: %s' % (len(CURRENT_GAME_STATE['CURRENT_CUP']), ', '.join(CURRENT_GAME_STATE['CURRENT_CUP'])))
    results = []
    for die in CURRENT_GAME_STATE['CURRENT_HAND']:
        results.append(rollDie(die))
    resultStr = ['%s_%s' % (result[COLOR][0].upper(), result[ICON][:2]) for result in results]
    logging.debug('%s rolled %s' % (CURRENT_GAME_STATE['CURRENT_ZOMBIE'], ', '.join(resultStr)))
    if VERBOSE: print(', '.join(['%s %s' % (result[COLOR].title(), result[ICON]) for result in results]))

    # count the shotguns and remove them from the hand
    for result in results:
        if result[ICON] == SHOTGUN:
            CURRENT_GAME_STATE['NUM_SHOTGUNS_ROLLED'] += 1
            logging.debug('Removing ' + result[COLOR] + ' from hand for shotgun.')
            CURRENT_GAME_STATE['CURRENT_HAND'].remove(result[COLOR])

    # count the brains and remove them from the hand
    for result in results:
        if result[ICON] == BRAINS:
            CURRENT_GAME_STATE['ROLLED_BRAINS'].append(result[COLOR])
            CURRENT_GAME_STATE['NUM_BRAINS_ROLLED'] += 1
            logging.debug('Removing ' + result[COLOR] + ' from hand for brains.')
            CURRENT_GAME_STATE['CURRENT_HAND'].remove(result[COLOR])

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






if __name__ == '__main__':
    main()