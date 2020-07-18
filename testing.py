import re

simple = """```python
print("asd")```"""

text = """
not nessesarely related to discord.py, but python and discord.
is it possible to format discord code blocks 
```
these
```
with python3 syntax
using 
\```python
\```
seams to be using python2 syntax

```python
print "hello"
```

```python
print("hello")
```
"""

mod = text.replace("\\```python", "").replace("\\```", "")
valids = mod.split("```python\n")[1:]
cleaned = [valid.rstrip().rstrip("```").rstrip() for valid in valids]
print(cleaned)
