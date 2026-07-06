import numpy as np

# 1. Creating Arrays
print("1. Creating Arrays:")
arr1 = np.array([1, 2, 3, 4, 5])
print("1D Array:", arr1)

arr2 = np.array([[1, 2, 3], [4, 5, 6]])
print("2D Array:\n", arr2)

arr_zeros = np.zeros((3, 4))
print("Array of Zeros (3x4):\n", arr_zeros)

arr_ones = np.ones((2, 2))
print("Array of Ones (2x2):\n", arr_ones)

arr_range = np.arange(0, 10, 2) # start, stop (exclusive), step
print("Array with arange (0 to 10, step 2):", arr_range)

arr_linspace = np.linspace(0, 1, 5) # start, stop (inclusive), number of elements
print("Array with linspace (0 to 1, 5 elements):", arr_linspace)
print("-" * 30)

# 2. Array Attributes
print("2. Array Attributes:")
print("Shape of arr2:", arr2.shape)
print("Number of dimensions of arr2:", arr2.ndim)
print("Data type of arr1:", arr1.dtype)
print("Size of arr1 (total elements):", arr1.size)
print("-" * 30)

# 3. Basic Operations
print("3. Basic Operations:")
a = np.array([10, 20, 30, 40])
b = np.array([1, 2, 3, 4])

print("a + b:", a + b)
print("a * 2:", a * 2)
print("a / b:", a / b)
print("a > 20:", a > 20)
print("-" * 30)

# 4. Indexing and Slicing
print("4. Indexing and Slicing:")
print("Element at index 2 of arr1:", arr1[2])
print("First row of arr2:", arr2[0, :])
print("Second column of arr2:", arr2[:, 1])
print("Slice of arr1 (index 1 to 4):", arr1[1:4])
print("-" * 30)