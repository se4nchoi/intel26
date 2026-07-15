import numpy as np
import tensorflow as tf

(x_train, y_train), (x_test, y_test) = tf.keras.datasets.mnist.load_data()

# 7.1 전처리
x_train = x_train.astype(np.float32) / 255.0
x_test = x_test.astype(np.float32) / 255.0

x_train = x_train.reshape(-1, 28 * 28)
x_test = x_test.reshape(-1, 28 * 28)
# endof 7.1

# 7.2 모델 생성
model = tf.keras.Sequential([
    tf.keras.Input(shape=(784,)),
    tf.keras.layers.Dense(128, activation="relu"),
    tf.keras.layers.Dense(10, activation="softmax")
])

model.compile(
    optimizer="adam",
    loss="sparse_categorical_crossentropy",
    metrics=["accuracy"]
)
# endof 7.2

# 7.3 모델 학습
model.fit(
    x_train,
    y_train,
    epochs=5,
    batch_size=32,
    validation_split=0.1
)
# endof 7.3

# 7.4 모델 평가
test_loss, test_accuracy = model.evaluate(
    x_test,
    y_test,
    verbose=0
)
# endof 7.4

print("테스트 손실:", test_loss)
print("테스트 정확도:", test_accuracy)

# 7.5 모델 예측
probabilities = model.predict(
    x_test[:5],
    verbose=0
)

predicted_labels = np.argmax(
    probabilities,
    axis=1
)
# endof 7.5
print("실제 정답:", y_test[:5])
print("예측 결과:", predicted_labels)