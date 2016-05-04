import sys
import os
import time
try:
	import cPickle as pickle
except:
	import pickle
import pygame
from pygame.locals import *
# Twisted
from twisted.internet.protocol import Protocol, ClientFactory
from twisted.internet import reactor
from twisted.internet.defer import DeferredQueue
from twisted.internet.task import LoopingCall

#matchmaking host and port
SERVER_HOST = 'student03.cse.nd.edu'
SERVER_PORT = 40091
#game server host and port - provided by matchmaking server
GAME_HOST = ''
GAME_PORT = 40091

#deferred queues for the various paths of communication
match_send = DeferredQueue()
match_receive = DeferredQueue()
game_send = DeferredQueue()
game_receive = DeferredQueue()

class GameSpace(object):
	def __init__(self):
		pygame.init()
		self.size = self.width, self.height = (640, 480)
		self.screen = pygame.display.set_mode(self.size)
		#list of mowers assigned to each layer
		self.player_mowers = []
		#list of shadows assigned to each player
		self.player_shadows = []
		self.curr_shadow = None
		#add callback for data coming from matchmaking server
		match_receive.get().addCallback(self.match_receiveCallback)
		self.tick = 0# tick regulation variable
		self.dir = 0#direction that player i facing
		self.ready = False#boolean for if game is starting
		self.num_players = 0#number of players in game
		#possible ghost images
		self.ghosts = ["images/red_grass.png", "images/blue_grass.png", "images/purple_grass.png", "images/orange_grass.png"]
		#possible mower images
		self.mowers = ["images/red_mower.png", "images/blue_mower.png", "images/purple_mower.png", "images/orange_mower.png"]
		#title screen image
		self.title = Image("images/title.png", [self.width/2, self.height/2], self)
		#grass background image
		self.background = Image("images/grass_background.png", [self.width/2, self.height/2], self)
		self.alive = True#boolean for if you are alive
		#game over screen image
		self.game_over = Image("images/gameover.png", [self.width/2, self.height/2], self)
		#win screen image
		self.win_screen = Image("images/win.png", [self.width/2, self.height/2], self)
		self.player_number = 0#your player number
		self.players_ready = 0#number of players ready to play
		self.countdown = 100#seconds until game starts
		self.font = pygame.font.Font(None, 30)#font object for dynamic text
		self.win = False#boolean for if you have won
		self.start = False#boolean for if game is about to start
		self.offset = 30#offset used for computing initial position of players
		self.offsets = []#list of offsets for each player
		self.dirs = []#direction for each player

	def main(self):
		self.tick = (self.tick+1)

		#user input
		for event in pygame.event.get():
			if event.type == QUIT:
				reactor.stop()
			elif self.ready:#game has started
				if event.type == KEYDOWN:
					if event.key == K_UP:
						data = pickle.dumps({"Key": "up"})
						game_send.put(data)
					elif event.key == K_DOWN:
						data = pickle.dumps({"Key": "down"})
						game_send.put(data)
					elif event.key == K_LEFT:
						data = pickle.dumps({"Key": "left"})
						game_send.put(data)
					elif event.key == K_RIGHT:
						data = pickle.dumps({"Key": "right"})
						game_send.put(data)
			else:#if game is not ready to start
				if event.type == KEYDOWN:
					if event.key == K_r:
						match_send.put("ready")

		#display game objects
		if not self.start:#game is in title screen or in play
			self.screen.blit(self.background.image, self.background.rect)
		else:#game is getting ready to start
			self.screen.fill((0, 0, 0))#fill black
		if not self.ready:#title screen
			#display loading screen
			self.screen.blit(self.title.image, self.title.rect)
			#status text - players ready
			text1 = self.font.render("Players Ready: {0}/{1}".format(self.players_ready, self.num_players), True, (0, 0, 0))
			text1pos = text1.get_rect(center = (self.width/2, self.height/2+50))
			#status text of time until game starts or waiting
			if self.num_players <= 1:
				text2 = self.font.render("Waiting for more players...", True, (0, 0, 0))
			else:
				text2 = self.font.render("Game starting in {0} seconds...".format(self.countdown), True, (0, 0, 0))
			text2pos = text2.get_rect(center = (self.width/2, self.height/2+90))
			self.screen.blit(text1, text1pos)
			self.screen.blit(text2, text2pos)
		elif self.start:#if game about to start
			#tell player game is loading
			text = self.font.render("Loading...", True, (255, 255, 255))
			textpos = text.get_rect(center = (self.width/2, self.height/2))
			self.screen.blit(text, textpos)
			#get initial placement of player on screen and display
			#this is done so the user knows their color and starting position
			self.initial_placement()
			self.screen.blit(self.player_mowers[self.player_number].image, self.player_mowers[self.player_number].rect)
		else:#game i being played
			#display game
			if len(self.player_shadows) > 0:
			# update does not have the overhead of flip b/c it only blits the args, not the entire page
				for player in self.player_shadows:
					player.draw(self.screen)
				for player in self.player_mowers:
					self.screen.blit(player.image, player.rect)
			if self.win:
				self.screen.blit(self.win_screen.image, self.win_screen.rect) 
			elif not self.alive:
				self.screen.blit(self.game_over.image, self.game_over.rect)

		if self.start:#if game is about to start
			pygame.display.flip()#diplay new items
			time.sleep(3)#sleep to allow time for game server to start
			#connect to game server
			reactor.connectTCP(GAME_HOST, GAME_PORT, GameConnFactory(self))
			self.start = False#set start to false to game will begin
		else:
			pygame.display.flip()

	def game_receiveCallback(self, data):
		#receive new data
		try:
			new_state = pickle.loads(data)#try to load data
		except:
			#if data was not able to load
			game_receive.get().addCallback(self.game_receiveCallback)
			return
		#create new Image sprite with new center
		dead_players = 0
		for i in xrange(self.num_players):
			self.curr_shadow = Image(self.ghosts[i], [new_state[i]['center'][0], new_state[i]['center'][1]], self)
		#update center of player and direction
			if new_state[i]['direction'] == 'R':
				self.dir = 0
			elif new_state[i]['direction'] == 'L':
				self.dir = 2
			elif new_state[i]['direction'] == 'U':
				self.dir = 1
			elif new_state[i]['direction'] == 'D':
				self.dir = 3
			self.player_mowers[i].rect.center = [new_state[i]['center'][0], new_state[i]['center'][1]]
			self.player_mowers[i].image = self.player_mowers[i].rot_center(self.player_mowers[i].original_image, 90*self.dir)
		#add new sprite to group
			self.player_shadows[i].add(self.curr_shadow)
			#check if any players have lost
			if new_state[i]['alive'] == False:
				dead_players += 1
				if i == self.player_number:
					self.alive = False
				elif dead_players == self.num_players - 1 and self.alive:#if everyone but you is dead, you win
					self.win = True
		game_receive.get().addCallback(self.game_receiveCallback)

	def match_receiveCallback(self, data):
		global GAME_HOST, GAME_PORT
		try:#try to load new data
			new_state = pickle.loads(data)
		except:
			match_receive.get().addCallback(self.match_receiveCallback)

		#update seconds, number of players, and ready players
		self.num_players = new_state['Players Total']#set total number of players connected
		if not new_state['Begin Game']:#if game is not beginning
			self.players_ready = new_state['Players Ready']#set number of ready players
			self.countdown = new_state['Time Left']#update time until game begins

		else:
			#if time to play, set host and port received
			GAME_HOST = new_state['Host']
			GAME_PORT = new_state['Port']
			game_receive.get().addCallback(self.game_receiveCallback)
			self.player_number = new_state['Player Number']#st your player number
			self.start = True#start to true so game will begin
			self.make_players()#create player arrays

		match_receive.get().addCallback(self.match_receiveCallback)

	def make_players(self):
		for i in xrange(self.num_players):
			self.player_mowers.append(Mower(self.mowers[i], [-100, -100], self))
			self.player_shadows.append(pygame.sprite.Group())

		self.ready = True

	def initial_placement(self):
		self.dirs = [0,2,3,1]#possible orientations of players
		#starting position of each player on screen
		self.offsets = [(self.offset,self.height/2),(self.width-self.offset,self.height/2),(self.width/2,self.offset),(self.width/2,self.height-self.offset)]

		#rotate this clients player to proper orientation and set position
		self.dir = self.dirs[self.player_number]
		self.player_mowers[self.player_number].image = self.player_mowers[self.player_number].rot_center(self.player_mowers[self.player_number].original_image, 90*self.dir)
		x = self.offsets[self.player_number][0]
		y = self.offsets[self.player_number][1]
		self.player_mowers[self.player_number].rect.center = [x, y]

class Mower(pygame.sprite.Sprite):
	def __init__(self, img_file, center, gs=None):
		pygame.sprite.Sprite.__init__(self)
		self.gs = gs
		self.original_image = pygame.image.load(img_file)#save original image
		self.image = self.original_image
		self.rect = self.image.get_rect()
		self.rect.center = center#set center as argument passed in

	def rot_center(self, image, angle):
		#function to rotate image to proper orientation
		orig_rect = image.get_rect()
		rot_image = pygame.transform.rotate(image, angle)
		rot_rect = orig_rect.copy()
		rot_rect.center = rot_image.get_rect().center
		rot_image = rot_image.subsurface(rot_rect).copy()
		return rot_image

class Image(pygame.sprite.Sprite):
	def __init__(self, img_file, center, gs=None):
		pygame.sprite.Sprite.__init__(self)
		self.gs = gs
		self.original_image = pygame.image.load(img_file)#save original image
		self.image = self.original_image
		self.rect = self.image.get_rect()
		self.rect.center = center

class MatchmakingConn(Protocol):
	def __init__(self, gs):
		#connection to matchmaking server
		self.gs = gs

	def connectionMade(self):
		print "matchmaking: connection made to", SERVER_HOST, "port", SERVER_PORT
		match_send.get().addCallback(self.match_sendCallback)

	def connectionLost(self, reason):
		print "matchmaking: connection lost to", SERVER_HOST, "port", SERVER_PORT

	def dataReceived(self, data):
		match_receive.put(data)#put data on queue from matchmaking server

	def match_sendCallback(self, data):
		self.transport.write(data)#send data to matchmaking server
		match_send.get().addCallback(self.match_sendCallback)

class MatchmakingConnFactory(ClientFactory):
	def __init__(self, gs):
		self.gs = gs

	def buildProtocol(self, addr):
		return MatchmakingConn(self.gs)

	def clientConnectionFailed(self, connector, reason):
		print "matchmaking: failed to connect to", SERVER_HOST, "port", SERVER_PORT

class GameConn(Protocol):
	def __init__(self, gs):
		self.gs = gs

	def connectionMade(self):
		print "connection made to game server"
		#tell game server your player number
		data = pickle.dumps({'Player Number': self.gs.player_number})
		self.transport.write(data)
		game_send.get().addCallback(self.game_sendCallback)

	def connectionLost(self, reason):
		print "connection lost to game server"
		try:#try to stop reactor after game ends. done incase reactor is already stopped for some reason
			reactor.stop()
		except:
			pass

	def dataReceived(self, data):
		game_receive.put(data)

	def game_sendCallback(self, data):
		self.transport.write(data)
		game_send.get().addCallback(self.game_sendCallback)

class GameConnFactory(ClientFactory):
	def __init__(self, gs):
		self.gs = gs

	def buildProtocol(self, addr):
		return GameConn(self.gs)

	def clientConnectionFailed(self, connector, reason):
		print "failed to connect to game server"
		reactor.stop()

if __name__ == '__main__':
	print 'Initializing pygame Gamespace...'
	gs = GameSpace()
	print 'Initializing twisted connection...'
	reactor.connectTCP(SERVER_HOST, SERVER_PORT, MatchmakingConnFactory(gs))
	lc = LoopingCall(gs.main)
	lc.start(1.0/20)
	reactor.run()
	lc.stop()
