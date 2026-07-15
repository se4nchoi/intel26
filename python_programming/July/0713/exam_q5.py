import numpy as np
import tensorflow as tf

# 결과 재현을 위한 난수 시드 고정
tf.keras.utils.set_random_seed(42)

# MNIST 손글씨 숫자 데이터 불러오기
(x_train, y_train), (x_test, y_test) = tf.keras.datasets.mnist.load_data()

# 픽셀 값을 0~255 범위에서 0~1 범위로 정규화
x_train = x_train.astype(np.float32) / 255.0
x_test = x_test.astype(np.float32) / 255.0

# Conv2D 입력 형식에 맞게 채널 차원 추가
# 기존 shape: (데이터 수, 28, 28)
# 변경 shape: (데이터 수, 28, 28, 1)
x_train = np.expand_dims(x_train, axis=-1)
x_test = np.expand_dims(x_test, axis=-1)

# CNN 모델 생성
model = tf.keras.Sequential([
    # 입력 이미지: 28 x 28 크기의 흑백 이미지 1채널
    tf.keras.Input(shape=(28, 28, 1)),

    # 32개의 필터를 사용하여 기본적인 이미지 특징 추출
    tf.keras.layers.Conv2D(
        filters=32,
        kernel_size=(3, 3),
        activation="relu"
    ),

    # 2 x 2 영역에서 가장 큰 값을 남겨 feature map 크기 축소
    tf.keras.layers.MaxPooling2D(
        pool_size=(2, 2)
    ),

    # 64개의 필터를 사용하여 더 복잡한 특징 추출
    tf.keras.layers.Conv2D(
        filters=64,
        kernel_size=(3, 3),
        activation="relu"
    ),

    # 다차원 feature map을 1차원 벡터로 변환
    tf.keras.layers.Flatten(),

    # 추출된 특징을 조합하는 128개 뉴런의 은닉층
    tf.keras.layers.Dense(
        units=128,
        activation="relu"
    ),

    # 숫자 0~9에 대응하는 10개 클래스 출력
    # Softmax를 사용해 각 클래스의 확률 계산
    tf.keras.layers.Dense(
        units=10,
        activation="softmax"
    )
])

# 모델 학습 설정
model.compile(
    optimizer="adam",
    loss="sparse_categorical_crossentropy",
    metrics=["accuracy"]
)

# 모델 구조 출력
model.summary()

# 모델 학습
model.fit(
    x_train,
    y_train,
    epochs=5,
    batch_size=64,
    validation_split=0.1
)

# 테스트 데이터로 정확도 평가
test_loss, test_accuracy = model.evaluate(
    x_test,
    y_test,
    verbose=0
)

print("\n테스트 손실:", test_loss)
print("테스트 정확도:", test_accuracy)

# 테스트 이미지 5개 예측
sample_images = x_test[:5]
sample_labels = y_test[:5]

# 각 이미지에 대한 10개 클래스 확률
probabilities = model.predict(
    sample_images,
    verbose=0
)

# 가장 높은 확률을 가진 클래스 선택
predicted_labels = np.argmax(
    probabilities,
    axis=1
)

print("\n실제 정답:", sample_labels)
print("예측 결과:", predicted_labels)

# 첫 번째 이미지의 클래스별 확률 출력
print("\n첫 번째 이미지의 클래스별 확률:")
for class_number, probability in enumerate(probabilities[0]):
    print(f"숫자 {class_number}: {probability:.6f}")

print(
    "확률 합:",
    np.sum(probabilities[0])
)