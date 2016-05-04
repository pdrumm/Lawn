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
PLAYER_PORT = 40091
# Game vars
MAX_PLAYERS = 4
WAIT_TIME = 60 #seconds
READY_TIME = 5 #seconds
GAME_PORT = 40055
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
	"""An instance of the Protocol class is instantiated when you connect to the client and will go away when the connection is finished. This connection protocol handles home's connection on the command port, which is used to do initial setup and pass high level instructions."""
	def __init__(self,addr,players):
		"""This method initializes a few important varibles for the CommandServerConnection. The addr stores the ip address of the work client connected to itself. The ClientConn and DataConn, currently initiated to None, will point to the instance of the ClientServerConnection and DataServerConnection  that home has at a given instance in time. The queue is a deferred queue which will temporarily hold data sent from the ssh client until the data connection is made."""
		self.addr = addr
		self.is_ready = False
		self.players = players
		print 'matchmaker initialized!'

	def connectionMade(self):
		"""When the command connection to work is made, begin to listen on the client port for any potential ssh client requests."""
		print 'player connection received from {addr}'.format(addr=self.addr)
		self.players.append(self)

	# Player -> Matchmaker
	def dataReceived(self,data):
		"""After establishing the connection with work, home has no need to receive any data from work over the command connection."""
		print data
		if data == "ready":
			self.is_ready = True

	def update_player(self,data):
		"""Send the player the up to date game info"""
		print "data: {data}".format(data=data)
		data = pickle.dumps(data)
		self.transport.write(data)

	def start_game(self,pNum,player_count,game_port):
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
		"""If the command connection is lost with work, then the home script should stop running."""
		print 'matchmaker connection lost to {addr}'.format(addr=self.addr)
		try:
			self.players.remove(self)
		except:
			pass


class MatchmakerServerConnectionFactory(Factory):
	"""The ServerFactory is a factory that creates Protocols and receives events relating to the conenction state."""
	def __init__(self,players):
		self.players = players
		print 'MatchmakerServerConnFactory initialized!'
	def buildProtocol(self,addr):
		"""Creates an instance of a subclass of Protocol. We override this method to alter how Protocol instances get created by using the CommandServerConnection class that inherits from Protocol. This creates an instance of a CommandServerConnection with a given client that connects to the proxy."""
		print 'conn attempted'
		return MatchmakerServerConnection(addr,self.players)


####################################################
################ LOOPING CALL ######################
####################################################

def matchmaker_loop_iterate(players):
	"""This loop will determine whether or not to start a game by checking the status of all of the players, and then do so if called for."""
	# globals
	global MAX_PLAYERS, INIT_TIMER, START_TIME, GAME_PORT, WAIT_TIME, CURR_TIME, READY_TIME, FINAL_DIFF

	num_players = len(players)
	# if there is only one player connected, tell them that we're waiting for more
#	if num_players <= 1:
#		for i in range(num_players):
#			players[i].update_player({
#				"Begin Game": False,
#				"Players Ready": 1,
#				"Players Total": 1,
#				"Time Left": int(WAIT_TIME)
#			})
#		INIT_TIMER = 1
#		return

	# check if we need to initialize the timer
	if INIT_TIMER:
		print "initializing timer"
		START_TIME = time.time()
		# store the start time of the automatic begin-play countdown for each player
		for i in range(num_players):
			if i >= MAX_PLAYERS:
				break
			players[i].countdown = START_TIME
		INIT_TIMER = 0

	# update the game-start timer
	CURR_TIME = WAIT_TIME - (time.time()-START_TIME)

	# If everyone is ready, then set decrease the clock to a smaller time-til-game-start
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
	# if there are MAX players, then autostart
	if num_players >= MAX_PLAYERS:
		players_ready = MAX_PLAYERS
		if CURR_TIME > READY_TIME:
			CURR_TIME = READY_TIME - FINAL_DIFF
			FINAL_DIFF += 1

	# update each of the players on other players and when the game will begin
	if CURR_TIME > 0.0:
		for i in range(num_players):
			if i >= MAX_PLAYERS-1:
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
		# fork off a new game server for the clients to connect to
		try:
			pid = os.fork()
		except OSError as e:
			print "could not fork game server process"
			sys.exit(1)
		if pid == 0: #child
			print "exec'ing the game server"
			os.execlp("python","python","game_server.py",str(players_ready),str(GAME_PORT))
		else: #parent
			# tell each player that their game is beginning, and which player number they are
			for i in range(players_ready):
				player = players.pop(0)
				player.start_game(i,players_ready,GAME_PORT)
			GAME_PORT += 1
			INIT_TIMER = 1
			FINAL_DIFF = 0


# Handler for dead children
def sigchld_handler(signum, frame):
	os.wait()

####################################################
###################### MAIN ########################
####################################################

if __name__ == '__main__':

	# create a handler to collect children procs when they die
	signal.signal(signal.SIGCHLD,sigchld_handler)

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
