import sys, getopt, os, signal
import time
try:
	import cPickle as pickle
except:
	import pickle
# Twisted
from twisted.internet.protocol import Factory
from twisted.internet.protocol import ClientFactory
from twisted.internet.protocol import Protocol
from twisted.internet import reactor
from twisted.internet import error as twisted_error
from twisted.internet.defer import DeferredQueue
from twisted.internet.task import LoopingCall

# Define Ports:
PLAYER_PORT = 40091 #the port that the players will reach the matchmaker on
# Game vars
MAX_PLAYERS = 4
WAIT_TIME = 60 #seconds
READY_TIME = 5 #seconds
GAME_PORT = 40055 #starting port for game server to listen on
HOST_NAME = "student03.cse.nd.edu"
# Clock vars
INIT_TIMER = True
START_TIME = 0.0
CURR_TIME = WAIT_TIME
FINAL_DIFF = 0


####################################################
############ GAME SERVER CONNECTION ################
####################################################

class MatchmakerServerConnection(Protocol):
	"""A Matchmaking server connection is created for every client player. This matchmaker connection is used to collect user information so that players can be paired up with a game server and then begin playing a game."""
	def __init__(self,addr,players):
		"""This method initializes a few important varibles, most notably being self.players. self.players is an array that the matchmaker uses to store all client player connections. Once a player connects, the player connection adds itself to this list of connections. This list is then used in the main looping call to service the players."""
		self.addr = addr
		self.is_ready = False
		self.players = players

	def connectionMade(self):
		"""When a connection with a client player is made, add that player to the Matchmaker's list of player connections."""
		print 'MATCHMAKER: player connection received from {addr}'.format(addr=self.addr)
		self.players.append(self)

	# Player -> Matchmaker
	def dataReceived(self,data):
		"""The only data that the matchmaker needs from each player is if they are ready to play or not."""
		if data == "ready":
			self.is_ready = True

	def update_player(self,data):
		"""Send the player updates on how many other players are online, how many are ready to play, how long until the game begins, etc."""
		data = pickle.dumps(data)
		self.transport.write(data)

	def start_game(self,pNum,player_count,game_port):
		"""When a group of players has been matched up and is ready to play, this method is called for each of their connections. This essentially sends the players game info such as where to find their game server at and how many players will be in the game."""
		data = {
			"Begin Game": True,
			"Player Number": pNum,
			"Players Total": player_count,
			"Host": HOST_NAME,
			"Port": game_port
		}
		self.update_player(data)
		self.transport.loseConnection()

	def connectionLost(self,reason):
		"""If the connection with a client player is lost, then take them off of the list of players."""
		try:
			self.players.remove(self)
		except:
			pass


class MatchmakerServerConnectionFactory(Factory):
	def __init__(self,players):
		"""Store the players list so that it can be passed to each player conenction created/"""
		print 'MATCHMAKER: Matchmaker initialized!'
		self.players = players
	def buildProtocol(self,addr):
		"""Create an instance of the Matchmaker server connection when a new client connects. This connection is used to uniquely service that client."""
		return MatchmakerServerConnection(addr,self.players)


####################################################
################ LOOPING CALL ######################
####################################################

def matchmaker_loop_iterate(players):
	"""This 'game loop' is run once a second to service players who want to play the game. It loops through the player conenctions to see if players are ready to begin a game, and if they are, then a new game server process is forked for that group of players. When a game is created for a group of players, they have been successfully serviced by the matchmaker, which then begins to service any more players that are trying to play the game."""
	# globals
	global MAX_PLAYERS, INIT_TIMER, START_TIME, GAME_PORT, WAIT_TIME, CURR_TIME, READY_TIME, FINAL_DIFF
	# local
	num_players = len(players)

	# Check if we need to initialize the timer.
	# The timer is a countdown until when the game will begin.
	# The timer is initialized once a group of 2 or more players are online. 
	if INIT_TIMER:
		START_TIME = time.time()
		INIT_TIMER = 0

	# update the game-start timer
	CURR_TIME = WAIT_TIME - (time.time()-START_TIME)

	# Determine if everyone is ready
	# If everyone is ready, then immediately decrease the clock to ~5 seconds so that they dont have to continue waiting
	players_ready = 0
	players_total = 0
	for i in range(num_players):
		if i >= MAX_PLAYERS:
			break
		players_total += 1
		if players[i].is_ready:
			players_ready += 1
	if players_ready == players_total and num_players>1:
		if CURR_TIME > READY_TIME:
			CURR_TIME = READY_TIME - FINAL_DIFF
			FINAL_DIFF += 1
	# if there are MAX players, then autostart the game (they dont need to tell us that theyre ready)
	if num_players >= MAX_PLAYERS:
		players_ready = MAX_PLAYERS
		if CURR_TIME > READY_TIME:
			CURR_TIME = READY_TIME - FINAL_DIFF
			FINAL_DIFF += 1

	# update each of the players on other players and when the game will begin
	if CURR_TIME > 0.0:
		for i in range(num_players):
			if i >= MAX_PLAYERS:
				break
			players[i].update_player({
				"Begin Game": False,
				"Players Ready": players_ready,
				"Players Total": players_total,
				"Time Left": int(CURR_TIME)
			})
		if num_players <= 1:
			INIT_TIMER = 1
	# if the timer hits zero, then begin the game!
	else:
		# calculate the number of players in the game
		players_ready = 0
		for i in range(num_players):
			if i >= MAX_PLAYERS:
				break
			players_ready += 1
		# fork off a new game server for the clients to connect to
		try:
			pid = os.fork()
		except OSError as e:
			print "MATCHMAKER: Error: Could not fork a game server process"
			sys.exit(1)
		if pid == 0: #child
			os.execlp("python","python","game_server.py",str(players_ready),str(GAME_PORT))
		else: #parent
			# create a handler to collect children procs when they die
			signal.signal(signal.SIGCHLD,sigchld_handler)

			# tell each player that their game is beginning, and which player number they are
			for i in range(players_ready):
				player = players.pop(0)
				player.start_game(i,players_ready,GAME_PORT)

			GAME_PORT += 1
			INIT_TIMER = 1
			FINAL_DIFF = 0


# Handler to collect children procs when they die
def sigchld_handler(signum, frame):
	print 'MATCHMAKER: Child GameServer process completed.'
	os.wait()

####################################################
###################### MAIN ########################
####################################################

if __name__ == '__main__':

	# array to keep track of all player connections made
	players = []

	# Listen for players to connect
	# the reactor is just an event processor
	reactor.listenTCP(
		PLAYER_PORT,
		MatchmakerServerConnectionFactory(players)
	)

	# initialize game loop
	lc = LoopingCall(matchmaker_loop_iterate,players)
	lc.start(1.0)

	# begin reactor event loop
	reactor.run()

	# after reactor stops, end game loop
	lc.stop()
