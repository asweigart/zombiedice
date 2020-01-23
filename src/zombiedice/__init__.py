"""
Zombie Dice is by Steve Jackson Games
http://zombiedice.sjgames.com/

Zombie Dice simulator by Al Sweigart (al@inventwithpython.com)
(I'm not affiliated with SJ Games. This is a hobby project.)


Note: A "turn" is a single player's turn. A "round" is every player having one turn.
Note: Since all variables are public in Python, it is trivial to have a bot that hacks the tournament code. Inspect the bot code before running it.

Instructions for making your own bot can be found here: http://inventwithpython.com/blog/2012/11/21/programming-ai-bots-for-zombie-dice/
"""

__version__ = '0.1.5'

EXCEPTIONS_LOSE_GAME = False # if True, errors in bot code won't stop the tournament code but instead result in the bot losing that game. Leave on False for debugging.
MAX_TURN_TIME = None # number of seconds bot can take per turn. Violating this results in the bot losing the game.

# TODO - I wish there was a way to pre-emptively cut off the bot's turn() call
# after MAX_TURN_TIME seconds have elapsed, but it seems like there's no
# simple way to share GAME_STATE state between the threads/processes.

import logging, random, sys, copy, platform, time, threading, webbrowser, os, re
from collections import namedtuple

# Import correct web server module
here = os.path.abspath(os.path.dirname(__file__))
os.chdir(here)

if platform.python_version().startswith('2.'):
    from SimpleHTTPServer import * # python 2 code
    from SocketServer import *
else:
    from http.server import HTTPServer, SimpleHTTPRequestHandler # python 3 code

logging.basicConfig(level=logging.WARNING, format='%(asctime)s - %(levelname)s - %(message)s')
logging.debug('Start of the Zombie Dice program.')

# constants, to keep a typo in a string from making weird errors
COLOR = 0
ICON = 1
RED = 'red'
GREEN = 'green'
YELLOW = 'yellow'
SHOTGUN = 'shotgun'
BRAINS = 'brains'
FOOTSTEPS = 'footsteps'

DieRoll = namedtuple('DieRoll', 'color icon')

TOURNAMENT_STATE = None

GAME_STATE = { # Just so that this dict is shareable for user's bot code, don't reassign this variable ever. (Poor design, but it's made for implementation simplicity for newbie programmers.)
    'CURRENT_ZOMBIE': None, # string of the zombie whose turn it is currently
    'CURRENT_CUP': None, # list of dice strings (i.e. 'red', 'yellow', 'green')
    'CURRENT_HAND': None, # list of dice being rolled (should always be length of three)
    'SHOTGUNS_ROLLED': None, # number of shotguns rolled this turn
    'BRAINS_ROLLED': None, # number of brains rolled this turn
    'ROLLED_BRAINS_DETAILS': None, # list of dice strings for each brain rolled, used in the rare event we run out of brain dice
    'TURN_START_TIME': None, # time since unix epoch that the current turn began
}

# Web GUI stuff:
WEB_SERVER_PORT = random.randint(49152, 61000)
SCORE_BAR_MAX_WIDTH = 350 # width in pixels in the web ui for the score bar
TOURNAMENT_RUNNING = False
WEB_GUI_NUM_GAMES = None
START_TIME = None


def assignUniqueZombieName(zombies):
    # Assign names to zombies missing names:
    for zombie in zombies:
        if not hasattr(zombie, 'name') or zombie.name is None:
            zombie.name = zombie.__class__.__name__
        elif not isinstance(zombie.name, str):
            zombie.name = str(zombie.name)

    # Assign names to zombies with duplicate names:
    for zombie in zombies:
        otherZombiesNames = [z.name for z in zombies]
        otherZombiesNames.remove(zombie.name)

        # Check if a duplicate name exists:
        if zombie.name in otherZombiesNames:
            i = 2
            while zombie.name + str(i) in otherZombiesNames:
                i += 1
            zombie.name = zombie.name + str(i)


def runWebGui(zombies, numGames):
    global BOTS, NUM_GAMES
    assignUniqueZombieName(zombies)
    BOTS = list(zombies)
    NUM_GAMES = numGames
    print('Zombie Dice Visualization is running. Open your browser to http://localhost:%s to view it.' % (WEB_SERVER_PORT))
    print('Press Ctrl-C to quit.')
    broswerOpenerThread = BrowserOpener()
    broswerOpenerThread.start()

    if platform.python_version().startswith('2.'):
        httpd = TCPServer(('localhost', WEB_SERVER_PORT), ZombieDiceHandler) # python 2 code
    else:
        httpd = HTTPServer(('localhost', WEB_SERVER_PORT), ZombieDiceHandler) # python 3 code
    try:
        httpd.serve_forever()
    except (KeyboardInterrupt, SystemExit):
        httpd.socket.close()
        sys.exit('Quitting...')


def runGame(zombies):
    """Runs a single game of zombie dice. zombies is a list of zombie dice bot objects."""
    global GAME_STATE
    assignUniqueZombieName(zombies)

    # create a new game state object
    playerScores = dict([(zombie.name, 0) for zombie in zombies])
    playerOrder = [zombie.name for zombie in zombies]
    logging.debug('Player order: ' + ', '.join(playerOrder))

    GAME_STATE['ORDER'] = playerOrder
    GAME_STATE['SCORES'] = playerScores
    GAME_STATE['ROUND'] = 0

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
        GAME_STATE['ROUND'] += 1
        logging.debug('ROUND #%s, scores: %s' % (GAME_STATE['ROUND'], GAME_STATE['SCORES']))

        for zombie in zombiesInPlay:
            if zombie in crashedBots:
                continue
            GAME_STATE['CURRENT_ZOMBIE'] = zombie.name
            logging.debug("%s's turn." % (GAME_STATE['CURRENT_ZOMBIE']))

            # set up for a new turn
            GAME_STATE['CURRENT_CUP'] = [RED] * 3 + [YELLOW] * 4 + [GREEN] * 6
            random.shuffle(GAME_STATE['CURRENT_CUP'])
            GAME_STATE['CURRENT_HAND'] = []
            GAME_STATE['SHOTGUNS_ROLLED'] = 0
            GAME_STATE['BRAINS_ROLLED'] = 0
            GAME_STATE['ROLLED_BRAINS_DETAILS'] = [] # list of dice colors, in case of "ran out of dice"

            # run the turn
            try:
                stateCopy = copy.deepcopy(GAME_STATE)
                GAME_STATE['TURN_START_TIME'] = time.time()
                zombie.turn(stateCopy) # (don't pass the original GAME_STATE)
            except Exception:
                crashedBots.append(zombie)
                if EXCEPTIONS_LOSE_GAME:
                    # if the bot code has an unhandled exception, it
                    # automatically loses this game
                    GAME_STATE['SCORES'][zombie.name] = -1
                    logging.warn('%s has lost the game due to a raised exception.' % (GAME_STATE['CURRENT_ZOMBIE']))
                else:
                    raise # crash the tournament program (good for debugging)
            if GAME_STATE['SHOTGUNS_ROLLED'] < 3:
                logging.debug('%s stops.' % (GAME_STATE['CURRENT_ZOMBIE']))
            else:
                logging.debug('%s is shotgunned. Lose all brains.' % (GAME_STATE['CURRENT_ZOMBIE']))

            # add brains to the score
            if GAME_STATE['SHOTGUNS_ROLLED'] < 3:
                GAME_STATE['SCORES'][zombie.name] += GAME_STATE['BRAINS_ROLLED']

            if GAME_STATE['SCORES'][zombie.name] >= 13:
                # once a player reaches 13 brains, it becomes the last round
                lastRound = True
                logging.debug('Last round. (%s has reached 13 brains.)' % (zombie.name))

        if tieBreakingRound:
            break # there is only one tie-breaking round, so after it end the game

        if lastRound:
            # only zombies tied with the highest score go on to the tie-breaking round (if there is one)
            zombiesInPlay = []
            highestScore = max(GAME_STATE['SCORES'].values()) # used for tie breaking round
            # zombiesInPlay will now only have the zombies tied with the highest score:
            zombiesInPlay = [zombie for zombie in zombies if GAME_STATE['SCORES'][zombie.name] == highestScore]

            if len(zombiesInPlay) == 1:
                # only one winner, so end the game
                break
            else:
                # multiple winners, so go on to the tie-breaking round.
                logging.debug('Tie breaking round with %s' % (', '.join([zombie.name for zombie in zombiesInPlay])))
                tieBreakingRound = True

    # call every zombie's endGame() method, if it has one
    for zombie in zombies:
        if 'endGame' in dir(zombie):
            zombie.endGame(copy.deepcopy(GAME_STATE))

    # rank bots by score
    ranking = sorted(GAME_STATE['SCORES'].items(), key=lambda x: x[1], reverse=True)
    highestScore = ranking[0][1]
    logging.debug('Final Scores: %s' % (', '.join(['%s %s' % (x[0], x[1]) for x in ranking])))     #(', '.join(['%s %s' % (name, score) for name, score in ranking.items()])))

    # winners are the bot(s) with the highest score
    winners = [x[0] for x in ranking if x[1] == highestScore]
    logging.debug('Winner%s: %s' % ((len(winners) != 1 and 's' or ''), ', '.join(winners)))

    return GAME_STATE


def runTournament(zombies, numGames):
    """A tournament is one or more games of Zombie Dice. The bots are re-used between games, so they can remember previous games.
    zombies is a list of zombie bot objects. numGames is an int of how many games to run."""
    global TOURNAMENT_STATE
    zombies = list(zombies)

    TOURNAMENT_STATE = {'GAME_NUMBER': 0,
                        'WINS': dict([(zombie.name, 0) for zombie in zombies]),
                        'TIES': dict([(zombie.name, 0) for zombie in zombies])}

    print('Tournament of %s games started...' % (numGames))

    for TOURNAMENT_STATE['GAME_NUMBER'] in range(numGames):
        random.shuffle(zombies) # randomize the order of the bots
        endState = runGame(zombies) # use the same zombie objects so they can remember previous games.

        if endState is None:
            sys.exit('Error when running game.')

        # Sort out the scores and find the winner.
        ranking = sorted(endState['SCORES'].items(), key=lambda x: x[1], reverse=True)
        highestScore = ranking[0][1]
        winners = [x[0] for x in ranking if x[1] == highestScore]
        if len(winners) == 1:
            TOURNAMENT_STATE['WINS'][ranking[0][0]] += 1
        elif len(winners) > 1:
            for score in endState['SCORES'].items():
                if score[1] == highestScore:
                    TOURNAMENT_STATE['TIES'][score[0]] += 1

    TOURNAMENT_STATE['GAME_NUMBER'] += 1 # increment to show all games are finished

    # print out the tournament results in neatly-formatted columns.
    print('Tournament results:')
    maxNameLength = max([len(zombie.name) for zombie in zombies])

    winsRanking = sorted(TOURNAMENT_STATE['WINS'].items(), key=lambda x: x[1], reverse=True)
    print('Wins:')
    for winnerName, winnerScore in winsRanking:
        print('    %s %s' % (winnerName.rjust(maxNameLength), str(winnerScore).rjust(len(str(numGames)))))

    tiesRanking = sorted(TOURNAMENT_STATE['TIES'].items(), key=lambda x: x[1], reverse=True)
    print('Ties:')
    for tiedName, tiedScore in tiesRanking:
        print('    %s %s' % (tiedName.rjust(maxNameLength), str(tiedScore).rjust(len(str(numGames)))))


def roll():
    """This global function is called by a zombie bot object to indicate that they wish to roll the dice.
    The state of the game and previous rolls are held in global variables."""
    global GAME_STATE

    if MAX_TURN_TIME is not None and (time.time() - GAME_STATE['TURN_START_TIME']) > MAX_TURN_TIME:
        # if the bot code has taken too long, it
        # automatically loses this game
        #GAME_STATE['SCORES'][zombie.name] = -1
        logging.warn('%s has lost the game due to taking too long.' % (GAME_STATE['CURRENT_ZOMBIE']))
        raise Exception('Exceeded max turn time.')

    # make sure zombie can actually roll
    if GAME_STATE['SHOTGUNS_ROLLED'] >= 3:
        return None

    logging.debug(GAME_STATE['CURRENT_ZOMBIE'] + ' rolls. (brains: %s, shotguns: %s)' % (GAME_STATE['BRAINS_ROLLED'], GAME_STATE['SHOTGUNS_ROLLED']))

    # "ran out of dice", so put the rolled brains back into the cup
    if 3 - len(GAME_STATE['CURRENT_HAND']) > len(GAME_STATE['CURRENT_CUP']):
        logging.debug('Out of dice! Putting rolled brains back into cup.')
        GAME_STATE['CURRENT_CUP'].extend(GAME_STATE['ROLLED_BRAINS_DETAILS'])
        GAME_STATE['ROLLED_BRAINS_DETAILS'] = []

    # add new dice to hand from cup until there are 3 dice in the hand
    while len(GAME_STATE['CURRENT_HAND']) < 3:
        newDie = random.choice(GAME_STATE['CURRENT_CUP'])
        logging.debug('%s die added to hand from cup.' % (newDie))
        GAME_STATE['CURRENT_CUP'].remove(newDie)
        GAME_STATE['CURRENT_HAND'].append(newDie)

    # roll the dice
    logging.debug('Hand is %s' % (', '.join(GAME_STATE['CURRENT_HAND'])))
    logging.debug('Cup has %s: %s' % (len(GAME_STATE['CURRENT_CUP']), ', '.join(GAME_STATE['CURRENT_CUP'])))
    diceRollResults = {SHOTGUN: 0, FOOTSTEPS: 0, BRAINS: 0, 'rolls': []}
    for die in GAME_STATE['CURRENT_HAND']:
        dieRollResult = rollDie(die)
        diceRollResults['rolls'].append(dieRollResult)
        diceRollResults[dieRollResult[ICON]] += 1 # increase the shotgun/brain/footstep count

    logging.debug('%s rolled %s' % (GAME_STATE['CURRENT_ZOMBIE'], diceRollResults))

    # count the shotguns and remove them from the hand
    for dieRollResult in diceRollResults['rolls']:
        if dieRollResult[ICON] == SHOTGUN:
            GAME_STATE['SHOTGUNS_ROLLED'] += 1
            logging.debug('Removing ' + dieRollResult[COLOR] + ' from hand for shotgun.')
            GAME_STATE['CURRENT_HAND'].remove(dieRollResult[COLOR])

    # count the brains and remove them from the hand
    for dieRollResult in diceRollResults['rolls']:
        if dieRollResult[ICON] == BRAINS:
            GAME_STATE['ROLLED_BRAINS_DETAILS'].append(dieRollResult[COLOR])
            GAME_STATE['BRAINS_ROLLED'] += 1
            logging.debug('Removing ' + dieRollResult[COLOR] + ' from hand for brains.')
            GAME_STATE['CURRENT_HAND'].remove(dieRollResult[COLOR])

    return diceRollResults


def rollDie(die):
    """Returns the result of a single die roll as a DieRoll namedtuple.
    Index 0 of the tuple is the color of the die (i.e. 'green', 'yellow', 'red').
    Index 1 is the icon: 'shotgun', 'footsteps', 'brains'."""
    roll = random.randint(1, 6)
    if die == RED:
        if roll in (1, 2, 3):
            return DieRoll(RED, SHOTGUN)
        elif roll in (4, 5):
            return DieRoll(RED, FOOTSTEPS)
        elif roll in (6,):
            return DieRoll(RED, BRAINS)
    elif die == YELLOW:
        if roll in (1, 2):
            return DieRoll(YELLOW, SHOTGUN)
        elif roll in (3, 4):
            return DieRoll(YELLOW, FOOTSTEPS)
        elif roll in (5, 6):
            return DieRoll(YELLOW, BRAINS)
    elif die == GREEN:
        if roll in (1,):
            return DieRoll(GREEN, SHOTGUN)
        elif roll in (2, 3):
            return DieRoll(GREEN, FOOTSTEPS)
        elif roll in (4, 5, 6):
            return DieRoll(GREEN, BRAINS)





# ========================================================================
# Web Gui Code:
# ========================================================================

class ZombieDiceHandler(SimpleHTTPRequestHandler):
    def log_message(self, format, *args):
        pass # comment out this entire method if you want to see the original HTTP log messages.

    def output(self, msg):
        self.send_header('Content-type','text/html')
        self.end_headers()
        self.wfile.write(msg.encode('ascii'))

    def moreoutput(self, msg):
        self.wfile.write(msg.encode('ascii'))


    def do_GET(self):
        global WEB_GUI_NUM_GAMES, START_TIME, TOURNAMENT_RUNNING
        self.send_response(200)
        reqPath = os.path.join(os.getcwd(), os.path.normpath(self.path[1:]))

        if os.path.isfile(reqPath):
            self.serveFile(reqPath)

        elif self.path == '/mainstatus':
            self.renderStatus()

        elif self.path == '/score':
            self.renderScoreJavascript()

        elif self.path.startswith('/start'):
            # "/start/<NUM GAMES>" is visited when the player clicks the "Begin Tournament" button. Check the path for the number of games to run.
            self.beginTournamentButtonPressed()

        elif self.path == '/':
            self.renderMainPage()


    def serveFile(self, reqPath):
        mimeTypeMapping = {'.js': 'application/x-javascript',
                           '.html': 'text/html',
                           '.css': 'text/css',
                           '.png': 'image/png',
                           '.gif': 'image/gif',
                           '.jpg': 'image/jpeg'}
        ending = reqPath[reqPath.rfind('.'):]
        if ending in mimeTypeMapping:
            self.send_header('Content-type',mimeTypeMapping[ending])
        else:
            self.send_header('Content-type','text/plain')
        self.end_headers()
        fp = open(reqPath, 'rb')
        self.wfile.write(fp.read())


    def renderStatus(self):
        if not TOURNAMENT_RUNNING:
            # display the "Begin Tournament" button.
            self.output("""
                <center>
                <div>
                  Run <input type="text" size="4" id="numGamesToRun" value="%s"> simulated games.<br />
                  <input type="button" value="Begin Tournament" onclick="startTournament(); return false;" />
                </div>
                </center>
                """ % (NUM_GAMES))
        else:
            # display the current status of the tournament simulation that is in progress
            self.output("""
                <center style="font-size:1.5em;">
                <span style="color: #FF0000">%s</span> / <span style="color: #FF0000">%s</span> Games Run</center>
                Estimate Time Remaining: <span style="color: #FF0000">%s</span>
                """ % (TOURNAMENT_STATE['GAME_NUMBER'], WEB_GUI_NUM_GAMES, estTimeRemaining(START_TIME, TOURNAMENT_STATE['GAME_NUMBER'], WEB_GUI_NUM_GAMES)))

            if TOURNAMENT_STATE['GAME_NUMBER'] == WEB_GUI_NUM_GAMES:
                # the javascript code checks for this text to know when to stop making repeated ajax requests for status updates
                self.moreoutput('<center>(Refresh page to run a new tournament.)</center>')


    # Returns JavaScript that will be evaluated by eval() in the web page (elegant solution, I know) to update the score table.
    def renderScoreJavascript(self):
        self.send_header('Content-type','text/html')
        self.end_headers()

        if TOURNAMENT_RUNNING and WEB_GUI_NUM_GAMES is not None and START_TIME is not None and TOURNAMENT_STATE['GAME_NUMBER'] is not None:
            for zombieName in [bot.name for bot in BOTS]:
                predictedMaxWidth = int(SCORE_BAR_MAX_WIDTH * max(int(len(BOTS) / 2.0), 1)) # We'll assume that the bots mostly evenly win games
                #predictedMaxWidth = SCORE_BAR_MAX_WIDTH # If the score bar keeps getting too long, just uncomment this line

                scoreBarLength = int((TOURNAMENT_STATE['WINS'][zombieName] / float(WEB_GUI_NUM_GAMES)) * predictedMaxWidth)
                scoreBarColor = getScoreBarColor(zombieName, TOURNAMENT_STATE['WINS'])
                wins = TOURNAMENT_STATE['WINS'][zombieName]
                ties = TOURNAMENT_STATE['TIES'][zombieName]

                escapedZombieName = zombieName.replace(' ', '_') # JavaScript code can't handle zombie name with spaces. TODO - probably can't handle other characters too.
                self.moreoutput("$('#%s_scorebar').css('width', '%spx'); " % (escapedZombieName, scoreBarLength))
                self.moreoutput("$('#%s_scorebar').css('background-color', '#%s'); " % (escapedZombieName, scoreBarColor))
                self.moreoutput("$('#%s_wins').text('%s'); " % (escapedZombieName, wins))
                self.moreoutput("$('#%s_ties').text('%s'); " % (escapedZombieName, ties))


    def beginTournamentButtonPressed(self):
        global WEB_GUI_NUM_GAMES, TOURNAMENT_RUNNING, START_TIME

        # path will be set to "/start/<NUM GAMES>"
        mo = re.search(r'(\d+)', self.path)
        if mo is not None:
            WEB_GUI_NUM_GAMES = int(mo.group(1))
        else:
            WEB_GUI_NUM_GAMES = 1000 # default to 1000
        START_TIME = time.time()

        # start the tournament simulation in a separate thread
        tournamentThread = TournamentThread()
        tournamentThread.start()
        TOURNAMENT_RUNNING = True # TOURNAMENT_RUNNING remains True after the tournament completes, until the "/" page is reloaded. Then it is set to False.
        self.output('') # return blank http reply so the browser doesn't try the request again.

    def renderMainPage(self):
        global WEB_GUI_NUM_GAMES, TOURNAMENT_RUNNING, START_TIME

        # when this page is loaded, if the previous tournmaent completed then restart the tournament:
        if WEB_GUI_NUM_GAMES is not None and TOURNAMENT_STATE['GAME_NUMBER'] == WEB_GUI_NUM_GAMES:
            TOURNAMENT_RUNNING = False # set to True after user clicks the "Begin Tournament" button in the web ui and the tournamentThread starts running.
            WEB_GUI_NUM_GAMES = None # TODO - make this a member variable instead of a global
            START_TIME = None # timestamp of when the tournament started, used for the "estimated time remaining"
            #TOURNAMENT_STATE['GAME_NUMBER'] = 0 #

        # create the table where each bot has a row for its score
        scoreTableHtml = []
        for zombieName in sorted([bot.name for bot in BOTS]):
            escapedZombieName = zombieName.replace(' ', '_') # JavaScript code can't handle zombie name with spaces. TODO - probably can't handle other characters too.
            scoreTableHtml.append('<tr><td>%s</td><td style="width: %spx;"><div id="%s_scorebar">&nbsp;</div></td><td><span id="%s_wins"></span></td><td><span id="%s_ties"></span></td></tr>' % (zombieName, SCORE_BAR_MAX_WIDTH, escapedZombieName, escapedZombieName, escapedZombieName))
        scoreTableHtml = ''.join(scoreTableHtml)

        # output the main page's html (with the score table)
        self.output("""<!DOCTYPE html>
            <html>
            <head><title>Zombie Dice Simulator</title>
            <script src="jquery-1.8.3.min.js"></script></head>
            <body>
            <img src="imgZombieCheerleader.jpg" id="cheerleader" style="position: absolute; left: -90px; top: 10px; opacity: 0.0" />
            <img src="imgTitle.png" id="title" style="position: absolute; left: 80px; top: -10px; opacity: 0.0" />
            <div style="position: absolute; left: 10px; top: 310px; font-size: 0.8em;"><center>By Al Sweigart<br /><a href="https://inventwithpython.com">https://inventwithpython.com</a><br /><a href="http://www.amazon.com/gp/product/B003IKMR0U/ref=as_li_qf_sp_asin_il_tl?ie=UTF8&camp=1789&creative=9325&creativeASIN=B003IKMR0U&linkCode=as2&tag=playwithpyth-20">Buy Zombie Dice Online</a><br /><a href="https://github.com/asweigart/zombiedice">Program your own Zombie Dice bot.</a></center></div>
            <!-- The mainstatusDiv shows the "Begin Tournament" button, and then the number of games played along with estimated time remaining. -->
            <div id="mainstatusDiv" style="position: absolute; left: 210px; top: 80px; width: 550px; background-color: #EEEEEE; opacity: 0.0"></div>

            <!-- The scoreDiv shows how many wins and ties each bot has. -->
            <div id="scoreDiv" style="position: absolute; left: 210px; top: 150px; width: 550px; background-color: #EEEEEE; opacity: 0.0">

            <table border="0">
            <tr><td colspan="2"></td><td>Wins</td><td>Ties</td>
            %s
            </table>
            </div>


            <script>
            var ajaxIntervalID = undefined;

            window.setTimeout(function() {
                // display the main divs part way through the other animations
                updateMainStatus();
                $('#mainstatusDiv').css('opacity', '1.0');
                $('#scoreDiv').css('opacity', '1.0');
            }, 500);
            $('#cheerleader').animate({opacity: '+=1.0', left: '+=100'}, 600, null)
            $('#title').animate({opacity: '+=1.0', top: '+=30'}, 1000, function() {
            })


            function updateMainStatus() {
                //console.log((new Date).getTime() / 1000);
                <!-- This ajax request contains the html for the mainstatusDiv -->
                $.ajax({
                  url: "mainstatus",
                  success: function(data){
                    $('#mainstatusDiv').html(data);
                    if (data.indexOf('(Refresh page to run a new tournament.)') != -1 && ajaxIntervalID !== undefined) {
                        clearInterval(ajaxIntervalID);
                    }
                  }
                });

                <!-- This ajax request returns JavaScript code to update the divs. -->
                $.ajax({
                  url: "score",
                  success: function(data) {
                    eval(data);
                  }
                });
            }


            function startTournament() {
              <!-- Start the Python code for the zombie dice tournament, and start the repeated ajax calls to update the mainstatusDiv and score table -->
              $.ajax({
                url: "start/" + $("#numGamesToRun").val()
              });
              ajaxIntervalID = setInterval('updateMainStatus()', 250);
            }

            </script>
            </body>
            </html>
            """ % (scoreTableHtml))


# The bot in the lead has a bright red #FF0000 bar, whereas a bot at 0 wins has a black #000000 bar. Depending on where in between the bot's score is, the appropriate black-to-red color is returned. Returns a string like 'FF0000', without the leading '#' character.
def getScoreBarColor(zombieName, winsState):
    maxScore = max(winsState.values())
    myScore = winsState[zombieName]

    if maxScore == 0:
        return '000000' # return black color to prevent zero division error

    redness = int((myScore / float(maxScore)) * 255)
    redness = hex(redness)[2:].upper()
    if len(redness) == 1:
        redness = '0' + redness
    return redness + '0000' # return the HTML RGB color for the bar


# Calculates amount of time remaining for this tournament, given how long it has taken to run the previous games.
def estTimeRemaining(startTime, currentGame, totalGames):
    lapsed = time.time() - startTime
    if currentGame == 0:
        return 'Unknown' # prevent zero division
    totalEstTime = lapsed * (totalGames / float(currentGame))
    return prettyTime(int(totalEstTime - lapsed))


# Takes parameter that is a number of seconds and returns a pretty string with the time in weeks, days, hours, minutes, and seconds.
def prettyTime(t): # t is in seconds
    wk = day = hr = min = sec = 0
    if t > 604800:
        wk = t // 604800
        t = t % 604800
    if t > 86400:
        day = t // 86400
        t = t % 86400
    if t > 3600:
        hr = t // 3600
        t = t % 3600
    if t > 60:
        min = t // 60
        t = t % 60
    sec = t

    t_str = []
    if wk > 0:
        t_str.append('%s wk' % (wk))
    if wk > 0 or day > 0:
        t_str.append('%s day' % (day))
    if wk > 0 or day > 0 or hr > 0:
        t_str.append('%s hr' % (hr))
    if wk > 0 or day > 0 or hr > 0 or min > 0:
        t_str.append('%s min' % (min))
    t_str.append('%s sec' % (sec))

    return ' '.join(t_str[:2])


# Runs the zombie dice tournament in a separate thread.
class TournamentThread(threading.Thread):
    def run(self):
        runTournament(BOTS, WEB_GUI_NUM_GAMES)


class BrowserOpener(threading.Thread):
    def run(self):
        time.sleep(0.4) # give the server a bit of time to start
        webbrowser.open('http://localhost:%s' % (WEB_SERVER_PORT))


from . import examples

def demo():
    zombies = (
        examples.RandomCoinFlipZombie(name='Random'),
        examples.MonteCarloZombie(name='Monte Carlo', riskiness=40, numExperiments=20),
        examples.RollsUntilInTheLeadZombie(name='Until Leading'),
        examples.MinNumShotgunsThenStopsZombie(name='Stop at 2 Shotguns', minShotguns=2),
        examples.MinNumShotgunsThenStopsZombie(name='Stop at 1 Shotgun', minShotguns=1),
        examples.AlwaysRollsTwiceZombie(name='Roll Twice'),
        # Add any other zombie players here.
    )

    # Uncomment one of the following lines to run in CLI or Web GUI mode:
    #zombiedice.runTournament(zombies=zombies, numGames=100)
    runWebGui(zombies=zombies, numGames=1000)