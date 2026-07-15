# 학생들의 점수를 리스트로 저장
scores = [78, 85, 92, 68, 95, 88, 74]

# 모든 점수의 합을 학생 수로 나누어 평균 점수를 계산
average_score = sum(scores) / len(scores)

# 점수 리스트에서 가장 높은 점수를 구함
highest_score = max(scores)

# 점수 리스트에서 가장 낮은 점수를 구함
lowest_score = min(scores)

# 80점 이상인 점수만 새로운 리스트에 저장
scores_above_80 = [score for score in scores if score >= 80]

# 평균 이상인 점수의 개수를 계산
count_above_average = sum(
    1 for score in scores
    if score >= average_score
)

# 평균 점수를 출력
print("평균 점수:", average_score)

# 최고점을 출력
print("최고점:", highest_score)

# 최저점을 출력
print("최저점:", lowest_score)

# 80점 이상인 점수 리스트를 출력
print("80점 이상 점수:", scores_above_80)

# 평균 이상인 학생 수를 출력
print("평균 이상인 학생 수:", count_above_average)
