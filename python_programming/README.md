# Python Programming

Lecture notes, practice programs, datasets, notebooks, and exam exercises from the Intel-26 K-DT Python module. The material progresses from core syntax and file handling to object-oriented programming, numerical analysis, and introductory machine learning.

## What is here

Materials are grouped by class date:

```text
python_programming/
├── June/
│   ├── 0622/   First programs and introductory notes
│   ├── 0626/   Python fundamentals
│   └── 0629/   Control flow and file I/O
├── July/
│   ├── 0701/   Functions, collections, and continued practice
│   ├── 0706/   Object-oriented programming and NumPy
│   ├── 0707/   Pandas, visualization, and machine-learning basics
│   ├── 0713/   Coding-test preparation and exam solutions
│   └── 0714/   Prompt-based software exam materials
└── README.md
```

Individual date folders may contain raw notes alongside a reviewed Markdown summary, executable exercises, datasets, or submitted coursework.

## Topics covered

- Variables, built-in types, operators, strings, and console input/output
- Lists, dictionaries, slicing, comprehensions, and exception handling
- Conditionals, loops, functions, lambdas, modules, and command-line arguments
- Text-file input/output
- Classes, instance and class attributes, and special methods
- NumPy arrays, indexing, vectorized operations, and array properties
- Pandas `Series` and `DataFrame` workflows using CSV and Excel data
- Data analysis and visualization with Matplotlib
- Introductory regression, classification, and scikit-learn workflows
- Algorithmic problem solving and coding-test practice

## Running the examples

Most scripts can be run from the repository root with Python 3:

```bash
python python_programming/June/0622/hello.py
```

Examples from the data-analysis lessons may require third-party packages such as NumPy, Pandas, Matplotlib, scikit-learn, or Jupyter. There is no shared dependency lock file for this course folder, so check the imports in the exercise you intend to run and use an isolated virtual environment.

Open `python_programming/July/0707/chap15.ipynb` in JupyterLab, Jupyter Notebook, or a compatible editor. Dataset paths in older exercises may be relative to their dated folder; if a script cannot find a CSV or spreadsheet, run it from that folder or update the path locally.

## Notes on the archive

These files reflect the course as taught and are retained for study and reference. Some folders contain both original classroom notes and later cleaned summaries, and dates or comments inside legacy files may not always match the surrounding directory name.
