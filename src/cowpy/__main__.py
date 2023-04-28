from .cowpy import Cowpy
import sys 

if len(sys.argv) > 1:

    if sys.argv[1] == "-c":

        if len(sys.argv) < 3:
            print("Please provide a file to check")
            sys.exit(1)
        file_to_check = sys.argv[2]
        print(f'Checking {file_to_check}')
        
        _cowpy = Cowpy()
        _cowpy.check(file_to_check)

    else:

        print(f'{sys.argv[1]} is not recognized')