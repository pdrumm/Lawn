import sys
import os
import pygame
from pygame.locals import *
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
		self.square = Square(self)
		receive.get().addCallback(self.receiveCallback)

	def main(self):
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
		self.screen.fill(self.black)
		self.screen.blit(self.square.image, self.square.rect)

		pygame.display.flip()

	def receiveCallback(self, data):
		print data
		center = [int(x) for x in data.spli(',')]
		#receive new center? Then set center
		self.square.rect.center = center
		receive.get().addCallback(self.receiveCallback)

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
		print "connection"
		self.gs = gs

	def connectionMade(self):
		print "connection made to", SERVER_HOST, "port", SERVER_PORT
		send.get().addCallback(self.sendCallback)

	def connectionLost(self, reason):
		print "connection lost to", SERVER_HOST, "port", SERVER_PORT

	def dataReceived(self, data):
		receive.put(data)

	def sendCallback(self, data):
		print data
		self.transport.write(data)
		send.get().addCallback(self.sendCallback)

class ServerConnFactory(ClientFactory):
	def __init__(self, gs):
		print "factory"
		self.gs = gs

	def buildProtocol(self, addr):
		print "here"
		return ServerConn(self.gs)

	def clientConnectionFailed(self, connector, reason):
		print "failed to connect to", SERVER_HOST, "port", SERVER_PORT

if __name__ == '__main__':
	gs = GameSpace()
	reactor.connectTCP(SERVER_HOST, SERVER_PORT, ServerConnFactory(gs))
	lc = LoopingCall(gs.main)
	lc.start(2)
	reactor.run()
	lc.stop()
