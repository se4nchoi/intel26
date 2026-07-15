import numpy as np
import tensorflow as tf

# NumPy 배열 생성
array = np.array([
    [2, 4, 6],
    [8, 10, 12],
    [14, 16, 18]
])

# NumPy 배열을 TensorFlow Tensor로 변환
tensor = tf.convert_to_tensor(array)

# Tensor의 shape 출력
print("shape:", tensor.shape)

# Tensor의 dtype 출력
print("dtype:", tensor.dtype)

# Tensor의 모든 값에 10을 더함
added_tensor = tensor + 10

# 연산 결과 출력
print("10을 더한 결과:")
print(added_tensor)

# Tensor & Numpy 배열의 차이
"""
- 둘다 다차원 배열을 표현한다
- numpy 는 범용적인 과학연산 (CPU 위주) 에 특화
- tensor 는 딥러닝에 특화 (GPU/TPU 등의 가속엔진)
"""
