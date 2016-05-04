# Lawn
#####Tron, but with grass.

The goal of this game is to drive around the screen and not run into the
streams coming from the mowers or the edge of the screen. The last player
left alive wins.


In order to run the game you will need python with the twisted and 
pygame libraries installed. Before starting up the game, configure the 
host and port in matchmaker.py to be the machine and port number you would 
like the matchmaking server to run on. However, default values are already 
provided. Now, to start up the game, first run the matchmaking server. 
To do so, execute `python matchmaker.py`. The matchmaking server will then 
be ready to accept new players.


A maximum of four players can play in one game at a time and a minimum of
two. If you changed the host machine or port number on the matchmaking server, 
then please also configure the client.py file so that it will connect to the 
server that you just started running. Next, start the client by running 
`python client.py`. Once you have connected, you will see a title screen
with information about the number of players connected, the number of
players ready to play, and how much time until the game begins. To
tell the server that you are ready to play, simply make sure that you are 
in the game window and then press **r**. It is important to remember that the
matchmaker needs at least two players to begin a new game! Once the time on
the clock has run out, the game will begin. A loading screen will
appear, showing you which player you are and where you will start. Once
the grass background returns, the game will immediately begin. Use the 
arrow keys to steer your mower...*and good luck!*
