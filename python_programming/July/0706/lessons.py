class TeleVision:
  serial_num = 0  # class variable
  def __init__(self, channel, volume, on):
    # total instance* variables ? = 4
    TeleVision.serial_num += 1
    self.serial_num = TeleVision.serial_num
    self.channel = channel
    self.volume = volume    
    self.on = on
    
  def __str__(self):
    return f"TV({'On' if self.on else 'Off'}, Volume: {self.volume}, Channel: {self.channel}, Serial Number: {self.serial_num})"
  
  

class Rectangle:
  def __init__(self, width, height):
    self.width = width
    self.height = height
    
  def area(self):
    return self.width * self.height
  
  
  def __add__(self, other):
    new_width = self.width + other.width
    new_height = self.height + other.height
    return Rectangle(new_width, new_height)
  
  def __str__(self):
    return f"Rectangle(Width: {self.width}, Height: {self.height})"
  