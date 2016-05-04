# Lawn
Tron, but with grass

The goal of this game is to drive around the screen and not run into the
streams coming from the mowers as well as the walls. The last player
left alie wins


In order to run the game you will need python with the twisted and 
pygame libraries installed. To start the game, first we need to run the
matchmaking server. First configure the host and port in matchmaker.py 
to be the machine and port number you would like to run on then run the
server. To do so `python matchmaker.py`. The server will then be ready 
to accept players.


A maximum of four players can play in one game and also a minimum of
two. Configure the client.py files so that it connects to the server
that you just started running. Then start the client by running 
`python client.py`. Once you have connected, you will see a title screen
with information about the number of players connected, the number of
players ready to play, and how much time until the game begins. To
ready up, simply make sure you are in the game window then press r. Once the time has run out, the game will begin. A loading screen will then
appear telling you what player you are and where you will start. Once
the grass background returns, the game has begun. Use the arrow keys to steer your mower.
