# Miniature Relational Database with Order
A program that performs basic operations of relational algebra.  
Built with Python.

Given ordered tables (array-tables) whose rows consist of strings and integers, this program could:  
- take operations from standard input:
  - each operation should be on a single line. 
  - each time a line is executed, the time it took to execute would be printed.
  - comparators for select and join will be `=, <, >, !=, <=, >=`
  - comments begin with `//` and go to the end of the line.
  - see __input.txt__ for examples.
- perform the basic operations of relational algebra: 
  - selection, 
  - projection, 
  - join, 
  - group by, and 
  - count, sum and avg aggregates.  
- sort an array-table by one or more columns
- run moving sums and average aggregates on a column of an array-table.
- assign the result of a query to an array-table.
- import a vertical bar delimited ﬁle into an array-table (in the same order). For example:
  ```
  saleid|itemid|customerid|storeid|time|qty|pricerange
  45|133|2|63|49|23|outrageous
  658|75|2|89|46|43|outrageous
  149|103|2|23|67|2|cheap
  398|82|2|41|3|27|outrageous
  147|81|2|4|92|11|outrageous
  778|75|160|72|67|17|supercheap
  829|112|2|70|63|43|supercheap
  101|105|2|9|74|28|expensive
  ```
- export from an array-table to a ﬁle preserving its order.
- support in memory B-trees and hash structures. 

## Getting Started
These instructions will get you a copy of the project up and running on your local machine for development and testing purposes. 

### Prerequisites
- python
- PyPY BTrees package (4.6.1): use `pip install BTrees` to install it. (https://pypi.org/project/BTrees/)

### Executing
1. Put input files for inputfromfile functions (e.g. "sales1.txt") into the same directory as the the source code(.py) file.
2. Execute the .py file `python lih238.py < "{input.txt}"`
3. Output:  
    1. lih238_AllOperations.txt (a file with all operations' results): 
      - if the operation failed to execute, there will be an "Error!\n" message printed on the console and also written in this file
      - the record of each operation includes:
        - the first line indicate the operations executed.
        - the second part is 3 lines presenting the timing results,  
          showing 3 different results generating from different timimng methods in python <time> module.
        - if there are new table created, it printed the table name(#rows), the header and the whold table. 
        - For example:
          ```
          Now operating: inputfromfile with arguments--['sales1']
          time.time()         diff: 0.149186 sec
          time.process_time() diff: 0.092450 sec
          time.perf_counter() diff: 0.149189 sec
          New table created: R ( 1000 rows)
          saleid|itemid|customerid|storeid|time|qty|pricerange
          36|14|2|38|49|15|moderate
          784|90|182|97|46|31|moderate
          801|117|2|43|81|14|outrageous
          ...
          ```
    2. outputtofile operation results

## Running the tests
1. run `python lih238.py < "input.txt"` to see if the program works properly.
2. run `python lih238.py < "input2.txt"`, this might take 1-2 hours to run.
