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

#SERVER_HOST = 'student02.cse.nd.edu'
SERVER_HOST = 'student01.cse.nd.edu'
SERVER_PORT = 40091

send = DeferredQueue()
receive = DeferredQueue()

class GameSpace(object):
	def __init__(self):
		pygame.init()
		self.size = self.width, self.height = (640, 480)
		self.black = (0, 0, 0)
		self.screen = pygame.display.set_mode(self.size)
		# self.square = Square("temp.png", [-100, -100], self)
		#self.shadow = Square("laser.png",self)
		self.player_mowers = []
		self.player_shadows = []
		# self.shadow = pygame.sprite.Group()
		self.curr_shadow = None
		receive.get().addCallback(self.receiveCallback)
		# tick regulation variable
		self.tick = 0
		self.flip_rate = 30
		self.dir = 0
		self.ready = False
		self.num_players = 0

	def main(self):
		if not self.ready:
			self.screen.fill((255, 0, 0))
		else:
			self.tick = (self.tick+1)%self.flip_rate
			#user input
			for event in pygame.event.get():
				if event.type == QUIT:
					reactor.stop()
				elif event.type == KEYDOWN:
					if event.key == K_UP:
						send.put("up")
						self.dir = 1
					elif event.key == K_DOWN:
						send.put("down")
						self.dir = 3
					elif event.key == K_LEFT:
						send.put("left")
						self.dir = 2
					elif event.key == K_RIGHT:
						send.put("right")
						self.dir = 0

			#display game objects
			self.screen.fill(self.black)
			if len(self.player_shadows > 0):
			# if len(self.shadow.sprites()) > 0:
				# self.screen.blit(self.curr_shadow.image, self.curr_shadow.rect)
			# self.screen.blit(self.square.image, self.square.rect)
	#		print '({x},{y})'.format(x=self.square.rect.x,y=self.square.rect.y)

			# update does not have the overhead of flip b/c it only blits the args, not the entire page
			# if self.tick == 0:
				for player in self.player_shadows:
					player.draw(self.screen)
				for player in self.player_mowers:
					self.screen.blit(player.image, player.rect)
		pygame.display.flip()
		# else:
			# pygame.display.update(self.square)

	def receiveCallback(self, data):
		#receive new center
		center = pickle.loads(data)
		#create new square sprite with that center
		for i in xrange(self.num_players):
			self.curr_shadow = Square("laser_original.png", [center[0], center[1]], self)
		#update center of player
			self.player_mowers[i].rect.center = [center[i][0], center[i][1]]
			self.player_mowers[i].image = self.square.rot_center(self.square.original_image, 90*self.dir)
		#add new sprite to group
			self.player_shadows[i].add(self.curr_shadow)
		receive.get().addCallback(self.receiveCallback)

	def make_players(self):
		for i in xrange(self.num_players):
			self.player_mowers.append(Square("temp.png", [-100, -100], self))
			self.player_shadows.append(pygame.sprite.Group())

		self.ready = True

class Square(pygame.sprite.Sprite):
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

class ServerConn(Protocol):
	def __init__(self, gs):
		print 'connection init'
		self.gs = gs

	def connectionMade(self):
		print "connection made to", SERVER_HOST, "port", SERVER_PORT
		send.get().addCallback(self.sendCallback)

	def connectionLost(self, reason):
		print "connection lost to", SERVER_HOST, "port", SERVER_PORT

	def dataReceived(self, data):
		if not self.gs.ready:
			unpack = pickle.loads(data)
			for key in unpack.keys():
				self.gs.num_players = unpack[key]
				self.gs.make_players()
		else:
			receive.put(data)

	def sendCallback(self, data):
		self.transport.write(data)
		send.get().addCallback(self.sendCallback)

class ServerConnFactory(ClientFactory):
	def __init__(self, gs):
		self.gs = gs
		print 'factory init'

	def buildProtocol(self, addr):
		print 'factory buildprotocol'
		return ServerConn(self.gs)

	def clientConnectionFailed(self, connector, reason):
		print "failed to connect to", SERVER_HOST, "port", SERVER_PORT
		reactor.stop()

if __name__ == '__main__':
	print 'Initializing pygame Gamespace...'
	gs = GameSpace()
	print 'Initializing twisted connection...'
	reactor.connectTCP(SERVER_HOST, SERVER_PORT, ServerConnFactory(gs))
	lc = LoopingCall(gs.main)
	lc.start(1.0/60)
	reactor.run()
	lc.stop()
