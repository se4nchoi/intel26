"""
#1.
a) Count how many times each number appears.
b) Produce a list containing only the unique values.
c) Sort the unique values in descending order.
d) Return the two most frequent values.

nums = [3, 1, 3, 2, 1, 3]
"""
def count(nums):
    # use hashmap to increment counts
    hm = {} # or however you make a hash in python
    for num in nums:
      if (num in hm):
        hm[num] += 1
      else:
        hm[num] = 1
        
    return hm

def unique(nums):
    unique_values = []
    for num in nums:
      if num not in unique_values:
        unique_values.append(num)
    return unique_values
      
def desc_sort(nums):
    values = unique(nums)
    # if not implemented, make that helper function while looping
    # hmm.. what is the most efficient way to descend 
    # this is where i need practice...
    # i feel a bubble sort or something maybe sort this array in place
    # but not sure on implementation
    
    # brute force is to loop in n^2 ?
    # compare curr value to max (idx 0), then search entire array?
    # because if a max was determined, for sure the rest of array don't have anything bigger
    
    n = len(values)
    for i in range(0, n):
      max_idx = values[i]
      for k in range(i+1, n):
        curr = values[k]
        if curr >= max_idx:
          values[k], values[i] = max_idx, curr

def two_most_freq1(nums):
  hash = count(nums)
  high = -1
  second = -1
  num1 = None
  num2 = None
  for (key, val) in hash:
    if (val >= high):
      num1 = key
      high = val
    elif (val >= second):
      num2 = key
      second = val
  return num1, num2

def two_most_freq(nums):
    counts = count(nums)

    highest_count = -1
    second_count = -1
    most_frequent = None
    second_most_frequent = None

    for key, val in counts.items():
      # if tied, replace
      if val >= highest_count:
        second_count = highest_count
        second_most_frequent = most_frequent
        
        highest_count = val
        most_frequent = key
      elif val >= second_count:
        second_count = val
        second_most_frequent = key
    
    return most_frequent, second_most_frequent