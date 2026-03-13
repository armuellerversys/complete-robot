import time
from matrix_text import Matrix
import random

matrix = Matrix()

for i in range(10):
    text = "Hi-" + str(random.randint(0, 9))
    print(f"Show text: {text}")
    matrix.show_text(text)
    time.sleep(3)