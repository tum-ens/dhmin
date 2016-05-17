try:
    import pyomo.environ
    from pyomo.opt.base import SolverFactory
    PYOMO3 = False
except ImportError:
    import coopr.environ
    from coopr.opt.base import SolverFactory
    PYOMO3 = True
import dhmin
import dhmintools
import pandas as pd
import pandashp as pdshp
import pandaspyomo as pdpo
import pyomotools
from coopr.opt.base import SolverFactory
from operator import itemgetter

# config
data_file = 'mnl.xlsx'
params = {'r_heat':0.07} # only specify changed values
timesteps = [(1600,.8),(1040,.5)] # list of (duration [hours], scaling_factor) tuples
                              # annual fulload hours = sum(t, duration[t]*sf[t]) = 1800

     
# read vertices and edges from Excel data_file
# lines 2 and 3 are just a fancy way of writing
# vertex = dfs['Vertex']
# edge = dfs['Edge']
# while scaling better when the number of spreadsheets increase
dfs = pyomotools.read_xls(data_file)
vertex, edge = dfs['Vertex'], dfs['Edge']

# get model
# create instance
# solver interface (GLPK)
prob = dhmin.create_model(vertex, edge, params, timesteps)
if PYOMO3:
    prob = prob.create()
solver = SolverFactory('glpk')
result = solver.solve(prob, timelimit=30)
if PYOMO3:
    prob.load(result)

# use special-purpose function to plot power flows
dhmintools.plot_flows_min(instance)

