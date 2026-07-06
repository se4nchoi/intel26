class Car:
  def __init__(self, speed, color, model):
    self.speed = speed
    self.color = color
    self.model = model
  def set_speed(self, speed):
    self.speed = speed
  def get_speed(self):
    return self.speed
  
  def __str__(self):
    return f"Car - Model: {self.model}, Color: {self.color}, Speed: {self.speed}"
  

C1 = Car(100, "White", "Kia EV6")
C2 = Car(150, "Black", "Tesla Model S")
print(C1)
print(C2)