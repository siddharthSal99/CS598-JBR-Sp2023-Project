# Python program to read
# json file
  
  
import json
  
# Opening JSON file
f = open('dataset/python/python20.json')
  
# returns JSON object as 
# a dictionary
data = json.load(f)
  
# Iterating through the json
# list
for ix,rec in enumerate(data):
    fh = open("dataset/python/sample-database/train"+str(ix)+".py", "a", encoding="utf-8")
    print(rec["original_string"])
    fh.write(rec["original_string"])
    fh.close()
  
# Closing file
f.close()


# from staticfg import CFGBuilder

# cfg = CFGBuilder().build_from_file('quick sort', 'dataset/python/train0.py')
# cfg.build_visual('train0', 'png')