import numpy as np
import pandas as pd

# 학생별 국어, 영어, 수학 점수를 NumPy 배열로 저장
data = np.array([
    [85, 90, 88],
    [70, 80, 75],
    [95, 98, 100],
    [60, 72, 68]
])

# NumPy 배열을 DataFrame으로 변환하고 과목명을 열 이름으로 지정
df = pd.DataFrame(
    data,
    columns=["국어", "영어", "수학"]
)

# 각 행에 저장된 학생별 세 과목 평균을 계산하여 새로운 열에 추가
df["평균"] = df.mean(axis=1)

# 평균 열에서 가장 높은 값이 위치한 행의 인덱스를 구함
highest_index = df["평균"].idxmax()

# 해당 인덱스를 이용하여 평균이 가장 높은 학생의 전체 정보를 가져옴
highest_student = df.loc[highest_index]

# 전체 DataFrame을 출력
print("전체 학생 성적:")
print(df)

# 평균이 가장 높은 학생의 정보를 출력
print("\n평균이 가장 높은 학생:")
print(highest_student)