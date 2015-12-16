import coopr.environ
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
get_vertex_edge_from = itemgetter('Vertex', 'Edge')
(vertex, edge) = get_vertex_edge_from(dfs)

# get model
# create instance
# solver interface (GLPK)
model = dhmin.create_model(vertex, edge, params, timesteps)
instance = model.create()
solver = SolverFactory('glpk')
result = solver.solve(instance, timelimit=30)
instance.load(result)

# use special-purpose function to plot power flows
dhmintools.plot_flows_min(instance)

