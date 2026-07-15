import numpy as np
import tensorflow as tf

# 학습 데이터: 샘플 5개, 각 샘플에 입력 특성 1개
x_train = np.array(
    [1, 2, 3, 4, 5],
    dtype=np.float32
).reshape(-1, 1)

y_train = np.array(
    [3, 6, 9, 12, 15],
    dtype=np.float32
).reshape(-1, 1)

# 테스트 데이터: 샘플 3개, 각 샘플에 입력 특성 1개
x_test = np.array(
    [6, 7, 8],
    dtype=np.float32
).reshape(-1, 1)


def train_and_evaluate(epochs):
    """지정한 epoch만큼 선형 회귀 모델을 학습하고 결과를 반환한다."""

    # 두 모델이 동일한 초기 가중치에서 시작하도록 시드를 고정
    tf.keras.utils.set_random_seed(42)

    # 입력값 하나를 받아 출력값 하나를 생성하는 선형 회귀 모델
    model = tf.keras.Sequential([
        tf.keras.Input(shape=(1,)),
        tf.keras.layers.Dense(1)
    ])

    # Adam optimizer와 평균제곱오차 손실 함수 설정
    model.compile(
        optimizer="adam",
        loss="mse"
    )

    # 모델 학습
    history = model.fit(
        x_train,
        y_train,
        epochs=epochs,
        verbose=0
    )

    # 테스트 데이터 예측
    predictions = model.predict(
        x_test,
        verbose=0
    ).flatten()

    # Dense 층이 학습한 가중치와 편향 추출
    weight, bias = model.layers[0].get_weights()

    return {
        "epochs": epochs,
        "predictions": predictions,
        "loss": history.history["loss"][-1],
        "weight": weight[0][0],
        "bias": bias[0]
    }


# 20 epochs와 300 epochs 모델을 각각 학습
result_20 = train_and_evaluate(20)
result_300 = train_and_evaluate(300)
result_1500 = train_and_evaluate(1500)

# 결과 출력
for result in [result_20, result_300, result_1500]:
    print(f"\n===== {result['epochs']} epochs =====")
    print("예측값:", result["predictions"])
    print("최종 loss:", result["loss"])
    print("가중치:", result["weight"])
    print("편향:", result["bias"])

# 실제 정답 출력
print("\n실제 기대값:", np.array([18, 21, 24], dtype=np.float32))