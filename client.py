import sys
import os
import pygame
from pygame.locals import *
from twisted.internet.protocol import Protocol, ClientFactory
from twisted.internet import reactor
# from twisted.internet.defer import DeferredQueue
from twisted.internet.task import LoopingCall

SERVER_HOST = 'student0x.cse.nd.edu'
SERVER_PORT = 41091

class GameSpace(object):
	def __init__(self):
		pygame.init()
		self.size = self.width, self.height = (640, 480)
		self.black = (0, 0, 0)
		self.screen = pygame.display.set_mode(self.size)
		self.square = Square(self)

	def main(self):
		#display game objects
		self.screen.fill(self.black)
		self.screen.blit(self.square.image, self.square.rect)

		pygame.display.flip()

class Square(pygame.sprite.Sprite):
	def __init__(self, gs=None):
		self.gs = gs
		self.image = pygame.image.load("laser.png")
		self.rect = self.image.get_rect()
		self.rect.center = [100, 100]

	def tick(self):
		pass

class ServerConn(Protocol):
	def __init__(self, gs):
		self.gs = gs

	def connectionMade(self):
		print "connection made to", SERVER_HOST, "port", SERVER_PORT

	def connectionLost(self, reason):
		print "connection lost to", SERVER_HOST, "port", SERVER_PORT

class ServerConnFactory(ClientFactory):
	def __init__(self, gs):
		self.gs = gs

	def buildProtocl(self):
		return ServerConn(self.gs)

	def clientConnectionFailed(self, connector, reason):
		print "failed to connect to", SERVER_HOST, "port", SERVER_PORT

if __name__ == '__main__':
	gs = GameSpace()
	lc = LoopingCall(gs.main)
	lc.start(1.0/60)
	reactor.connectTCP(SERVER_HOST, SERVER_PORT, ServerConnFactory(gs))
	reactor.run()
	lc.stop()
