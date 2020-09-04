import re

text = """hahahahaha this si my first box
```py
import urllib2
try:
  urllib2.urlopen("https://google.com", timeout=1)
  print("internet on")
except:
  print("internet off")
```

hihihi this is my second box
```py
a = "asd"
```
asdasdasda
```
asd
```"""

pattern = re.compile(r"`{3}(\w+)\n((?:(?!`{3}).)+)```", re.DOTALL)
if match := pattern.findall(text):
    for stuff in match:
        asd, qwe = stuff
