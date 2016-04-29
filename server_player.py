class Player:
	"""This class represents an instance of a player in the game."""

	# Attributes
	# Players' server connection
	server_conn = None

	# Set speed vector of player
	(x,y) = (0,0)
	(dx,dy) = (0,0)
	speed = 1

	# What direction is the player facing?
	direction = "R"

	def __init__(self):
		pass

	def update(self):
		# Move left/right
		self.x += self.dx
		# Move up/down
		self.y += self.dy

	def update_dir(self,dir):
		"""Called when the user hits an arrow key."""
		if dir == "up":
			self.direction = "U"
			self.dx = 0
			self.dy = -1*speed
		elif dir == "down":
			self.direction = "D"
			self.dx = 0
			self.dy = 1*speed
		elif dir == "left":
			self.direction = "L"
			self.dx = -1*speed
			self.dy = 0
		elif dir == "right":
			self.direction = "R"
			self.dx = 1*speed
			self.dy = 0
