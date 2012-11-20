"""
TODO
General code cleanup and documentation
random port
flickr credit to that guy

"""


# Zombie Dice Simulator desktop web app
# By Al Sweigart al@inventwithpython.com

# oh god this code is messy.


from http.server import HTTPServer, SimpleHTTPRequestHandler
import zombiedice, threading, time, webbrowser, os, sys, random, re


# ==============================
# Assign the bots here:

BOTS = [zombiedice.ZombieBot_MonteCarlo('MonteCarlo', 40, 100),
        zombiedice.ZombieBot_MinNumShotgunsThenStops('Min2ShotgunsBot', 2),
        zombiedice.ZombieBot_RandomCoinFlip('RandomBot'),
        ]

# ==============================



GAMERUNNING = False
NUMGAMES = None
ZD_PORT = random.randint(100, 10000)
STARTTIME = None
TOURNAMENT_THREAD = None


class ZombieDiceHandler(SimpleHTTPRequestHandler):
    def output(self, msg):
        self.send_header('Content-type','text/html')
        self.end_headers()
        self.wfile.write(msg.encode('ascii'))

    def moreoutput(self, msg):
        self.wfile.write(msg.encode('ascii'))


    def do_GET(self):
        global NUMGAMES, STARTTIME, GAMERUNNING
        self.send_response(200)
        reqPath = os.path.join(os.getcwd(), os.path.normpath(self.path[1:]))

        if os.path.isfile(reqPath):
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
        elif self.path == '/mainstatus':

            if not GAMERUNNING:
                self.output("""
<center>
Run <input type="text" size="4" id="numGamesToRun" value="1000"> simulated games.<br />
<input type="button" value="Begin Tournament" onclick="startTournament()" />
</center>
""")
            elif GAMERUNNING and NUMGAMES is not None and STARTTIME is not None and zombiedice.CURRENT_GAME_NUM is not None:
                self.output("""
<center style="font-size:1.5em;">
<span style="color: #00FF00">%s</span> / <span style="color: #FF0000">%s</span> Games Run<br />
Estimate Time Remaining: <span style="color: #FF0000">%s</span>
</center>
""" % (zombiedice.CURRENT_GAME_NUM, NUMGAMES, estTimeRemaining(STARTTIME, zombiedice.CURRENT_GAME_NUM, NUMGAMES)))


                if zombiedice.CURRENT_GAME_NUM == NUMGAMES:
                    self.moreoutput('<center>(Refresh page to run a new tournament.)</center>')
                    self.moreoutput("""<!--DONE-->""") # oh god this is a terrible way to indicate the end of the tournament
            else:
                pass #self.output('%s %s %s' % (NUMGAMES, STARTTIME, zombiedice.CURRENT_GAME_NUM))

        elif self.path == '/score':
            self.output("""
            """) # yep, returning javascript code that will be passed to eval. Elegant.

            if GAMERUNNING and NUMGAMES is not None and STARTTIME is not None and zombiedice.CURRENT_GAME_NUM is not None:
                for zombieName in [bot.name for bot in BOTS]:
                    self.moreoutput("""$('#%s_scorebar').css('width', '%spx'); """ % (zombieName, getScoreBarLength(zombiedice.TOURNAMENT_STATE['wins'][zombieName], NUMGAMES, 300)))
                    self.moreoutput("""$('#%s_scorebar').css('background-color', '#%s'); """ % (zombieName, getScoreBarColor(zombieName, zombiedice.TOURNAMENT_STATE['wins'])))
                    self.moreoutput("""$('#%s_wins').text('%s'); """ % (zombieName, zombiedice.TOURNAMENT_STATE['wins'][zombieName]))
                    self.moreoutput("""$('#%s_ties').text('%s'); """ % (zombieName, zombiedice.TOURNAMENT_STATE['ties'][zombieName]))

        elif self.path.startswith('/start'):
            mo = re.search('(\d+)', self.path)
            if mo is not None:
                NUMGAMES = int(mo.group(1))
            if NUMGAMES is None:
                NUMGAMES = 1000
            STARTTIME = time.time()
            TOURNAMENT_THREAD = TournamentThread()
            TOURNAMENT_THREAD.start()
            GAMERUNNING = True
            #self.output('Tournament started. Running %s games.' % (NUMGAMES))
        elif self.path == '/':

            # TODO - code to restart tournament goes here
            if NUMGAMES is not None and zombiedice.CURRENT_GAME_NUM == NUMGAMES:
                # restart the tournament
                GAMERUNNING = False
                NUMGAMES = None
                STARTTIME = None
                zombiedice.CURRENT_GAME_NUM = None

            scoreTableHtml = []
            for zombieName in [bot.name for bot in BOTS]:
                scoreTableHtml.append('<tr><td>%s</td><td style="width: 300px;"><div id="%s_scorebar">&nbsp;</div></td><td><span id="%s_wins"></span></td><td><span id="%s_ties"></span></td></tr>' % (zombieName, zombieName, zombieName, zombieName))
            scoreTableHtml = ''.join(scoreTableHtml)

            self.output("""
<html>
<head><title>Zombie Dice Simulator</title>
<script src="jquery-1.8.3.min.js"></script></head>
<body>
<img src="imgZombieCheerleader.jpg" id="cheerleader" style="position: absolute; left: -90px; top: 10px; opacity: 0.0" />
<img src="imgTitle.png" id="title" style="position: absolute; left: 100px; top: -10px; opacity: 0.0" />

<div id="mainstatusDiv" style="position: absolute; left: 310px; top: 120px; width: 550px; background-color: #EEEEEE; opacity: 0.0"></div>

<div id="scoreDiv" style="position: absolute; left: 310px; top: 220px; width: 550px; background-color: #EEEEEE; opacity: 0.0">
<table border="0">
<tr><td colspan="2"></td><td>Wins</td><td>Ties</td>
%s
</table>
</div>

<script>
var ajaxIntervalID = undefined;
$('#cheerleader').animate({opacity: '+=1.0', left: '+=100'}, 600, null)
$('#title').animate({opacity: '+=1.0', top: '+=50'}, 1000, function() {
    updateMainStatus();
    $('#mainstatusDiv').css('opacity', '1.0');
    $('#scoreDiv').css('opacity', '1.0');
})


function updateMainStatus() {
    console.log('updateMainStatus()')
    $.ajax({
      url: "mainstatus",
      context: document.body,
      success: function(data){
        $('#mainstatusDiv').html(data);
        if (data.indexOf('DONE') != -1 && ajaxIntervalID !== undefined) {
            clearInterval(ajaxIntervalID);
        }
      }
    });

    $.ajax({
      url: "score",
      context: document.body,
      success: function(data) {
        eval(data);
      }
    });
}


function startTournament() {
   $.ajax({
      url: "start/" + $("#numGamesToRun").val(),
      context: document.body,
      success: function(data){
        console.log('Tournament started.');
      }
    });
    ajaxIntervalID = setInterval('updateMainStatus()', 100);
}

</script>
</body>
</html>
""" % (scoreTableHtml))


def getScoreBarColor(zombieName, winsState):
    maxScore = max(winsState.values())
    myScore = winsState[zombieName]

    redness = int((myScore / float(maxScore)) * 255)
    redness = hex(redness)[2:].upper()
    if len(redness) == 1:
        redness = '0' + redness
    return redness + '0000'

def getScoreBarLength(wins, totalNumGames, maxLength):
    return int((wins / totalNumGames) * maxLength)


def estTimeRemaining(startTime, currentGame, totalGames):
    lapsed = time.time() - startTime
    totalEstTime = lapsed * (totalGames / currentGame)
    return prettyTime(round(totalEstTime - lapsed, 1))


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
    if wk > 0 or day > 0 or hr > 0:
        t_str.append('%s min' % (min))
    t_str.append('%s sec' % (sec))

    return ''.join(t_str)


class ZombieWebServThread(threading.Thread):
    def run(self):
        httpd = HTTPServer(('127.0.0.1', ZD_PORT), ZombieDiceHandler)
        httpd.serve_forever()

class TournamentThread(threading.Thread):
    def run(self):
        zombiedice.runTournament(BOTS, NUMGAMES)

zomWeb = ZombieWebServThread()
zomWeb.start()
time.sleep(0.2)
webbrowser.open('http://localhost:%s' % (ZD_PORT))

while True:
    time.sleep(1)


# https://secure.flickr.com/photos/grmisiti/8149582049/sizes/o/in/photostream/
# photo by Gianluca Ramalho Misiti
