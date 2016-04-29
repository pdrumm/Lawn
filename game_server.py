import sys, getopt
from server_player import Player
# Twisted
from twisted.internet.protocol import Factory
from twisted.internet.protocol import ClientFactory
from twisted.internet.protocol import Protocol
from twisted.internet import reactor
from twisted.internet import error as twisted_error
from twisted.internet.defer import DeferredQueue
from twisted.internet.task import LoopingCall

# Define Ports: player1 gets port BASE_PORT, player2 gets port BASE_PORT+1, etc
BASE_PORT = 40755


####################################################
############ GAME SERVER CONNECTION ################
####################################################

class GameServerConnection(Protocol):
	"""An instance of the Protocol class is instantiated when you connect to the client and will go away when the connection is finished. This connection protocol handles home's connection on the command port, which is used to do initial setup and pass high level instructions."""
	def __init__(self,addr,player,queue):
		"""This method initializes a few important varibles for the CommandServerConnection. The addr stores the ip address of the work client connected to itself. The ClientConn and DataConn, currently initiated to None, will point to the instance of the ClientServerConnection and DataServerConnection  that home has at a given instance in time. The queue is a deferred queue which will temporarily hold data sent from the ssh client until the data connection is made."""
		self.addr = addr
#		self.ClientConn = None
#		self.DataConn = None
		self.queue = queue
		self.player = player
		print 'game server initialized!'

	def connectionMade(self):
		"""When the command connection to work is made, begin to listen on the client port for any potential ssh client requests."""
#		reactor.listenTCP(
#			CLIENT_PORT,
#			ClientServerConnectionFactory(self)
#		)
		print 'command connection received from {addr}'.format(addr=self.addr)
		self.player.server_conn = self

	# Work -> Home
	def dataReceived(self,data):
		"""After establishing the connection with work, home has no need to receive any data from work over the command connection."""
		self.queue.put(data)
		self.player.queue_len += 1

	def update_position(self):
		data = str(self.player.x)+','+str(self.player.y)
		self.transport.write(data)
		print data

	def connectionLost(self,reason):
		"""If the command connection is lost with work, then the home script should stop running."""
		print 'command connection lost to {addr}'.format(addr=self.addr)
		try:
			reactor.stop()
		except twisted_error.ReactorNotRunning:
			pass


class GameServerConnectionFactory(Factory):
	"""The ServerFactory is a factory that creates Protocols and receives events relating to the conenction state."""
	def __init__(self,player,queue):
		self.queue = queue
		self.player = player
		print 'GameServerConnFactory initialized!'
	def buildProtocol(self,addr):
		"""Creates an instance of a subclass of Protocol. We override this method to alter how Protocol instances get created by using the CommandServerConnection class that inherits from Protocol. This creates an instance of a CommandServerConnection with a given client that connects to the proxy."""
		print 'conn attempted'
		return GameServerConnection(addr,self.player,self.queue)


####################################################
################ LOOPING CALL ######################
####################################################

tick = 0
def game_loop_iterate(players,player_DQs):
	# check to see if all players are ready
	for player in players:
		if player.server_conn == None:
			print 'All players not ready!'
			return

	# update game clock
	global tick
	tick += 1

	# tick players
	for player in players:
		player.update()

	# send players new gamestate data
	for player in players:
		player.server_conn.update_position()

	# check for user input
	# for each player, if they have a keypress in the queue, then retrieve the top one
	for player in range(len(players)):
		if players[player].queue_len > 0:
			players[player].queue_len -= 1
			player_DQs[player].get().addCallback(players[player].update_dir)

####################################################
###################### MAIN ########################
####################################################

if __name__ == '__main__':

	# listen on all players' ports
	players_range = range(int(sys.argv[1]))
	players = []
	player_DQs = []
	for i in players_range:
		# create new player
		player = Player()
		players.append(player)
		# create player DeferredQueue array
		queue = DeferredQueue()
		player_DQs.append(queue)
		# the reactor is just an event processor
		print BASE_PORT + i
		reactor.listenTCP(
			BASE_PORT + i,
			GameServerConnectionFactory(player,queue)
		)

	# initialize game loop
	lc = LoopingCall(game_loop_iterate,players,player_DQs)
	lc.start(1.0/60)

	# begin reactor event loop
	reactor.run()

	# after reactor stops, end game loop
	lc.stop()
