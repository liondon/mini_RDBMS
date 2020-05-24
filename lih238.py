
# coding: utf-8

# In[2]:


### GLOBAL VARIABLES:
### - table: each table is a numpy structured array
###   >> Assuming: integer is 32-bit signed integer, string is 20-character unicode string
### - tableDic: tables["tableName"] returns [table, colDic]
### - colDic: column dictionary for corresponding table s.t. colDic["colName"] = index of that column (in that table)
### - idxDic: indicex dictionary s.t. idxDic[(tableName, colName)] = corresponding index (hash or btree)
###   >> Assuming: There won't be both Btree and Hash indexes created on one field.
###                Index will only be on single field

### NOTE: 
### - This system is case-sensitive
### - Should be further modelized
### - there are some more functions in numpy library that could be useful
### - functions related to using index is a mess

import sys
import time
import numpy as np
import operator as op
import itertools as it
from BTrees.OOBTree import OOBTree

### Change the settings for integer & string here. ###
integer = 'i4'
string = 'U20'
FLOAT = 'f8'

tableDic = {}
idxDic = {}

comparators = {"!=": op.ne, "<=": op.le, ">=": op.ge,
               "=": op.eq, "<": op.lt, ">": op.gt}

calculators = {"+": op.add, "-": op.sub, "*": op.mul, "/": op.truediv}
unCalculats = {"+": op.sub, "-": op.add, "*": op.truediv, "/": op.mul}


# In[3]:


### - what this function does: 
###   > seperate the conditions for selection or join operations
###   Assuming: if there is "and", there is no "or", vice versa.
### - what its inputs are/mean: 
###   > conditions: a string that represents the conditions for selection or join operations. (e.g. T1.a = T2.b and T1.c = 5)
### - what the outputs are/mean: 
###   > cond: a list of all conditions, each item is a string representing a single condition. (e.g. T1.a > T2.b)
###   > AndOr: a string representing whether the conditions in cond are combined with "and"/"or".
### - any side eﬀects to globals:
###   > NO
def condList(conditions):
    s = conditions
    if s.find("and") != -1:
        (cond, AndOr) = (s.split("and"), "and")
    elif s.find("or") != -1:
        (cond, AndOr) = (s.split("or"), "or")
    else:
        (cond, AndOr) = ([s], None)
    for i in range(len(cond)):
        cond[i] = cond[i].strip().lstrip('(').rstrip(')')    
    return (cond, AndOr)

### - what this function does: 
###   > further analyse a single condition to check if there is any arithmetic operation.
### - what its inputs are/mean: 
###   > condition: a string representing a single condition. (e.g. T1.a + c1 > T2.b * c2)
### - what the outputs are/mean: 
###   > a, acal, consta: a is (Column | Constant), acal is [+|-|*|/], consta is [Constant]
###   > b, bcal, constb: b is (Column | Constant), bcal is [+|-|*|/], constb is [Constant]
###   > o: (<|<=|=|!=|>|>=)
### - any side eﬀects to globals:
###   > NO
def conditionDecmp(condition):
    for cmp in comparators.keys():
        currCond = condition.split(cmp)
        for ele in ["!", "<", ">"]:
            if currCond[0].find(ele) != -1:
                continue
        if (len(currCond) > 1) and (currCond[1].find("=")) == -1:
            o = cmp
            break
    a = currCond[0].strip().strip("'").strip('"')
    b = currCond[1].strip().strip("'").strip('"')
    acal, consta, bcal, constb = None, 0, None, 0
    for cal in calculators.keys():
        a_c = a.split(cal)
        if len(a_c) > 1:
            a, acal, consta = a_c[0].strip(), cal, int(a_c[1].strip())
            break
    for cal in calculators.keys():
        b_c = b.split(cal)
        if len(b_c) > 1:
            b, bcal, constb = b_c[0].strip(), cal, int(b_c[1].strip())
            break
    a = int(a) if a.isnumeric() else a
    b = int(b) if b.isnumeric() else b
    return (a, acal, consta, o, b, bcal, constb)


# In[4]:


### - what this function does: 
###   > check if a given row table[i] satisfy the given conditions
### - what its inputs are/mean: 
###   > tableName: the name of the table that we are checking
###   > cond: a list of all conditions, each item is a string representing a single condition. (e.g. T1.a > T2.b)
###   > AndOr: a string representing whether the conditions in cond are combined with "and"/"or".
###   > i: the index of the row that we are checking
### - what the outputs are/mean: 
###   > qualify: True if the row meet all conditions, False otherwise.
### - any side eﬀects to globals:
###   > NO
def checkCond1T(tableName, cond, AndOr, i):
    (table, colDic) = (tableDic[tableName][0], tableDic[tableName][1])
    for condition in cond:
        (a, acal, consta, o, b, bcal, constb) = conditionDecmp(condition)
        #print((a, acal, consta, o, b, bcal, constb))
        a = table[a][i] if (colDic.get(tableName+"."+str(a)) != None) else a
        b = table[b][i] if (colDic.get(tableName+"."+str(b)) != None) else b
        a = calculators[acal](a, consta) if acal != None else a
        b = calculators[bcal](b, constb) if bcal != None else b
        a = a.strip() if type(a)==np.str_ else a
        b = b.strip() if type(b)==np.str_ else b
        qualify = comparators[o](a, b)        
        #print(a, o, b, comparators[o](a, b))
        if (AndOr == "and" and qualify == False) or (AndOr == "or" and qualify == True):
            break
    return qualify

### - what this function does: 
###   > check whether t1[i] and t2[j] satisfy the conditions
### - what its inputs are/mean: 
###   > t1Name, t2Name: the name of the tables that we are checking
###   > cond: a list of all conditions, each item is a string representing a single condition. (e.g. T1.a > T2.b)
###   > AndOr: a string representing whether the conditions in cond are combined with "and"/"or".
###   > i, j: the indices of the rows that we are checking
### - what the outputs are/mean: 
###   > qualify: True if the row(s) meet all conditions, False otherwise.
### - any side eﬀects to globals:
###   > NO
def checkCond2T(t1Name, t2Name, cond, AndOr, i, j):
    table1, colDic1, table2, colDic2 = tableDic[t1Name][0], tableDic[t1Name][1], tableDic[t2Name][0], tableDic[t2Name][1]
    for condition in cond:
        (a, acal, consta, o, b, bcal, constb) = conditionDecmp(condition)
        #print((a, acal, consta, o, b, bcal, constb))
        a = table1[a.split(".")[1]][i] if (colDic1.get(a) != None) else a
        a = table2[a.split(".")[1]][j] if (colDic2.get(a) != None) else a
        b = table1[b.split(".")[1]][i] if (colDic1.get(b) != None) else b
        b = table2[b.split(".")[1]][j] if (colDic2.get(b) != None) else b
        a = calculators[acal](a, consta) if acal != None else a
        b = calculators[bcal](b, constb) if bcal != None else b
        a = a.strip() if type(a)==np.str_ else a
        b = b.strip() if type(b)==np.str_ else b
        qualify = comparators[o](a, b)
        #print(a, o, b, comparators[o](a, b))        
        if (AndOr == "and" and qualify == False) or (AndOr == "or" and qualify == True):
            break
    return qualify


# In[5]:


### - what this function does: 
###   > find potential qualified rows using index
###   > Assuming: only use on equality comparison, not on range search.
###   > NOTE: Not able to deal with T.colA = T.colB, assuming condition pattern is T.col = const | const = T.col
### - what its inputs are/mean: 
###   > tableName: the name of the table that we are checking
###   > cond: a list of all conditions, each item is a string representing a single condition. (e.g. T1.a > T2.b)
###   > AndOr: a string representing whether the conditions in cond are combined with "and"/"or".
### - what the outputs are/mean: 
###   > answer: indices of potential qualified rows that need further checking
### - any side eﬀects to globals:
###   > NO
def checkIdx1T(tableName, cond, AndOr):
    answer = set(())
    for condition in cond:
        (a, acal, consta, o, b, bcal, constb) = conditionDecmp(condition)
        if (o != "="):
            continue
        if idxDic.get((tableName, a)) == None:
            a, b = b, a
        if idxDic.get((tableName, a)) == None:
            continue
        index = idxDic[(tableName, a)]
        print("use index: "+str((tableName, a)))
        newAns = set(())
        b = calculators[bcal](b, constb) if bcal != None else b
        b = unCalculats[acal](b, consta) if acal != None else b
        a = a.strip() if type(a)==np.str_ else a
        b = b.strip() if type(b)==np.str_ else b        
        if index.get(b) == None:
            continue
        for idx in index[b]:
            newAns.add(idx)
        answer = (newAns & answer) if (AndOr == "and") and (len(answer) != 0) else (newAns | answer)
    return answer

### - what this function does: 
###   > find potential qualified rows using index (condition might relate to two tables)
###   > Assuming: only use on equality comparison, not on range search.
###   > NOTE: Not able to deal with T.col = const | const = T.col, assuming condition pattern is T1.colA = T2.colB
### - what its inputs are/mean: 
###   > t1Name, t2Name: the name of the table that we are checking
###   > cond: a list of all conditions, each item is a string representing a single condition. (e.g. T1.a > T2.b)
###   > AndOr: a string representing whether the conditions in cond are combined with "and"/"or".
### - what the outputs are/mean: 
###   > answer: indices of potential qualified rows that need further checking
### - any side eﬀects to globals:
###   > NO
def checkIdx2T(t1Name, t2Name, cond, AndOr):
    answer = set(())
    for condition in cond:
        (a, acal, consta, o, b, bcal, constb) = conditionDecmp(condition)
        if (o != "="):
            continue
        tableA, indexA, tableB, indexB = None, None, None, None
        if a.find(".") != -1:
            a_split = a.split(".")
            (tableA, colA) = (a_split[0], a_split[1])
            indexA = idxDic.get((tableA, colA))
            if indexA != None:
                print("use index: "+str((tableA, colA)))
            tableA = tableDic[tableA][0]
        if b.find(".") != -1:
            b_split = b.split(".")
            (tableB, colB) = (b_split[0], b_split[1])
            indexB = idxDic.get((tableB, colB))
            if indexB != None:
                print("use index: "+str((tableB, colB)))
            tableB = tableDic[tableB][0]
        newAns = set(())
        if (indexA != None) and (indexB != None):    ### a, b are both colnames
            for a in indexA.keys():
                b = a
                b = calculators[acal](b, consta) if acal != None else b
                b = unCalculats[bcal](b, constb) if bcal != None else b
                a = a.strip() if type(a)==np.str_ else a
                b = b.strip() if type(b)==np.str_ else b
                try:
                    result = list(it.product(indexA[a], indexB[b]))
                    for pair in result:
                        newAns.add(pair)
                except:
                    continue                    
        elif indexA != None:    ### a is a column, b might be constant or column
            if tableB == None and indexA.get(b) != None:    ### when b is a constant and indexA[b] get something
                pass    ### should fix this: depend on AndOr
            else:    ### when b is a column
                for j in range(tableB.shape[0]):
                    b = tableB[colB][j]
                    b = calculators[bcal](b, constb) if bcal != None else b
                    b = unCalculats[acal](b, consta) if acal != None else b
                    b = b.strip() if type(b)==np.str_ else b
                    i = indexA[b] if indexA.get(b) != None else []
                    result = list(it.product(i, [j]))
                    for pair in result:
                        newAns.add(pair)            
        elif indexB != None:
            if tableA == None and indexB.get(a) != None:
                pass    ### should fix this
            else:
                for i in range(tableA.shape[0]):
                    a = tableA[colA][i]
                    a = calculators[acal](a, consta) if acal != None else a
                    a = unCalculats[bcal](a, constb) if bcal != None else a
                    a = a.strip() if type(a)==np.str_ else a
                    j = indexB[a] if indexB.get(a) != None else []
                    result = list(it.product([i], j))
                    for pair in result:
                        newAns.add(pair)            
        else:
            continue
        answer = (newAns & answer) if (AndOr == "and") and (len(answer) != 0) else (newAns | answer)
        
    return answer


# In[6]:


### - what this function does: 
###   > create a new table
### - what its inputs are/mean: 
###   > tableName: the name of the table that we are creating
###   > tableNcolDic: (newTable, colDic), storing the newTable itself and its column dictionary, colDic.
### - what the outputs are/mean: 
###   > None
### - any side eﬀects to globals:
###   > tableDic[tableName] = (newTable, newcolDic), 
###     i.e. storing this table to the table dictionary so that we can find it with its name
### - Example operation in the input commands: 
###   > R := newTable
def createT(tableName, tableNcolDic):  
    (newTable, colDic) = (tableNcolDic[0], tableNcolDic[1])
    newcolDic = {}
    for key in colDic.keys():
        newcolDic[tableName + "." + key] = colDic[key] 
    tableDic[tableName] = (newTable, newcolDic)


# In[7]:


### - what this function does: 
###   > input a .txt file into a structured array
### - what its inputs are/mean: 
###   > args: a list storing the arguments given in the input command. Should include the following elements:
###   >> fileName: the file Name that we are inputing
### - what the outputs are/mean: 
###   > (newTable, colDic): storing the newTable itself and its column dictionary, colDic.
### - any side eﬀects to globals:
###   > No
### - Example operation in the input commands: 
###   > inputfromfile(sales1)
def inputFromFile(args):
    (fileName) = (args[0])
    colDic, typeLs = {}, []
    f = open(fileName+".txt","r")
    line_split = f.readline().strip().split("|")
    line2_split = f.readline().strip().split("|")
    for i in range(len(line_split)):
        colDic[line_split[i]] = i
        t = (line_split[i], integer) if line2_split[i].strip().isnumeric() else (line_split[i], string)
        typeLs.append(t)
    f.close()    
    newTable = np.loadtxt(fileName+".txt", delimiter="|", skiprows=1, dtype=typeLs)
    return (newTable, colDic)


# In[8]:


### - what this function does: 
###   > select all rows in given table that meet all given conditions
### - what its inputs are/mean: 
###   > args: a list storing the arguments given in the input command. Should include the following elements:
###   >> tableName: the name of the table that we are checking
###   >> conditions: a string that represents the conditions for selection or join operations. (e.g. T1.a = T2.b and T1.c = 5)
### - what the outputs are/mean: 
###   > (newTable, colDic): storing the newTable itself and its column dictionary, colDic.
### - any side eﬀects to globals:
###   > No
### - Example operation in the input commands: 
###   > select(R, (time > 50) or (qty < 30))
def select(args):
    (tableName, conditions) = (args[0], args[1])
    (table, colDic) = (tableDic[tableName][0], tableDic[tableName][1])
    (cond, AndOr) = condList(conditions)
    ### check if there is index to use, and returns the qualified indices for further check
    answer = checkIdx1T(tableName, cond, AndOr)
    print("We got {} potential answers after check index".format(len(answer)))
    ### if there is no index to use, thus we have to check every row in table
    if len(answer) == 0:
        for i in range(table.shape[0]):
            qualify = checkCond1T(tableName, cond, AndOr, i)
            if qualify == True:
                answer.add(i)
    ### if there is index to use, and AndOr="and", 
    ### we have to check qualified rows in answer
    elif AndOr == "and":
        wrong = set(())
        for i in answer:
            qualify = checkCond1T(tableName, cond, AndOr, i)
            if qualify != True:
                wrong.add(i)
        answer = answer - wrong
    ### if there is index to use, and AndOr="or", 
    ### check if there is qualified rows other than those already in answer
    elif AndOr == "or":
        check = set(range(table.shape[0])) - answer
        print("We have to check {} remaining records.".format(len(check)))
        for i in check:
            qualify = checkCond1T(tableName, cond, AndOr, i)
            if qualify == True:
                answer.add(i)
    #print(answer)    
    newcolDic, typeLs = {}, table.dtype
    for key in colDic.keys():
        newcolDic[key.split(".")[1]] = colDic[key]
    newTable = np.zeros(len(answer), dtype=typeLs)
    i = 0
    for idx in sorted(answer):
        newTable[i] = table[idx]
        i += 1
    return (newTable, newcolDic)


# In[9]:


### - what this function does: 
###   > (inner) join two tables on given conditions
### - what its inputs are/mean: 
###   > args: a list storing the arguments given in the input command. Should include the following elements:
###   >> t1Name, t2Name: names of tables that we are joinning
###   >> conditions: a string that represents the conditions for selection or join operations. (e.g. T1.a = T2.b and T1.c = 5)
### - what the outputs are/mean: 
###   > (newTable, colDic): storing the newTable itself and its column dictionary, colDic.
### - any side eﬀects to globals:
###   > No
### - Example operation in the input commands: 
###   > join(R, S, R.customerid = S.C) 
def join(args):
    (t1Name, t2Name, conditions) = (args[0], args[1], args[2])
    (table1, colDic1) = (tableDic[t1Name][0], tableDic[t1Name][1])
    (table2, colDic2) = (tableDic[t2Name][0], tableDic[t2Name][1])
    (cond, AndOr) = condList(conditions)
    answer = checkIdx2T(t1Name, t2Name, cond, AndOr)
    print("We got {} potential answers after check index".format(len(answer)))
    ### if there is no index to use, thus we have to check every row in table
    if len(answer) == 0:
        for i in range(table1.shape[0]):
            for j in range(table2.shape[0]):
                qualify = checkCond2T(t1Name, t2Name, cond, AndOr, i, j)
                if qualify == True:
                    answer.add((i, j))
    ### if there is index to use, and AndOr="and", 
    ### we have to check qualified rows in answer
    elif AndOr == "and":
        wrong = set(())
        for i, j in answer:
            qualify = checkCond2T(t1Name, t2Name, cond, AndOr, i, j)
            if qualify != True:
                wrong.add((i, j))
        answer = answer - wrong
    ### if there is index to use, and AndOr="or", 
    ### check if there is qualified rows other than those already in answer
    elif AndOr == "or":
        for i in range(table1.shape[0]):
            for j in range(table2.shape[0]):
                if (i, j) in answer:
                    continue
                qualify = checkCond2T(t1Name, t2Name, cond, AndOr, i, j)
                if qualify == True:
                    answer.add((i, j))            
        #check = set(it.product(range(table1.shape[0]), range(table2.shape[0]))) - answer    ## might get a MemoryError.
        #print("We have to check {} remaining pairs.".format(len(check)))
        #for (i, j) in check:
        #        qualify = checkCond2T(t1Name, t2Name, cond, AndOr, i, j)
        #        if qualify == True:
        #            answer.add((i, j))    
    #print(answer)
    newcolDic, typeLs = {}, []
    i = 0
    for key in colDic1.keys():
        key = key.split(".")[1]
        colName = t1Name+"_"+key
        newcolDic[colName] = i
        t = (colName, integer) if type(table1[key][0])==np.dtype(integer) else (colName, string)
        typeLs.append(t)
        i += 1
    for key in colDic2.keys():
        key = key.split(".")[1]
        colName = t2Name+"_"+key
        newcolDic[colName] = i
        t = (colName, integer) if type(table2[key][0])==np.dtype(integer) else (colName, string)
        typeLs.append(t)
        i += 1
    newTable = np.zeros(len(answer), dtype=typeLs)
    idx = 0
    for i, j in sorted(answer):
        for key in newcolDic.keys():
            splitKey = key.split("_")
            oldKey = splitKey[0]+"."+splitKey[1]
            newTable[key][idx] = table1[i][colDic1[oldKey]] if (colDic1.get(oldKey) != None) else table2[j][colDic2[oldKey]]
        idx += 1
    return (newTable, newcolDic)


# In[11]:


### - what this function does: 
###   > project given columns in given table
### - what its inputs are/mean: 
###   > args: a list storing the arguments given in the input command. Should include the following elements:
###   >> tableName: name of table that we are projecting
###   >> colNames: list of string that represents names of columns that we are projecting
### - what the outputs are/mean: 
###   > (newTable, colDic): storing the newTable itself and its column dictionary, colDic.
### - any side eﬀects to globals:
###   > No
### - Example operation in the input commands: 
###   > project("R1", "saleid", "qty", "pricerange")
def project(args):
    (tableName, colNames) = (args[0], args[1:])
    (table, colDic) = (tableDic[tableName][0], tableDic[tableName][1])    
    newcolDic, typeLs = {}, []
    i = 0
    for colName in colNames:
        newcolDic[colName] = i
        t = (colName, integer) if type(table[colName][0])==np.dtype(integer) else (colName, string)
        typeLs.append(t)
        i += 1    
    newTable = np.zeros(table.shape[0], dtype=typeLs)
    for i in range(table.shape[0]):
        for colName in colNames:
            newTable[colName][i] = table[colName][i]
    return (newTable, newcolDic)


# In[16]:


### - what this function does: 
###   > count the rows in given table for given columns
### - what its inputs are/mean: 
###   > args: a list storing the arguments given in the input command. Should include the following elements:
###   >> tableName: name of table that we are dealing
###   >> colNames: list of string that represents names of columns that we are dealing
### - what the outputs are/mean: 
###   > (newTable, colDic): storing the newTable itself and its column dictionary, colDic.
### - any side eﬀects to globals:
###   > No
### - Example operation in the input commands: 
###   > count(R1, qty)
def count(args):
    tableName = args[0]
    (table, colDic) = (tableDic[tableName][0], tableDic[tableName][1])
    newcolDic, typeLs = {}, []
    newcolDic["count("+tableName+")"] = 0
    typeLs.append(("count("+tableName+")", integer))
    newTable = np.zeros(1, dtype=typeLs)
    newTable["count("+tableName+")"][0] = table.shape[0]
    return (newTable, newcolDic)

    if False:   ### a former version
        (tableName, colNames) = (args[0], args[1:])
        (table, colDic) = (tableDic[tableName][0], tableDic[tableName][1])
        newcolDic, typeLs = {}, []
        i = 0
        for colName in colNames:
            newcolDic["count("+colName+")"] = i
            typeLs.append(("count("+colName+")", integer))
            i += 1
        newTable = np.zeros(i, dtype=typeLs)
        for colName in colNames:
            count = 0
            for i in range(table.shape[0]):
                count += 1
            newTable["count("+colName+")"][0] = count
        return (newTable, newcolDic)


# In[21]:


### - what this function does: 
###   > calculate sum(s) of values in a column of given table for all given column(s). 
### - what its inputs are/mean: 
###   > args: a list storing the arguments given in the input command. Should include the following elements:
###   >> tableName: name of table that we are dealing
###   >> colNames: list of string that represents names of columns that we are dealing
### - what the outputs are/mean: 
###   > (newTable, colDic): storing the newTable itself and its column dictionary, colDic.
### - any side eﬀects to globals:
###   > No
### - Example operation in the input commands: 
###   > sum(R1, qty)
def sum(args):
    (tableName, colNames) = (args[0], args[1:])
    (table, colDic) = (tableDic[tableName][0], tableDic[tableName][1])
    newcolDic, typeLs = {}, []
    i = 0
    for colName in colNames:
        newcolDic["sum("+colName+")"] = i
        typeLs.append(("sum("+colName+")", FLOAT))
        i += 1
    newTable = np.zeros(i, dtype=typeLs)
    for colName in colNames:
        total = 0
        for i in range(table.shape[0]):
            total += table[colName][i]
        newTable["sum("+colName+")"][0] = total    
    return (newTable, newcolDic)


# In[22]:


### - what this function does: 
###   > calculate average(s) of values in a column of given table for all given column(s). 
### - what its inputs are/mean: 
###   > args: a list storing the arguments given in the input command. Should include the following elements:
###   >> tableName: name of table that we are dealing
###   >> colNames: list of string that represents names of columns that we are dealing
### - what the outputs are/mean: 
###   > (newTable, colDic): storing the newTable itself and its column dictionary, colDic.
### - any side eﬀects to globals:
###   > No
### - Example operation in the input commands: 
###   > avg(R1, qty)
def avg(args):
    (tableName, colNames) = (args[0], args[1:])
    (table, colDic) = (tableDic[tableName][0], tableDic[tableName][1])
    newcolDic, typeLs = {}, []
    i = 0
    for colName in colNames:
        newcolDic["avg("+colName+")"] = i
        typeLs.append(("avg("+colName+")", FLOAT))
        i += 1
    newTable = np.zeros(i, dtype=typeLs)
    for colName in colNames:
        total = 0
        for i in range(table.shape[0]):
            total += table[colName][i]
        avg = total / table.shape[0]
        newTable["avg("+colName+")"][0] = avg
    return (newTable, newcolDic)


# In[23]:


### - what this function does: 
###   > calculate sum of values in a given column of given table, group by given column(s)
### - what its inputs are/mean: 
###   > args: a list storing the arguments given in the input command. Should include the following elements:
###   >> tableName: name of table that we are dealing
###   >> sumCol: name of column that we are calculating for
###   >> groupCols: list of string that represents names of columns that we should use to group the result
### - what the outputs are/mean: 
###   > (newTable, colDic): storing the newTable itself and its column dictionary, colDic.
### - any side eﬀects to globals:
###   > No
### - Example operation in the input commands: 
###   > sumgroup(R1, qty, time, pricerange) 
def sumGroup(args):
    (tableName, sumCol, groupCols) = (args[0], args[1], args[2:])
    (table, colDic) = (tableDic[tableName][0], tableDic[tableName][1])
    newcolDic, typeLs = {}, []
    i = 0
    for colName in groupCols:
        newcolDic[colName] = i
        t = (colName, integer) if type(table[colName][0])==np.dtype(integer) else (colName, string)
        typeLs.append(t)
        i += 1
    newcolDic["sum("+sumCol+")"] = i
    typeLs.append(("sum("+sumCol+")", integer))
    sumDic = {}
    for i in range(table.shape[0]):
        groupLs = []
        for colName in groupCols:
            groupLs.append(table[colName][i])
        groupTp = tuple(groupLs)    ## need this because list is unhashable
        if (sumDic.get(groupTp) == None):
            sumDic[groupTp] = 0
        sumDic[groupTp] += table[sumCol][i]
    newTable = np.zeros(len(sumDic), dtype=typeLs)
    i = 0
    for key in sumDic.keys():
        for j in range(len(key)):
            newTable[i][j] = key[j]
        newTable[i][-1] = sumDic[key]
        i += 1
    return (newTable, newcolDic)    


# In[24]:


### - what this function does: 
###   > calculate average of values in a given column of given table, group by given column(s)
### - what its inputs are/mean: 
###   > args: a list storing the arguments given in the input command. Should include the following elements:
###   >> tableName: name of table that we are dealing
###   >> avgCol: name of column that we are calculating for
###   >> groupCols: list of string that represents names of columns that we should use to group the result
### - what the outputs are/mean: 
###   > (newTable, colDic): storing the newTable itself and its column dictionary, colDic.
### - any side eﬀects to globals:
###   > No
### - Example operation in the input commands: 
###   > avggroup(R1, qty, pricerange) 
def avgGroup(args):
    (tableName, avgCol, groupCols) = (args[0], args[1], args[2:])
    (table, colDic) = (tableDic[tableName][0], tableDic[tableName][1])
    newcolDic, typeLs = {}, []
    i = 0
    for colName in groupCols:
        newcolDic[colName] = i
        t = (colName, integer) if type(table[colName][0])==np.dtype(integer) else (colName, string)
        typeLs.append(t)
        i += 1
    newcolDic["avg("+avgCol+")"] = i
    typeLs.append(("avg("+avgCol+")", FLOAT))
    avgDic = {}
    for i in range(table.shape[0]):
        groupLs = []
        for colName in groupCols:
            groupLs.append(table[colName][i])
        groupTp = tuple(groupLs)    ## need this because list is unhashable
        if (avgDic.get(groupTp) == None):
            avgDic[groupTp] = [0, 0]
        avgDic[groupTp][0] += int(table[avgCol][i])
        avgDic[groupTp][1] += 1
    newTable = np.zeros(len(avgDic), dtype=typeLs)
    i = 0
    for key in avgDic.keys():
        for j in range(len(key)):
            newTable[i][j] = key[j]
        newTable[i][-1] = avgDic[key][0] / avgDic[key][1]
        i += 1
    return (newTable, newcolDic)    


# In[25]:


### - what this function does: 
###   > count values of a given column of given table, group by given column(s)
### - what its inputs are/mean: 
###   > args: a list storing the arguments given in the input command. Should include the following elements:
###   >> tableName: name of table that we are dealing
###   >> countCol: name of column that we are calculating for
###   >> groupCols: list of string that represents names of columns that we should use to group the result
### - what the outputs are/mean: 
###   > (newTable, colDic): storing the newTable itself and its column dictionary, colDic.
### - any side eﬀects to globals:
###   > No
### - Example operation in the input commands: 
###   > countgroup(R1, qty, pricerange) 
def countGroup(args):
    (tableName, countCol, groupCols) = (args[0], args[1], args[2:])
    (table, colDic) = (tableDic[tableName][0], tableDic[tableName][1])
    newcolDic, typeLs = {}, []
    i = 0
    for colName in groupCols:
        newcolDic[colName] = i
        t = (colName, integer) if type(table[colName][0])==np.dtype(integer) else (colName, string)
        typeLs.append(t)
        i += 1
    newcolDic["count("+countCol+")"] = i
    typeLs.append(("count("+countCol+")", integer))
    countDic = {}
    for i in range(table.shape[0]):
        groupLs = []
        for colName in groupCols:
            groupLs.append(table[colName][i])
        groupTp = tuple(groupLs)    ## need this because list is unhashable
        if (countDic.get(groupTp) == None):
            countDic[groupTp] = 0
        countDic[groupTp] += 1
    newTable = np.zeros(len(countDic), dtype=typeLs)
    i = 0
    for key in countDic.keys():
        for j in range(len(key)):
            newTable[i][j] = key[j]
        newTable[i][-1] = countDic[key]
        i += 1
    return (newTable, newcolDic)    


# In[27]:


### - what this function does: 
###   > sort the given table by given column(s)
### - what its inputs are/mean: 
###   > args: a list storing the arguments given in the input command. Should include the following elements:
###   >> tableName: name of table that we are sorting
###   >> sortCols: list of string that represents names of columns that we should sort the table by
### - what the outputs are/mean: 
###   > (newTable, colDic): storing the newTable itself and its column dictionary, colDic.
### - any side eﬀects to globals:
###   > No
### - Example operation in the input commands: 
###   > sort(T1, [R1_time, S_C]) // sort T1 by R_itemid, S_C (in that order)
def sort(args):
    (tableName, sortCols) = (args[0], args[1:])
    (table, colDic) = (tableDic[tableName][0], tableDic[tableName][1])
    newcolDic, typeLs = {}, []
    for key in colDic.keys():
        colName = key.split(".")[1]
        newcolDic[colName] = colDic[key]
        t = (colName, integer) if type(table[colName][0])==np.dtype(integer) else (colName, string)
        typeLs.append(t)
    newTable = np.sort(table, order=sortCols, axis=0)
    return (newTable, newcolDic)


# In[28]:


### - what this function does: 
###   > perform the N item moving average of given table on given column
### - what its inputs are/mean: 
###   > args: a list storing the arguments given in the input command. Should include the following elements:
###   >> tableName: name of table that we are dealing
###   >> colName: name of column that we should perform on
###   >> N: means we should perform N item moving average 
### - what the outputs are/mean: 
###   > (newTable, colDic): storing the newTable itself and its column dictionary, colDic.
### - any side eﬀects to globals:
###   > No
### - Example operation in the input commands: 
###   > movavg(T2prime, R1_qty, 3) 
def movAvg(args):
    (tableName, colName, N) = (args[0], args[1], args[2])
    (table, colDic) = (tableDic[tableName][0], tableDic[tableName][1])
    N = int(N)
    newcolDic, typeLs = {}, []
    i = 0
    for key in colDic.keys():
        key = key.split(".")[1]
        newcolDic[key] = i
        t = (key, integer) if type(table[key][0])==np.dtype(integer) else (key, string)
        typeLs.append(t)
        i += 1    
    newcolDic["movAvg("+colName+")"] = i
    typeLs.append(("movAvg("+colName+")", FLOAT))
    newTable = np.zeros(table.shape[0], dtype=typeLs)
    for i in range(table.shape[0]):
        if i < N-1:
            newTable["movAvg("+colName+")"][i] = np.average(table[colName][0:i+1])
        else:
            newTable["movAvg("+colName+")"][i] = np.average(table[colName][i+1-N:i+1])
        for key in colDic.keys():
            key = key.split(".")[1]
            newTable[key][i] = table[key][i]
    return (newTable, newcolDic)   


# In[29]:


### - what this function does: 
###   > perform the N item moving sum of given table on given column
### - what its inputs are/mean: 
###   > args: a list storing the arguments given in the input command. Should include the following elements:
###   >> tableName: name of table that we are dealing
###   >> colName: name of column that we should perform on
###   >> N: means we should perform N item moving sum 
### - what the outputs are/mean: 
###   > (newTable, colDic): storing the newTable itself and its column dictionary, colDic.
### - any side eﬀects to globals:
###   > No
### - Example operation in the input commands: 
###   > movsum(T2prime, R1_qty, 5) 
def movSum(args):
    (tableName, colName, N) = (args[0], args[1], args[2])
    N = int(N)
    (table, colDic) = (tableDic[tableName][0], tableDic[tableName][1])
    newcolDic, typeLs = {}, []
    i = 0
    for key in colDic.keys():
        key = key.split(".")[1]
        newcolDic[key] = i
        t = (key, integer) if type(table[key][0])==np.dtype(integer) else (key, string)
        typeLs.append(t)
        i += 1    
    newcolDic["movSum("+colName+")"] = i
    typeLs.append(("movSum("+colName+")", FLOAT))
    newTable = np.zeros(table.shape[0], dtype=typeLs)
    for i in range(table.shape[0]):
        if i < N-1:
            newTable["movSum("+colName+")"][i] = np.sum(table[colName][0:i+1])
        else:
            newTable["movSum("+colName+")"][i] = np.sum(table[colName][i+1-N:i+1])
        for key in colDic.keys():
            key = key.split(".")[1]
            newTable[key][i] = table[key][i]
    return (newTable, newcolDic)   


# In[30]:


### - what this function does: 
###   > create an (BTree) index on given table based on given column
### - what its inputs are/mean: 
###   > args: a list storing the arguments given in the input command. Should include the following elements:
###   >> tableName: name of table that we are creating index on
###   >> colName: name of column that we based on
### - what the outputs are/mean: 
###   > None
### - any side eﬀects to globals:
###   > update idxDic so that we can find the index with a given key, (tableName, colName).
### - Example operation in the input commands: 
###   > Btree(R, qty) 
def Btree(args):
    (tableName, colName) = (args[0], args[1])
    table = tableDic[tableName][0]
    myBTree = OOBTree()
    for index in range(table.shape[0]):
        if myBTree.get(table[colName][index]) == None:
            myBTree[table[colName][index]] = []
        myBTree[table[colName][index]].append(index)    
    idxDic[(tableName, colName)] = myBTree


# In[31]:


### - what this function does: 
###   > create an (Hash) index on given table based on given column
### - what its inputs are/mean: 
###   > args: a list storing the arguments given in the input command. Should include the following elements:
###   >> tableName: name of table that we are creating index on
###   >> colName: name of column that we based on
### - what the outputs are/mean: 
###   > None
### - any side eﬀects to globals:
###   > update idxDic so that we can find the index with a given key, (tableName, colName).
### - Example operation in the input commands: 
###   > Hash(R,itemid)
def Hash(args):
    (tableName, colName) = (args[0], args[1])
    table = tableDic[tableName][0]
    myHash = {}
    for index in range(table.shape[0]):
        if myHash.get(table[colName][index]) == None:
            myHash[table[colName][index]] = []
        myHash[table[colName][index]].append(index)
    idxDic[(tableName, colName)] = myHash


# In[32]:


### - what this function does: 
###   > concatenate two given tables if they have same schema
###   > NOTE: duplicate rows may result
### - what its inputs are/mean: 
###   > args: a list storing the arguments given in the input command. Should include the following elements:
###   >> t1Name, t2Name: names of tables that we are dealing
### - what the outputs are/mean: 
###   > (newTable, colDic): storing the newTable itself and its column dictionary, colDic.
### - any side eﬀects to globals:
###   > No
### - Example operation in the input commands: 
###   > concat(Q4, Q2) 
def concat(args):
    (t1Name, t2Name) = (args[0], args[1])
    table1, table2 = tableDic[t1Name][0], tableDic[t2Name][0]
    newcolDic = {}
    newTable = np.array([])
    if table1.dtype == table2.dtype:
        colDic1 = tableDic[t1Name][1]
        for key in colDic1.keys():
            newcolDic[key.split(".")[1]] = colDic1[key]
        newTable = np.concatenate((table1, table2), axis=0)
    return (newTable, newcolDic)


# In[33]:


### - what this function does: 
###   > output the given table into a file with given name and with vertical bar separators
### - what its inputs are/mean: 
###   > args: a list storing the arguments given in the input command. Should include the following elements:
###   >> tableName: names of tables that we are dealing
###   >> fName: name of the output file
### - what the outputs are/mean: 
###   > None
### - any side eﬀects to globals:
###   > No
### - Example operation in the input commands: 
###   > outputtofile(Q5, Q5) 
def outputToFile(args):
    (tableName, fName) = (args[0], args[1])
    (table, colDic) = (tableDic[tableName][0], tableDic[tableName][1])
    f = open("lih238_"+fName+".txt", "w")
    if False:
        ### for a header of column names:
        header = [None] * len(colDic)
        for key in colDic.keys():
            header[colDic[key]] = key
        for i in range(len(header)):
            f.write(header[i])
            if i != len(header) - 1:
                f.write("|")
        f.write("\n")
    for record in table:
        for i in range(len(record)):
            col = record[i]
            f.write(str(col).strip())
            if i != len(record)-1:
                f.write("|")
        f.write("\n")
    f.close()


# In[34]:


### This sould be moving to the front? the function definitions should be moving down? how to declare a function first in Python?
operation = {"inputfromfile": inputFromFile,
            "select": select,
            "project": project,
            "count": count,
            "sum": sum,
            "avg": avg,
            "sumgroup": sumGroup,
            "avggroup": avgGroup,
            "countgroup": countGroup,
            "join": join,
            "sort": sort,
            "movavg": movAvg,
            "movsum": movSum,
            "btree": Btree,
            "hash": Hash,
            "concat": concat,
            "outputtofile": outputToFile}

### - what this function does: 
###   > run the operations in "input.txt", and record the costing time (and results) of each operation
### - what its inputs are/mean: 
###   > "input.txt"/stdin: the operations that we want to run
### - what the outputs are/mean: 
###   > "<netid>_ALLOperations.txt": all operation results and timing records.
def mainfunc():
    #r = open("input.txt", "r")    
    ### or take operations from stdin:
    r = sys.stdin
    f = open("lih238_AllOperations.txt", "w")
    for line in r:
        time_start = time.time()
        time_start1 = time.process_time()
        time_start2 = time.perf_counter()        
        line = line.split("//")[0]
        if not line.strip():
            continue            
        newTName = ""
        if line.find(":=") != -1:
            line_split = line.split(":=")
            newTName, line = line_split[0].strip(), line_split[1].strip()
        s = line.find("(")
        line_split = [line[:s], line[s+1:]]
        func, s = line_split[0].lower(), line_split[1].rfind(")")
        if func == "stop":
            return
        line_split[1] = line_split[1][:s]
        args = line_split[1].split(",")
        for i in range(len(args)):    ### for arg in args only changes the copy!
            args[i] = args[i].strip().strip("'").strip('"')
        s = "Now operating: " + func + " with arguments--" + str(args) + "\n"
        print(s)
        f.write(s)
        try:
            result = operation[func](args)
        except:
            result = [None, None]
            print("Error!\n")
            f.write("Error!\n")
        time_stop = time.time()
        time_stop1 = time.process_time()
        time_stop2 = time.perf_counter()
        ### generating the timing result
        s = "time.time()         diff: {:6f} sec\n".format(time_stop - time_start)
        f.write(s)
        s = "time.process_time() diff: {:6f} sec\n".format(time_stop1 - time_start1)
        f.write(s)
        s = "time.perf_counter() diff: {:6f} sec\n".format(time_stop2 - time_start2)
        f.write(s)
        if result == [None, None]:
            continue
        ### generating the resulting table
        if newTName:
            createT(newTName, result)
            (table, colDic) = (result[0], result[1])
            s = "New table created: {0} ( {1:d} rows)\n".format(newTName, table.shape[0])
            f.write(s)
            ### for a header of column names:
            header = [None] * len(colDic)
            for key in colDic.keys():
                header[colDic[key]] = key
            for i in range(len(header)):
                f.write(header[i])
                if i != len(header) - 1:
                    f.write("|")
            f.write("\n")
            for record in table:
                for i in range(len(record)):
                    col = record[i]
                    f.write(str(col).strip())
                    if i != len(record)-1:
                        f.write("|")
                f.write("\n")
    f.close()
    return


# In[ ]:


mainfunc()
print(tableDic.keys())
print(idxDic.keys())

