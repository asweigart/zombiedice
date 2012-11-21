# Zombie Dice Simulator desktop web app
# By Al Sweigart al@inventwithpython.com
# Zombie Cheerleader photo by Gianluca Ramalho Misiti https://secure.flickr.com/photos/grmisiti/8149582049/


# oh god this code is messy.

import zombiedice

# ======================================================================================
# Instructions for making your own bot can be found here: http://inventwithpython.com/blog/2012/11/21/how-to-make-ai-bots-for-zombie-dice
# Assign the bots in the tournament here by adding "ZombieBot" objects to the BOTS list:

BOTS = [zombiedice.ZombieBot_MonteCarlo('MonteCarloBot', 40, 100),
        zombiedice.ZombieBot_MonteCarlo('FastMonteCarloBot', 40, 20), # executes faster because it runs fewer experimental rolls
        zombiedice.ZombieBot_MinNumShotgunsThenStops('Min2ShotgunsBot', 2),
        zombiedice.ZombieBot_MinNumShotgunsThenStops('Min1ShotgunBot', 1),
        #zombiedice.ZombieBot_HumanPlayer('Human'), # uncomment if you want to play (learn the rules to Zombie Dice first though)
        zombiedice.ZombieBot_RollsUntilInTheLead('RollsUntilInTheLeadBot'),
        zombiedice.ZombieBot_RandomCoinFlip('RandomBot'),
        ]
# ======================================================================================

import threading, time, webbrowser, os, sys, re, random, logging, platform

if platform.python_version().startswith('2.'):
    from SimpleHTTPServer import * # python 2 code
    from SocketServer import *
else:
    from http.server import HTTPServer, SimpleHTTPRequestHandler # python 3 code



WEB_SERVER_PORT = random.randint(49152, 61000)

SCORE_BAR_MAX_WIDTH = 350 # width in pixels in the web ui for the score bar

TOURNAMENT_RUNNING = False
TOTAL_NUM_GAMES = None
START_TIME = None


def main():
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
        global TOTAL_NUM_GAMES, START_TIME, TOURNAMENT_RUNNING
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
                  Run <input type="text" size="4" id="numGamesToRun" value="1000"> simulated games.<br />
                  <input type="submit" value="Begin Tournament" />
                </form>
                </center>
                """)
        else:
            # display the current status of the tournament simulation that is in progress
            self.output("""
                <center style="font-size:1.5em;">
                <span style="color: #00FF00">%s</span> / <span style="color: #FF0000">%s</span> Games Run</center>
                Estimate Time Remaining: <span style="color: #FF0000">%s</span>
                """ % (zombiedice.TOURNAMENT_STATE['gameNumber'], TOTAL_NUM_GAMES, estTimeRemaining(START_TIME, zombiedice.TOURNAMENT_STATE['gameNumber'], TOTAL_NUM_GAMES)))

            if zombiedice.TOURNAMENT_STATE['gameNumber'] == TOTAL_NUM_GAMES:
                # the javascript code checks for this text to know when to stop making repeated ajax requests for status updates
                self.moreoutput('<center>(Refresh page to run a new tournament.)</center>')


    # Returns JavaScript that will be evaluated by eval() in the web page (elegant solution, I know) to update the score table.
    def renderScoreJavascript(self):
        self.send_header('Content-type','text/html')
        self.end_headers()

        if TOURNAMENT_RUNNING and TOTAL_NUM_GAMES is not None and START_TIME is not None and zombiedice.TOURNAMENT_STATE['gameNumber'] is not None:
            for zombieName in [bot.name for bot in BOTS]:
                predictedMaxWidth = int(SCORE_BAR_MAX_WIDTH * max(int(len(BOTS) / 2.0), 1)) # We'll assume that the bots mostly evenly win games
                #predictedMaxWidth = SCORE_BAR_MAX_WIDTH # If the score bar keeps getting too long, just uncomment this line

                scoreBarLength = int((zombiedice.TOURNAMENT_STATE['wins'][zombieName] / float(TOTAL_NUM_GAMES)) * predictedMaxWidth)
                scoreBarColor = getScoreBarColor(zombieName, zombiedice.TOURNAMENT_STATE['wins'])
                wins = zombiedice.TOURNAMENT_STATE['wins'][zombieName]
                ties = zombiedice.TOURNAMENT_STATE['ties'][zombieName]

                self.moreoutput("$('#%s_scorebar').css('width', '%spx'); " % (zombieName, scoreBarLength))
                self.moreoutput("$('#%s_scorebar').css('background-color', '#%s'); " % (zombieName, scoreBarColor))
                self.moreoutput("$('#%s_wins').text('%s'); " % (zombieName, wins))
                self.moreoutput("$('#%s_ties').text('%s'); " % (zombieName, ties))


    def beginTournamentButtonPressed(self):
        global TOTAL_NUM_GAMES, TOURNAMENT_RUNNING, START_TIME

        # path will be set to "/start/<NUM GAMES>"
        mo = re.search('(\d+)', self.path)
        if mo is not None:
            TOTAL_NUM_GAMES = int(mo.group(1))
        else:
            TOTAL_NUM_GAMES = 1000 # default to 1000
        START_TIME = time.time()

        # start the tournament simulation in a separate thread
        tournamentThread = TournamentThread()
        tournamentThread.start()
        TOURNAMENT_RUNNING = True # TOURNAMENT_RUNNING remains True after the tournament completes, until the "/" page is reloaded. Then it is set to False.


    def renderMainPage(self):
        global TOTAL_NUM_GAMES, TOURNAMENT_RUNNING, START_TIME

        # when this page is loaded, if the previous tournmaent completed then restart the tournament:
        if TOTAL_NUM_GAMES is not None and zombiedice.TOURNAMENT_STATE['gameNumber'] == TOTAL_NUM_GAMES:
            TOURNAMENT_RUNNING = False # set to True after user clicks the "Begin Tournament" button in the web ui and the tournamentThread starts running.
            TOTAL_NUM_GAMES = None # TODO - make this a member variable instead of a global
            START_TIME = None # timestamp of when the tournament started, used for the "estimated time remaining"
            #zombiedice.TOURNAMENT_STATE['gameNumber'] = 0 #

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
        zombiedice.runTournament(BOTS, TOTAL_NUM_GAMES)


class BrowserOpener(threading.Thread):
    def run(self):
        time.sleep(0.4) # give the server a bit of time to start
        webbrowser.open('http://localhost:%s' % (WEB_SERVER_PORT))


if __name__ == '__main__':
    main()
    # program doesn't terminate at this point because the HTTP server thread is now running
