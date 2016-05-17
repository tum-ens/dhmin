import dhmin
import dhmintools
import geopandas
import pyomo.environ
from pyomo.opt.base import SolverFactory

# config
vertex_file = 'shp/mnl/vertex.shp'
edge_file = 'shp/mnl/edge.shp'
params = {'r_heat':0.07} # only specify changed values
timesteps = [(1600,.8),(1040,.5)] # list of (duration [hours], scaling_factor) tuples
                              # annual fulload hours = sum(t, duration[t]*sf[t]) = 1800
     
# read vertices and edges from shapefiles...
vertex = geopandas.read_file(vertex_file)
edge = geopandas.read_file(edge_file)
# ... and set indices to agree with Excel format
vertex.set_index(['Vertex'], inplace=True)
edge.set_index(['Edge', 'Vertex1', 'Vertex2'], inplace=True)

# at this point, rundh.py and rundhshp.py work identically!
# dhmin.create_model must not rely on vertex/edge DataFrames to contain any
# geometry information

# get model
# create instance
# solver interface (GLPK)
prob = dhmin.create_model(vertex, edge, params, timesteps)
solver = SolverFactory('glpk')
result = solver.solve(prob, timelimit=30, tee=True)
prob.solutions.load_from(result)

# use special-purpose function to plot power flows (works unchanged!)
dhmintools.plot_flows_min(prob)

# read time-independent variable values to DataFrame
# (list all variables using dhmin.list_entities(instance, 'variables')
caps = dhmin.get_entities(prob, ['Pmax', 'x'])
costs = dhmin.get_entity(prob, 'costs')

# remove Edge from index, so that edge and caps are both indexed on
# (vertex, vertex) tuples, i.e. their indices match for identical edges
edge.reset_index('Edge', inplace=True)

# change index names to 'Vertex1', 'Vertex2' from auto-inferred labels 
# 'vertex','vertex_'
caps.index.names = edge.index.names.copy()

# join optimal capacities with edge for geometry
edge_w_caps = edge.join(caps)
edge_w_caps.to_file('shp/mnl/edge_w_caps.shp')