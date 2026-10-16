import tensorflow as tf
import numpy as np
import matplotlib.pyplot as plt

mnist = tf.keras.datasets.mnist
(image_train, label_train), (image_test, label_test) = mnist.load_data()
print(image_train.shape, label_train.shape)
print(image_test.shape, label_test.shape)

COLS, ROWS = 3,2
OFFSET = 0

figure = plt.figure()
font_settings = {'fontsize': 12, 'color': 'darkblue'}

for i in range(OFFSET, ROWS*COLS + OFFSET):
    image = image_train[i]
    label = label_train[i]
    figure.add_subplot(ROWS, COLS, i - OFFSET + 1)
    plt.title(f'Label is [{label}]', fontdict=font_settings)
    plt.imshow(image)
plt.show(0)