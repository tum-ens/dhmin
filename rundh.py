import dhmin
import dhmintools
import pandas as pd
import pyomo.environ
from pyomo.opt.base import SolverFactory

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
data = dhmin.read_excel(data_file)
vertex, edge = data['Vertex'], data['Edge']

# get model
# create instance
# solver interface (GLPK)
prob = dhmin.create_model(vertex, edge, params, timesteps)
optim = SolverFactory('glpk')
prob.write('rundh.lp', io_options={'symbolic_solver_labels':True})
result = optim.solve(prob, timelimit=30, tee=True)
prob.solutions.load_from(result)

# use special-purpose function to plot power flows
dhmintools.plot_flows_min(prob)

