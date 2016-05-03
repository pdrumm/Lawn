import sys
import os
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
import math

SERVER_HOST = 'student03.cse.nd.edu'
SERVER_PORT = 40091
GAME_HOST = ''
GAME_PORT = 40091

match_send = DeferredQueue()
match_receive = DeferredQueue()
game_send = DeferredQueue()
game_receive = DeferredQueue()

class GameSpace(object):
	def __init__(self):
		pygame.init()
		self.size = self.width, self.height = (640, 480)
		self.screen = pygame.display.set_mode(self.size)
		self.player_mowers = []
		self.player_shadows = []
		self.curr_shadow = None
		match_receive.get().addCallback(self.match_receiveCallback)
		self.tick = 0# tick regulation variable
		self.flip_rate = 30
		self.dir = 0#direction that player i facing
		self.ready = False#boolean for if game is starting
		self.num_players = 0#number of players in game
		#possible ghost images
		self.ghosts = ["images/red_grass.png", "images/blue_grass.png", "images/purple_grass.png", "images/orange_grass.png"]
		#possible mower images
		self.mowers = ["images/red_mower.png", "images/blue_mower.png", "images/purple_mower.png", "image/orange_mower.png"]
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

	def main(self):
		self.tick = (self.tick+1)%self.flip_rate
		#user input
		for event in pygame.event.get():
			if event.type == QUIT:
				reactor.stop()
			elif self.ready:
				if event.type == KEYDOWN:
					if event.key == K_UP:
						game_send.put("up")
					elif event.key == K_DOWN:
						game_send.put("down")
					elif event.key == K_LEFT:
						game_send.put("left")
					elif event.key == K_RIGHT:
						game_send.put("right")
			else:
				if event.type == KEYDOWN:
					if event.key == K_r:
						match_send.put("ready")

		#display game objects
		self.screen.blit(self.background.image, self.background.rect)
		if not self.ready:
			#display loading screen
			self.screen.blit(self.title.image, self.title.rect)
			#statu text
			text1 = self.font.render("Players Ready: {0}/{1}".format(self.players_ready, self.num_players), True, (0, 0, 0))
			text1pos = text1.get_rect(center = (self.width/2, self.height/2+50))
			text2 = self.font.render("Game starting in {0} seconds...".format(self.countdown), True, (0, 0, 0))
			text2pos = text2.get_rect(center = (self.width/2, self.height/2+90))
			self.screen.blit(text1, text1pos)
			self.screen.blit(text2, text2pos)
		else:
			#display game
			if len(self.player_shadows) > 0:
			# update does not have the overhead of flip b/c it only blits the args, not the entire page
				for player in self.player_shadows:
					player.draw(self.screen)
				for player in self.player_mowers:
					self.screen.blit(player.image, player.rect)
			if self.win:
				self.screen.blit(self.win_screen.image, self.win_screen,rect) 
			elif not self.alive:
				self.screen.blit(self.game_over.image, self.game_over.rect)
		pygame.display.flip()
		# else:
			# pygame.display.update(self.Image)

	def game_receiveCallback(self, data):
		#receive new center
		try:
			new_state = pickle.loads(data)
		except:
			game_receive.get().addCallback(self.game_receiveCallback)
			return
		#create new Image sprite with that center
		for i in xrange(self.num_players):
			self.curr_shadow = Image(self.ghosts[i], [new_state[i]['center'][0], new_state[i]['center'][1]], self)
		#update center of player
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
			dead_players = 0
			if new_state[i]['alive'] == False:
				dead_players += 1
				if i == self.player_number:
					self.alive = False
				elif dead_players == self.num_players - 1 and self.alive:
					self.win = True
		game_receive.get().addCallback(self.game_receiveCallback)

	def match_receiveCallback(self, data):
		try:
			new_state = pickle.loads(data)
		except:
			match_receive.get().addCallback(self.match_receiveCallback)

		#update seconds, number of players, and ready players
		self.num_players = new_state['Players Total']
		if not new_state['Begin Game']:
			self.players_ready = new_state['Players Ready']
			self.countdown = new_state['Time Left']

		else:
			#if time to play, connect to game server
			GAME_HOST = new_state['Host']
			GAME_PORT = new_state['Port']
			reactor.connectTCP(GAME_HOST, GAME_PORT, GameConnFactory(self))
			game_receive.get().addCallback(self.game_receiveCallback)
			self.player_number = new_state['Player Number']
			self.make_players()

	def make_players(self):
		for i in xrange(self.num_players):
			self.player_mowers.append(Mower(self.mowers[i], [-100, -100], self))
			self.player_shadows.append(pygame.sprite.Group())

		self.ready = True

class Mower(pygame.sprite.Sprite):
	def __init__(self, img_file, center, gs=None):
		pygame.sprite.Sprite.__init__(self)
		self.gs = gs
		self.original_image = pygame.image.load(img_file)
		self.image = self.original_image
		self.rect = self.image.get_rect()
		# print center
		self.rect.center = center

	def rot_center(self, image, angle):
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
		self.original_image = pygame.image.load(img_file)
		self.image = self.original_image
		self.rect = self.image.get_rect()
		# print center
		self.rect.center = center

class MatchmakingConn(Protocol):
	def __init__(self, gs):
		print 'connection init'
		self.gs = gs

	def connectionMade(self):
		print "connection made to", SERVER_HOST, "port", SERVER_PORT
		match_send.get().addCallback(self.match_sendCallback)

	def connectionLost(self, reason):
		print "connection lost to", SERVER_HOST, "port", SERVER_PORT
		try:
			reactor.stop()
		except:
			pass

	def dataReceived(self, data):
		# if not self.gs.ready:
		# 	unpack = pickle.loads(data)
		# 	self.gs.num_players = unpack['Player Count']
		# 	self.gs.player_number = unpack['Player Number']
		# 	self.gs.make_players()
		# else:
		match_receive.put(data)

	def match_sendCallback(self, data):
		self.transport.write(data)
		match_send.get().addCallback(self.match_sendCallback)

class MatchmakingConnFactory(ClientFactory):
	def __init__(self, gs):
		self.gs = gs
		print 'factory init'

	def buildProtocol(self, addr):
		print 'factory buildprotocol'
		return MatchmakingConn(self.gs)

	def clientConnectionFailed(self, connector, reason):
		print "failed to connect to", SERVER_HOST, "port", SERVER_PORT
		# reactor.stop()

class GameConn(Protocol):
	def __init__(self, gs):
		self.gs = gs

	def connectionMade(self):
		print "connection made to game server"
		#tell game server your player number
		self.transport.write(self.gs.player_number)


	def connecitonLost(self, reason):
		print "connection lost to game server"
		try:
			reactor.stop()
		except:
			pass

	def dataReceived(self, data):
		game_receive.put(data)


class GameConnFactory(ClientFactory):
	def __init__(self, gs):
		self.gs = gs

	def buildProtocol(self, addr):
		return GameConn(self.gs)

	def clientConnectionFailed(self, connector, reason):
		print "failed to connect to game server"
		# reactor.stop()

if __name__ == '__main__':
	print 'Initializing pygame Gamespace...'
	gs = GameSpace()
	print 'Initializing twisted connection...'
	reactor.connectTCP(SERVER_HOST, SERVER_PORT, MatchmakingConnFactory(gs))
	lc = LoopingCall(gs.main)
	lc.start(1.0/20)
	reactor.run()
	lc.stop()
