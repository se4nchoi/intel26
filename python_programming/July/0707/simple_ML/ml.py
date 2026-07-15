import pandas as pd
from sklearn import svm
from sklearn.datasets import load_iris

iris = load_iris()

df = pd.DataFrame(iris.data)

s=svm.SVC(gamma=0.1, C=10)
s.fit(iris.data, iris.target)

new_d = [[6.4, 3.2, 6.0, 2.5], [7.1, 3.1, 4.7, 1.35], [5.1, 3.8, 1.5, 0.3], [6.2, 2.9, 4.3, 1.3]]

res = s.predict(new_d)
print("Predicted classes for new data points:", res)
