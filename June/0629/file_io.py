import os, sys

"""
write, read files
directories
"""
def write_read_files():
  # Get the absolute path of the directory where this script is located
  script_dir = os.path.dirname(os.path.abspath(__file__))
  # Create a full path for the output file inside that directory
  file_path = os.path.join(script_dir, 'test.txt')

  names = ['alice', 'bob', 'charlie', 'david', 'eve']


  print(f"Writing to file: {file_path}")
  with open(file_path, 'w', encoding='utf-8') as f:
    for name in names:
      f.write(f'{name} is awesome !\n')

  # --- Method 1: .readlines() ---
  # Reads the entire file into a list of strings (lines).
  # Good for when you need all lines in a list, but can use a lot of memory for large files.
  print("\n--- Reading with .readlines() ---")
  with open(file_path, 'r', encoding='utf-8') as f:
    lines = f.readlines() # lines is a list: ['line 1\n', 'line 2\n', ...]
    print(f"Type of object: {type(lines)}")
    for line in lines:
      # .strip() removes leading/trailing whitespace, including the newline character
      print(line.strip())

  # --- Method 2: .read() ---
  # Reads the entire file content into a single string.
  # Can be problematic for very large files as it loads everything into memory.
  print("\n--- Reading with .read() ---")
  with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read() # content is one single string
    print(f"Type of object: {type(content)}")
    print("--- File Content (as a single string) ---")
    print(content)
    print("-----------------------------------------")

  # --- Method 3: Iterating directly (Most Recommended) ---
  # This is the most memory-efficient and Pythonic way to read a file line-by-line.
  # It does not load the whole file into memory.
  print("\n--- Reading by iterating over the file object (Recommended) ---")
  with open(file_path, 'r', encoding='utf-8') as f:
    for line in f: # Each 'line' is read one at a time
      print(line.strip())
    

def executable_readwrite():
  # Check if a filename was provided as a command-line argument.
  # sys.argv[0] is the script name, so we need at least 2 arguments.
  if len(sys.argv) < 2:
    print("Error: No filename(s) provided.")
    print("Usage: python file_io.py <file1> [file2] ...")
    sys.exit(1) # Exit the script with an error code.

  # Get a list of all filenames from the command-line arguments
  filenames = sys.argv[1:]

  # Loop through each filename and process it
  for filename in filenames:
    print(f"\n--- Attempting to read file: {filename} ---")
    try:
      # Open the file provided by the user
      with open(filename, 'r', encoding='utf-8') as f:
        print(f"Successfully opened '{filename}'. Processing content:")
        # Process the file line-by-line
        for i, line in enumerate(f, 1):
          print(f"Line {i}: {line.strip().capitalize()}")

    except FileNotFoundError:
      # If a file is not found, print an error and continue to the next one.
      print(f"Error: The file '{filename}' was not found.")
    except Exception as e:
      print(f"An unexpected error occurred while reading '{filename}': {e}")

# This block ensures the code runs only when the script is executed directly.
if __name__ == "__main__":
  executable_readwrite()
  