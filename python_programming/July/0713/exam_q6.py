numbers = [1,2,3,4,5] 
print(sum(numbers)/len(numbers)) 
#print(numbers.max())
print(max(numbers))
"""
### 6.1 오류가 발생하는 부분

오류가 발생하는 부분은 다음 코드이다.

```python
print(numbers.max())
```

실행 시 다음과 같은 오류가 발생한다.

```text
AttributeError: 'list' object has no attribute 'max'
```

### 6.2 올바르게 수정한 코드

```python
numbers = [1, 2, 3, 4, 5]

print(sum(numbers) / len(numbers))
print(max(numbers))
```

### 예상 출력

```text
3.0
5
```

### 6.3 오류가 발생한 이유

`numbers`는 Python의 `list` 객체인데, `list` 클래스에는 `max()` 메서드가 정의되어 있지 않다. 따라서 `numbers.max()`처럼 객체 메서드 방식으로 호출하면 `AttributeError`가 발생한다.

반면 `max()`, `sum()`, `len()`은 Python이 기본으로 제공하는 내장 함수이므로, 처리할 리스트를 인자로 전달하여 `max(numbers)`와 같이 사용해야 한다.

"""
