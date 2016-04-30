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

SERVER_HOST = 'student02.cse.nd.edu'
SERVER_PORT = 40755

send = DeferredQueue()
receive = DeferredQueue()

class GameSpace(object):
	def __init__(self):
		pygame.init()
		self.size = self.width, self.height = (640, 480)
		self.black = (0, 0, 0)
		self.screen = pygame.display.set_mode(self.size)
		self.square = Square("lawnmower.png",self)
		self.shadow = Square("laser.png",self)
		receive.get().addCallback(self.receiveCallback)
		# tick regulation variable
		self.tick = 0
		self.flip_rate = 30

	def main(self):
		self.tick = (self.tick+1)%self.flip_rate
		#user input
		for event in pygame.event.get():
			if event.type == QUIT:
				reactor.stop()
			elif event.type == KEYDOWN:
				if event.key == K_UP:
					send.put("up")
				elif event.key == K_DOWN:
					send.put("down")
				elif event.key == K_LEFT:
					send.put("left")
				elif event.key == K_RIGHT:
					send.put("right")

		#display game objects
#		self.screen.fill(self.black)
		self.screen.blit(self.shadow.image, self.shadow.rect)
		self.screen.blit(self.square.image, self.square.rect)
		print '({x},{y})'.format(x=self.square.rect.x,y=self.square.rect.y)

		# update does not have the overhead of flip b/c it only blits the args, not the entire page
		if self.tick == 0:
			pygame.display.flip()
		else:
			pygame.display.update(self.square)

	def receiveCallback(self, data):
		center = pickle.loads(data)
#		center = [int(x) for x in data.split(',')]
		#receive new center? Then set center
		self.shadow.rect.center = self.square.rect.center
		self.square.rect.center = [center[0], center[1]]
		receive.get().addCallback(self.receiveCallback)

class Square(pygame.sprite.Sprite):
	def __init__(self, img_file, gs=None):
		self.gs = gs
		self.image = pygame.image.load(img_file)
		self.rect = self.image.get_rect()
		self.rect.center = [100, 100]

	def tick(self):
		pass

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

if __name__ == '__main__':
	print 'Initializing pygame Gamespace...'
	gs = GameSpace()
	print 'Initializing twisted connection...'
	reactor.connectTCP(SERVER_HOST, SERVER_PORT, ServerConnFactory(gs))
	lc = LoopingCall(gs.main)
	lc.start(1.0/60)
	reactor.run()
	lc.stop()
