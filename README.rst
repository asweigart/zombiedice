Zombie Dice Simulator
=====================

A simulator for the dice game Zombie Dice that can run bot AI players.

A full (but outdated) blog article explaining how these programs work (and the rules of Zombie Dice) can be found here: http://inventwithpython.com/blog/2012/11/21/how-to-make-ai-bots-for-zombie-dice/

This is useful for beginner/intermediate programming lessons or contests. The API for making bots is simple, and it features a web UI for projecting a nifty display of the tournament as it runs.

.. image:: screenshot.jpg

Quickstart
----------

First, you need to learn how to play Zombie Dice (this takes just a few minutes):

* `PDF of the rules in English <http://www.sjgames.com/dice/zombiedice/img/ZDRules_English.pdf>`_
* `Animated Flash demo of how to play <http://www.sjgames.com/dice/zombiedice/demo.html>`_
* `Instructables article with the rules <https://www.instructables.com/id/How-to-play-Zombie-Dice/>`_

Next, you need to create your own zombie. This is done by creating a class that implements a ``turn()`` method (called when it is your zombie's turn). The ``turn()`` method either calls the ``zombiedice.roll()`` function if you want to roll again, or returns to signal the end of their turn. The ``turn()`` method accepts one argument of the game state (documented later on this page). This class should also have a ``'name'`` attribute that contains a string of the player name. (This is so that the same class can be used for multiple players in a game.)

The ``zombiedice.roll()`` function returns a list of dictionaries. The dictionaries represent the dice roll results; it has a ``'color'`` and ``'icon'`` keys, which have possible values of ``'green'``, ``'yellow'``, ``'red'`` and ``'shotgun'``, ``'brains'``, and ``'footsteps'`` respectively. The list will contain three of these dictionaries for the three dice roll results. If the player has reached three shotguns or more, this list will be empty.

Here's an example of a zombie that keeps rolling until they've reached two shotguns, then stops. More example zombies can be found in *examples.py* in the *zombiedice* package.

..
    class StopsAt2ShotgunsZombie(object):
        """This bot keeps rolling until it reaches 2 shotguns."""
        def __init__(self, name):
            self.name = name

        def turn(self, gameState):
            shotgunsRolled = 0
            while shotgunsRolled < 2:
                results = roll()

                if results == []:
                    # Zombie has reached 3 or more shotguns.
                    return

                for i in results:
                    # Count shotguns in results.
                    if i[ICON] == SHOTGUN:
                        shotguns += 1

To run a tournament, create a file that calls either ``zombiedice.runWebGui()`` (for the nice web GUI) or ``zombiedice.runTournament()`` (for the plain command line interface). A typical file will look like *demo.py* in the `repo <https://github.com/asweigart/zombiedice>`_:

..
    from zombiedice import runTournament, runWebGui
    import zombiedice

    zombies = (
        zombiedice.examples.RandomCoinFlipZombie(name='Random'),
        zombiedice.examples.MonteCarloZombie(name='Monte Carlo', riskiness=40, numExperiments=20),
        zombiedice.examples.MinNumShotgunsThenStopsZombie(name='Min 2 Shotguns', minShotguns=2)
        # Add any other zombie players here.
    )

    # Uncomment one of the following lines to run in CLI or Web GUI mode:
    #runTournament(zombies=zombies, numGames=100, verbose=False)
    runWebGui(zombies=zombies, numGames=100, verbose=False)

