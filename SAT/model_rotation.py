import os
import sys
import time
import numpy as np
from math import ceil
from z3 import Bool, And, Or, Not, Xor, Implies, Solver
from itertools import combinations
from src.SATsolver import read_variables, convert_z3_format


def get_h_range(w_board, w, h):

    area = sum(w[i] * h[i] for i in range(len(w)))
    h_min = max(max(h), ceil(area / w_board ))
    h_max = sum([max(h[i],w[i]) for i in range(len(w))])

    return np.arange(h_min, h_max)

def existence(variable, span, r_span, limit, n_circuits, r):
    e = And([
            Xor(
                Or([
                    And(
                        And([variable[c][j] for j in np.arange(span[c]) + i]), 
                        Not(r[c])
                        ) for i in range(limit - span[c] + 1)]
                    ),
                Or([
                    And(
                        And([variable[c][j] for j in np.arange(r_span[c]) + i]),
                        r[c]
                        ) for i in range(limit - r_span[c] + 1)]
                    )
                ) for c in range(n_circuits)]
            )
    return e


def strong_existence(variable, span, r_span, limit, n_circuits, r):
    e = And([
            Xor(
                Or([
                    And(
                        And([variable[c][j] for j in np.arange(span[c]) + i]), 
                        And([Not(variable[c][j]) for j in list(set(np.arange(limit)) - set(np.arange(span[c]) + i))]),
                        Not(r[c])
                        ) for i in range(limit - span[c] + 1)]
                    ),
                Or([
                    And(
                        And([variable[c][j] for j in np.arange(r_span[c]) + i]), 
                        And([Not(variable[c][j]) for j in list(set(np.arange(limit)) - set(np.arange(r_span[c]) + i))]),
                        r[c]
                        ) for i in range(limit - r_span[c] + 1)]
                    )
                ) for c in range(n_circuits)]
            )
    return e


def unicity(variable, span, limit, n_circuits):
    u = And([
            And([
                Not(
                    And(
                        And([variable[c][j] for j in np.arange(span[c]) + i]),
                        And([variable[c][j] for j in np.arange(span[c]) + j])
                        )
                    ) for i, j in combinations(np.arange(limit - span[c]), 2)]
                ) for c in range(n_circuits)]
            )          
    return u


def impenetrability(x, y, w_board, h_board, n_circuits):
    i = And([
                Implies(Or([And(x[c][s], x[k][s])  for s in range(w_board)]), 
                            And([ 
                                Not(And(y[c][i], y[k][i])) for i in range(h_board)] 
                                )
                        ) for c, k in combinations(np.arange(n_circuits), 2)]
            )
    return i


def get_first_index(solution, bool_variable, n_circuits):
    return  [[solution.eval(variable) for variable in bool_variable[c]].index(True) for c in range(n_circuits)]

def rotated(solution, r):
    return [solution.eval(i) for i in r]

    
def rotate_circuits(w, h, rc):
    for i in range(len(rc)):
        if rc[i] == True:
            w[i], h[i] = h[i], w[i]
    return w, h

def SAT_model(circuits_variables):

    n_circuits = circuits_variables["tot_circuits"]
    w_board = circuits_variables["plate_width"]

    w = circuits_variables["circuits_width"]
    h = circuits_variables["circuits_height"]
 
    h_range = get_h_range(w_board, w, h)

    for h_board in h_range:

        x = [[Bool(f"x[{c}][{w}]") for w in range(w_board)] for c in range(n_circuits)]
        y = [[Bool(f"y[{c}][{h}]") for h in range(h_board)] for c in range(n_circuits)]

        r = [Bool(f"rx[{c}]") for c in range(n_circuits)]

        # setting the constraints
        existence_x = existence(x, w, h, w_board, n_circuits, r)
        existence_y = existence(y, h, w, h_board, n_circuits, r)

        strong_existence_x = existence(x, w, h, w_board, n_circuits, r)
        strong_existence_y = existence(y, h, w, h_board, n_circuits, r)

        unicity_x = unicity(x, w, w_board, n_circuits)
        unicity_y = unicity(y, w, h_board, n_circuits)


        impenetrability_c= impenetrability(x, y, w_board, h_board, n_circuits)

        solver = Solver()

        # use only the configuration that gave best results on the non rotated problem
        solver.add(existence_x)
        solver.add(existence_y)

        #solver.add(strong_existence_x)
        #solver.add(strong_existence_y)
        #solver.add(unicity_x)
        #solver.add(unicity_y)


        solver.add(impenetrability_c)

        start = time.time()
        solved = solver.check()
        end = time.time()
        execution_time = end - start
        
        
        if str(solved) == 'sat':
            solution = solver.model()
            xc = get_first_index(solution, x, n_circuits)
            yc = get_first_index(solution, y, n_circuits)
            rc = rotated(solution, r)
            rotated_circuits = rotate_circuits(w,h,rc)
            circuits_variables["circuits_width"] = rotated_circuits[0]
            circuits_variables["circuits_height"] = rotated_circuits[1]
    
            return {'h_board': h_board, 'execution_time': execution_time, 'xc': xc, 'yc': yc}

    return "unsat"

if __name__ == "__main__":

    circuits_variables = read_variables(sys.argv[1])
    
    solution = SAT_model(circuits_variables)
    if solution == 'unsat':
        print('Problem is unsat')
    else:
        # if "solution" is different from "unsat", it will have the following structure: 
        # (h_board, execution_time, x coordinates of the BL corners, x coordinates of the BL corners)
        # x and y coordinates are organized in lists, with indexes refering to circuits according to the order
        # defined in w and h lists
        convert_z3_format(circuits_variables, solution, sys.argv[2])



