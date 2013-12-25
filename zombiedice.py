"""
Zombie Dice is by Steve Jackson Games
http://zombiedice.sjgames.com/

Zombie Dice simulator by Al Sweigart (al@inventwithpython.com)
(I'm not affiliated with SJ Games. This is a hobby project.)

==== TOURNAMENT SETUP INSTRUCTIONS =============================================
In the main() function, enter the .py file that contains your zombie bots in the
exec() call.

Then adjust the "bots" list to create Zombie Bot objects in it.

Then call runTournament(), passing the numbr of games the tournament should play.

To run the web gui for this simulator, run "python zombiedice.py web"
================================================================================


Note: A "turn" is a single player's turn. A "round" is every player having one turn.
Note: Since all variables are public in Python, it is trivial to have a bot that hacks the tournament code. Inspect the bot code before running it.

Instructions for making your own bot can be found here: http://inventwithpython.com/blog/2012/11/21/how-to-make-ai-bots-for-zombie-dice
"""

# Load a file with zombie bots
exec(open('zombieBotExamples.py').read())

# pass runTournament() a list of bot objects
BOTS = [MonteCarloZombie('MonteCarlo', 40, 20),
        MinNumShotgunsThenStopsZombie('Min2Shotguns', 2),
        #MinNumShotgunsThenStopsZombie('Min2Shotguns2', 2),
        RandomCoinFlipZombie('Random'),
        #CrashZombie('Crash'),
        SlowZombie('Slow'),
        ]

NUM_GAMES = 100 # the number of games to run in this tournament. Default value for the web gui version.



VERBOSE = False # if True, program outputs the actions that happen during the game
EXCEPTIONS_LOSE_GAME = True  # if True, errors in bot code won't stop the tournament code but instead result in the bot losing that game. Leave on False for debugging.
MAX_TURN_TIME = 1 # number of seconds bot can take per turn. Violating this results in the bot losing the game.

# TODO - I wish there was a way to pre-emptively cut off the bot's turn() call
# after MAX_TURN_TIME seconds have elapsed, but it seems like there's no
# simple way to share GAME_STATE state between the threads/processes.

import logging, random, sys, copy, platform, time, threading, webbrowser, os, re

# Import correct web server module
if platform.python_version().startswith('2.'):
    from SimpleHTTPServer import * # python 2 code
    from SocketServer import *
else:
    from http.server import HTTPServer, SimpleHTTPRequestHandler # python 3 code

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


def main():
    runTournament(BOTS, NUM_GAMES)


def runWebGui():
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
        if VERBOSE: print('Round #%s' % (GAME_STATE['ROUND']))
        for zombie in zombiesInPlay:
            if zombie in crashedBots:
                continue
            GAME_STATE['CURRENT_ZOMBIE'] = zombie.name
            logging.debug('NEW TURN: %s' % (GAME_STATE['CURRENT_ZOMBIE']))
            if VERBOSE: print("%s's turn." % (GAME_STATE['CURRENT_ZOMBIE']))

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
                    if VERBOSE:
                        print('%s has lost the game due to a raised exception.' % (GAME_STATE['CURRENT_ZOMBIE']))
                else:
                    raise # crash the tournament program (good for debugging)
            if VERBOSE and GAME_STATE['SHOTGUNS_ROLLED'] < 3: print('%s stops.' % (GAME_STATE['CURRENT_ZOMBIE']))
            if VERBOSE and GAME_STATE['SHOTGUNS_ROLLED'] >= 3: print('%s is shotgunned. Lose all brains.' % (GAME_STATE['CURRENT_ZOMBIE']))

            # add brains to the score
            if GAME_STATE['SHOTGUNS_ROLLED'] < 3:
                GAME_STATE['SCORES'][zombie.name] += GAME_STATE['BRAINS_ROLLED']

            if GAME_STATE['SCORES'][zombie.name] >= 13:
                # once a player reaches 13 brains, it becomes the last round
                lastRound = True
                logging.debug('LAST ROUND')
                if VERBOSE: print('%s has reached 13 brains.' % (zombie.name))

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
                logging.debug('TIE BREAKING ROUND')
                if VERBOSE: print('Tie breaking round with %s' % (', '.join([zombie.name for zombie in zombiesInPlay])))
                tieBreakingRound = True

    # call every zombie's endGame() method, if it has one
    for zombie in zombies:
        if 'endGame' in dir(zombie):
            zombie.endGame(copy.deepcopy(GAME_STATE))

    # rank bots by score
    ranking = sorted(GAME_STATE['SCORES'].items(), key=lambda x: x[1], reverse=True)
    highestScore = ranking[0][1]
    logging.debug('Ranking: %s' % (ranking))
    if VERBOSE: print('Final Scores: %s' % (', '.join(['%s %s' % (x[0], x[1]) for x in ranking])))     #(', '.join(['%s %s' % (name, score) for name, score in ranking.items()])))

    # winners are the bot(s) with the highest score
    winners = [x[0] for x in ranking if x[1] == highestScore]
    logging.debug('Winner(s): %s' % (winners))
    if VERBOSE: print('Winner%s: %s' % ((len(winners) != 1 and 's' or ''), ', '.join(winners)))

    return GAME_STATE


def runTournament(zombies, numGames):
    """A tournament is one or more games of Zombie Dice. The bots are re-used between games, so they can remember previous games.
    zombies is a list of zombie bot objects. numGames is an int of how many games to run."""
    global TOURNAMENT_STATE
    TOURNAMENT_STATE = {'GAME_NUMBER': 0,
                        'WINS': dict([(zombie.name, 0) for zombie in zombies]),
                        'TIES': dict([(zombie.name, 0) for zombie in zombies])}

    print('Tournament of %s games started...' % (numGames))

    for TOURNAMENT_STATE['GAME_NUMBER'] in range(numGames):
        random.shuffle(zombies) # randomize the order
        endState = runGame(zombies) # use the same zombie objects so they can remember previous games.

        if endState is None:
            sys.exit('Error when running game.')

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
        if VERBOSE:
            print('%s has lost the game due to taking too long.' % (GAME_STATE['CURRENT_ZOMBIE']))
        raise Exception('Exceeded max turn time.')

    # make sure zombie can actually roll
    if GAME_STATE['SHOTGUNS_ROLLED'] >= 3:
        return []

    logging.debug(GAME_STATE['CURRENT_ZOMBIE'] + ' rolls. (brains: %s, shotguns: %s)' % (GAME_STATE['BRAINS_ROLLED'], GAME_STATE['SHOTGUNS_ROLLED']))
    if VERBOSE: print('%s rolls. (brains: %s, shotguns: %s)' % (GAME_STATE['CURRENT_ZOMBIE'], GAME_STATE['BRAINS_ROLLED'], GAME_STATE['SHOTGUNS_ROLLED']))

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
    results = []
    for die in GAME_STATE['CURRENT_HAND']:
        results.append(rollDie(die))
    resultStr = ['%s_%s' % (result[COLOR][0].upper(), result[ICON][:2]) for result in results]
    logging.debug('%s rolled %s' % (GAME_STATE['CURRENT_ZOMBIE'], ', '.join(resultStr)))
    if VERBOSE: print(', '.join(['%s %s' % (result[COLOR].title(), result[ICON]) for result in results]))

    # count the shotguns and remove them from the hand
    for result in results:
        if result[ICON] == SHOTGUN:
            GAME_STATE['SHOTGUNS_ROLLED'] += 1
            logging.debug('Removing ' + result[COLOR] + ' from hand for shotgun.')
            GAME_STATE['CURRENT_HAND'].remove(result[COLOR])

    # count the brains and remove them from the hand
    for result in results:
        if result[ICON] == BRAINS:
            GAME_STATE['ROLLED_BRAINS_DETAILS'].append(result[COLOR])
            GAME_STATE['BRAINS_ROLLED'] += 1
            logging.debug('Removing ' + result[COLOR] + ' from hand for brains.')
            GAME_STATE['CURRENT_HAND'].remove(result[COLOR])

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
                <form onsubmit="startTournament(); return false;" >
                  Run <input type="text" size="4" id="numGamesToRun" value="%s"> simulated games.<br />
                  <input type="submit" value="Begin Tournament" />
                </form>
                </center>
                """ % (NUM_GAMES))
        else:
            # display the current status of the tournament simulation that is in progress
            self.output("""
                <center style="font-size:1.5em;">
                <span style="color: #00FF00">%s</span> / <span style="color: #FF0000">%s</span> Games Run</center>
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

                self.moreoutput("$('#%s_scorebar').css('width', '%spx'); " % (zombieName, scoreBarLength))
                self.moreoutput("$('#%s_scorebar').css('background-color', '#%s'); " % (zombieName, scoreBarColor))
                self.moreoutput("$('#%s_wins').text('%s'); " % (zombieName, wins))
                self.moreoutput("$('#%s_ties').text('%s'); " % (zombieName, ties))


    def beginTournamentButtonPressed(self):
        global WEB_GUI_NUM_GAMES, TOURNAMENT_RUNNING, START_TIME

        # path will be set to "/start/<NUM GAMES>"
        mo = re.search('(\d+)', self.path)
        if mo is not None:
            WEB_GUI_NUM_GAMES = int(mo.group(1))
        else:
            WEB_GUI_NUM_GAMES = 1000 # default to 1000
        START_TIME = time.time()

        # start the tournament simulation in a separate thread
        tournamentThread = TournamentThread()
        tournamentThread.start()
        TOURNAMENT_RUNNING = True # TOURNAMENT_RUNNING remains True after the tournament completes, until the "/" page is reloaded. Then it is set to False.


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
            scoreTableHtml.append('<tr><td>%s</td><td style="width: %spx;"><div id="%s_scorebar">&nbsp;</div></td><td><span id="%s_wins"></span></td><td><span id="%s_ties"></span></td></tr>' % (zombieName, SCORE_BAR_MAX_WIDTH, zombieName, zombieName, zombieName))
        scoreTableHtml = ''.join(scoreTableHtml)

        # output the main page's html (with the score table)
        self.output("""
            <html>
            <head><title>Zombie Dice Simulator</title>
            <script src="jquery-1.8.3.min.js"></script></head>
            <body>
            <img src="imgZombieCheerleader.jpg" id="cheerleader" style="position: absolute; left: -90px; top: 10px; opacity: 0.0" />
            <img src="imgTitle.png" id="title" style="position: absolute; left: 100px; top: -10px; opacity: 0.0" />
            <div style="position: absolute; left: 30px; top: 610px; font-size: 0.8em;"><center>By Al Sweigart <a href="http://inventwithpython.com">http://inventwithpython.com</a><br /><a href="http://www.amazon.com/gp/product/B003IKMR0U/ref=as_li_qf_sp_asin_il_tl?ie=UTF8&camp=1789&creative=9325&creativeASIN=B003IKMR0U&linkCode=as2&tag=playwithpyth-20">Buy Zombie Dice Online</a><br /><a href="http://inventwithpython.com/blog/2012/11/21/how-to-make-ai-bots-for-zombie-dice">Programming your own Zombie Dice bot.</a></center></div>
            <!-- The mainstatusDiv shows the "Begin Tournament" button, and then the number of games played along with estimated time remaining. -->
            <div id="mainstatusDiv" style="position: absolute; left: 310px; top: 120px; width: 550px; background-color: #EEEEEE; opacity: 0.0"></div>

            <!-- The scoreDiv shows how many wins and ties each bot has. -->
            <div id="scoreDiv" style="position: absolute; left: 310px; top: 220px; width: 550px; background-color: #EEEEEE; opacity: 0.0">

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
            $('#title').animate({opacity: '+=1.0', top: '+=50'}, 1000, function() {
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
        return '000000' # prevent zero division

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




if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == 'web':
        runWebGui()
    else:
        main()