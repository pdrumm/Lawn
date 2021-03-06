class Player:
	"""This class represents an instance of a player in the game."""

	# Attributes
	# Players' server connection
	server_conn = None
	queue_len = 0

	# Set speed vector of player
	(x,y) = (0,0)
	(dx,dy) = (0,0)
	speed = 3

	# What direction is the player facing?
	direction = ""

	# screen vars
	(screen_w, screen_h) = (640,480)
	screen_offset = 30
	sprite_radius = 6

	# is the player still alive in the game?
	is_alive = True

	def __init__(self,pNum):
		"""When initialized, the player is updated with its starting position on the screen and initial velocity. This is reflected when the game starts and all players start at different edges, but all move towards the center."""
		# set initial arrays for respective players and assign values accordingly
		directions = ["R","L","D","U"]
		starting_pos = [(self.screen_offset,self.screen_h/2),(self.screen_w-self.screen_offset,self.screen_h/2),(self.screen_w/2,self.screen_offset),(self.screen_w/2,self.screen_h-self.screen_offset)]
		velocity = [(self.speed,0),(-1*self.speed,0),(0,self.speed),(0,-1*self.speed)]
		# assign the player it's initial values based off of the player's Player Number
		self.direction = directions[pNum]
		self.x = starting_pos[pNum][0]
		self.y = starting_pos[pNum][1]
		self.dx = velocity[pNum][0]
		self.dy = velocity[pNum][1]

	def update(self):
		"""Use the player's velocity to update its x,y position on the screen."""
		# Move left/right
		self.x += self.dx
		# Move up/down
		self.y += self.dy

	def update_dir(self,dir):
		"""Called when the user hits an arrow key. This method simply updates the orientation of the player as well as their directional velocity."""
		if dir == "up":
			if self.direction != "D":
				self.direction = "U"
				self.dx = 0
				self.dy = -1*self.speed
		elif dir == "down":
			if self.direction != "U":
				self.direction = "D"
				self.dx = 0
				self.dy = 1*self.speed
		elif dir == "left":
			if self.direction != "R":
				self.direction = "L"
				self.dx = -1*self.speed
				self.dy = 0
		elif dir == "right":
			if self.direction != "L":
				self.direction = "R"
				self.dx = 1*self.speed
				self.dy = 0

	def is_out_of_bounds(self):
		"""This method returns true if the player's x,y position is not within the bounds of the screen."""
		is_ob = False
		if self.x < 0 + self.sprite_radius or self.x > self.screen_w - self.sprite_radius:
			is_ob = True
		elif self.y < 0 + self.sprite_radius or self.y > self.screen_h - self.sprite_radius:
			is_ob = True
		return is_ob
