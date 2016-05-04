import sys, getopt, os
from server_player import Player
try:
	import cPickle as pickle
except:
	import pickle
import pygame
# Twisted
from twisted.internet.protocol import Factory
from twisted.internet.protocol import ClientFactory
from twisted.internet.protocol import Protocol
from twisted.internet import reactor
from twisted.internet import error as twisted_error
from twisted.internet.defer import DeferredQueue
from twisted.internet.task import LoopingCall

# Define Ports:
GAME_PORT = 40055


####################################################
############ GAME SERVER CONNECTION ################
####################################################

class GameServerConnection(Protocol):
	"""A game server connection is created for each player in this instance of the game. The game server connection is used to collect user input from the player, update the game state accordingly, and then send the new gamestate back to the user."""
	def __init__(self,addr,players):
		"""This method initializes a few important varibles, including variables unique to the player assigned to this conneciton. Some of these variables are the player's unique Player Number for the game, the player's message queue, and the player's server_player.Player instance."""
		self.addr = addr
		self.players = players
		self.player_num = None
		self.queue = None
		self.player = None
		self.still_playing = True

	def connectionMade(self):
		pass

	# Player -> Game Server
	def dataReceived(self,data):
		"""The game server will receive one of two types of data from the player. At the very beginning of the game, the player tells the game server what their Player Number is so that the game server can assign it some corresponding unique variables to that number. Otherwise, the data received will be key presses that the server will then process to update the gamestate."""
		data = pickle.loads(data)
		for key in data.keys():
			if key == "Player Number":
				self.player_num = data[key]
				self.queue = self.players[self.player_num]['queue']
				self.player = self.players[self.player_num]['player']
				self.player.server_conn = self
				print 'Player #{num} ready to begin'.format(num=self.player_num)
			elif key == "Key":
				self.queue.put(data[key])
				self.player.queue_len += 1

	def update_player(self,player_centers):
		"""Send the player the up to date game state/info"""
		data = pickle.dumps(player_centers)
		self.transport.write(data)

	def connectionLost(self,reason):
		"""If the player's connection is lost, then the server keeps track of this. No action will be taken, unless all players' connections are lost."""
		self.still_playing = False


class GameServerConnectionFactory(Factory):
	def __init__(self,players):
		print 'Game Server initialized!'
		self.players = players
	def buildProtocol(self,addr):
		"""Build an instance of a game server connection that may service the player trying to connect."""
		return GameServerConnection(addr,self.players)


####################################################
################ LOOPING CALL ######################
####################################################

class GameSpace(object):
	"""The gamespace is an object, used for convenience, to keep track of player data. This object also has a number of methods used to reduce any sort of redundancy and keep the main game loop as clean as possible."""
	def __init__(self, player_range):
		pygame.init()

		##################
		# GameSpace vars #
		##################
		self.tick = 0
		self.players_ready = False

		# Create players & player vars
		self.player_count = len(player_range)
		self.players = [] # an array of each player dict
		for i in player_range:
			# create new player object
			player = Player(i)
			queue = DeferredQueue()
			self.players.append({
				'player_num': i,
				'player': player,
				'queue': queue
			})

		# create a sprite group for all players' ghosts
		self.ghosts = pygame.sprite.Group()

		# default rect size
		image = pygame.image.load("images/laser_original.png")
		self.default_rect = image.get_rect()

		# array to hold the up to date position of players
		self.player_state = []
		for i in player_range:
			self.player_state.append({
				"center": [],
				"direction": "",
				"alive": True
			})

	def new_ghost(self,center):
		"""Generate and return a new sprite. This function is used to return a new instance of a 'ghost' object - ie. a piece of the trail behind one of the players."""
		ghost = pygame.sprite.Sprite()
		ghost.rect = self.default_rect.copy()
		ghost.rect.center = center
		return ghost

	def calculate_collisions(self):
		"""This method will determine if any player has collided with one of the players' ghosts. It loops through the ghost sprites and determines if any of them collide with a 1xY or Xx1 rectangle that represents the very front edge of the player."""
		for pObj in self.players:
			player = pObj['player']
			# get/set curr rect of player
			curr_pos = self.new_ghost([player.x, player.y])
			# set w,h of rect to match direction of movement
			if player.direction == "U":
				curr_pos.rect.centery -= curr_pos.rect.height
				curr_pos.rect.height = 1
			elif player.direction == "D":
				curr_pos.rect.centery += curr_pos.rect.height
				curr_pos.rect.height = 1
			elif player.direction == "L":
				curr_pos.rect.centerx -= curr_pos.rect.width
				curr_pos.rect.width = 1
			elif player.direction == "R":
				curr_pos.rect.centerx += curr_pos.rect.width
				curr_pos.rect.width = 1
			# collision detection
			contact = pygame.sprite.spritecollide(curr_pos,self.ghosts,False)
			if (len(contact)>0 or player.is_out_of_bounds() ):
				player.is_alive = False

	def wait_for_players(self):
		"""Do not start the main functionality of the game loop until all of the players are connected."""
		# check to see if all players are ready
		players_ready_count = self.player_count
		for pObj in self.players:
			if pObj['player'].server_conn == None:
				players_ready_count-=1

		if players_ready_count == self.player_count:
			self.players_ready = True


	def game_loop_iterate(self):
		"""Input players is an array of objects of the form {player_num,player,queue}. This game loop will tick the players, updating the overall gamestate, and then send the new gamestate back to each of the players."""
		# wait until all players have connected
		if not self.players_ready:
			gs.wait_for_players()
			return

		# update game clock
		self.tick += 1

		# tick players
		for pObj in self.players:
			self.player_state[pObj['player_num']]["alive"] = pObj['player'].is_alive
			if pObj['player'].is_alive:
				# generate new ghost for each player
				old_center = [pObj['player'].x,pObj['player'].y]
				self.ghosts.add(self.new_ghost(old_center))

				# update each players' (x,y)
				pObj['player'].update()

				# store array of new positions & direction
				self.player_state[pObj['player_num']]["center"] = [pObj['player'].x, pObj['player'].y]
				self.player_state[pObj['player_num']]["direction"] = pObj['player'].direction

		# collision detection
		self.calculate_collisions()

		# send players new gamestate data
		for pObj in self.players:
			pObj['player'].server_conn.update_player(self.player_state)

		# check for user input
		# for each player, if they have a keypress in the queue, then retrieve the top one
		for pObj in self.players:
			if pObj['player'].queue_len > 0:
				pObj['player'].queue_len -= 1
				pObj['queue'].get().addCallback(pObj['player'].update_dir)

		# end event loop if all players have lost connection
		no_connections = True
		for pObj in self.players:
			if pObj['player'].server_conn.still_playing:
				no_connections = False
		if no_connections:
			reactor.stop()
			

####################################################
###################### MAIN ########################
####################################################

if __name__ == '__main__':

	if len(sys.argv)!=3:
		print 'Usage: python game_server <number of players> <PORT>'
		exit()

	# grab the number of players in this game
	player_count = int(sys.argv[1])
	GAME_PORT = int(sys.argv[2])
	player_range = range(player_count)

	# initialize gamespace and generate the player objects within game
	gs = GameSpace(player_range)

	# Listen for players to connect
	reactor.listenTCP(
		GAME_PORT,
		GameServerConnectionFactory(gs.players)
	)

	# initialize game loop
	lc = LoopingCall(gs.game_loop_iterate)
	lc.start(1.0/20)

	# begin reactor event loop
	reactor.run()

	# after reactor stops, end game loop
	lc.stop()

	# clean exit
	os._exit(0)
