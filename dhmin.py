""" DHMIN: a weakly temporal district heating topology optimization model

"""

import warnings
try:
    import pyomo.core as pyomo
except ImportError:
    import coopr.pyomo as pyomo
    warnings.warn("Support for Pyomo 3.x is now deprecated and will be removed"
                  "removed with the next release. Please upgrade to Pyomo 4.",
                  FutureWarning, stacklevel=2)
import numpy as np
import pandas as pd


def read_excel(filename):
    """Read input Excel file and return dict of DataFrames for each sheet.
    
    Read an Excel spreadsheet with geographic input data.
    
    Args:
        filename: filename to an Excel spreadsheet with 'Vertex' and 'Edge'
        
    Returns:
        dict of 2 pandas DataFrames
    """
    with pd.ExcelFile(filename) as xls:
        vertex = xls.parse('Vertex').set_index('Vertex')
        edge = xls.parse('Edge').set_index(['Edge', 'Vertex1', 'Vertex2'])
    data = {
        'Vertex': vertex,
        'Edge': edge}
    return data

def create_model(vertex, edge, params={}, timesteps=[]):
    """return a DHMIN model instance from nodes and edges DataFrame
    
    Args:
        vertex: DataFrame of vertex with index and attributes
        edges: DataFrame of edges with (Vertex1, Vertex2) MultiIndex and attributes
        params: dict of cost and technical parameters
        timesteps: list of timestep tuples (duration, scaling factor)
    Returns:
        m: a coopr.pyomo ConcreteModel object
    Usage: 
        see rundh.py
    
    The optional argument params can be used to specify any of the 
    technical and cost parameters.
    
    The optional argument timesteps is given, DHMIN is run in multi-
    seasonal mode that includes a simplified time model. Each (t,p)
    tuple encodes a time interval of length (1 hour)*t and relative
    peak power requirement (peak)*p of all consumers. Note that sum(t)
    must be equal to 8760. The inequalities 0 <= t <= 8760 and 0 <= p <= 1
    are to be respected.

    """
    m = pyomo.ConcreteModel()
    m.name = 'DHMIN'
    
    # DATA PREPARATION
    
    tech_parameters = {
        'c_fix': 600, # (€/m) fixed pipe investment
        'c_var': 0.015, # (€/kW/m) variable pipe investment
        'c_om': 5, # (€/m) operation & maintenance
        'r_heat': 0.07, # (€/kWh) retail price for heat
        'annuity': anf(40, 0.06), # (%) annuity factor (years, interest)
        'thermal_loss_fix': 20e-3, # (kW/m) fixed thermal losses
        'thermal_loss_var': 1e-7, # (kW/kW/m) variable thermal losses
        'concurrence': 1, # (%) concurrence effect
        } 
    
    # Entity edge contains column 'Edge' as index. This model (in contrast to
    # the old GAMS version) does not use the 'Edge' ID on its own, so remove the
    # edge ID from the index ('Edge', 'Vertex1', 'Vertex2')
    edges = edge.reset_index('Edge')
            
    # replace default parameter values with user-defined ones, if specified
    tech_parameters.update(params)
    
    # make edges symmetric by duplicating each row (i,j) to (j,i)
    edges_tmp = edges
    edges_tmp.index.names = ['Vertex2', 'Vertex1']
    edges_tmp = edges_tmp.reorder_levels(['Vertex1', 'Vertex2'])
    edges = edges_tmp.append(edges, verify_integrity=True)
    del edges_tmp
    
    # derive list of neighbours for each vertex
    m.neighbours = {}
    for (i, j) in edges.index:
        m.neighbours.setdefault(i, [])
        m.neighbours[i].append(j)
        
    #
    m.vertices = vertex.copy()
    m.edges = edges.copy()
    
    cost_types = [
        'network', # pipe construction, maintenance
        'heat', # heating plants, operation
        'revenue', # sold heat
        ]
    
    # derive subset of source vertices, i.e. those with column 'init' set to 1
    source_vertex = vertex[vertex.init == 1].index

    # timestep preparation
    if timesteps:
        # extend timesteps with (name, duration, scaling factor) tuples and
        # add a near-zero (here: 1 hour) legnth, nominal power timestep 'Pmax'
        timesteps = [('t{}'.format(t[0]), t[0], t[1]) for t in timesteps]
        timesteps.append(('Pmax', 1 , 1))
        
        # now get a list of all source nodes
        # for each source, add a non-availability timestep ('v0', 1, 1)
        # and set availability matrix so that 'v0' is off in that timestep
        availability = np.ones((len(timesteps) + len(source_vertex), 
                                len(source_vertex)), 
                               dtype=np.int)
        
        for i, v0 in enumerate(source_vertex):
            availability[len(timesteps), i] = 0
            timesteps.append(('v{}'.format(v0), 1, 1))
    else:
        # no timesteps: create single dummy timestep with 100% availability
        timesteps = [('t0', 1, 1)]
        availability = np.ones((1, 
                                len(source_vertex)), 
                               dtype=np.int)
     
    # MODEL
    
    # Sets
    m.vertex = pyomo.Set(initialize=vertex.index)
    m.edge = pyomo.Set(within=m.vertex*m.vertex, initialize=edges.index)
    m.cost_types = pyomo.Set(initialize=cost_types)
    m.tech_params = pyomo.Set(initialize=tech_parameters.keys())
    m.timesteps = pyomo.Set(initialize=[t[0] for t in timesteps])
    m.source_vertex = pyomo.Set(initialize=source_vertex)
    
    # Parameters
    m.tech_parameters = pyomo.Param(m.tech_params, initialize=tech_parameters)
    
    # derive delta and eta from edge attributes
    m.delta = pyomo.Param(m.edge, initialize=dict(
                    edges['peak'] 
                        * edges['cnct_quota']
                        * tech_parameters['concurrence'] +
                    edges['length']
                        * tech_parameters['thermal_loss_fix']
                    ))
    m.eta = pyomo.Param(m.edge, initialize=dict(
                  1 - (edges['length']
                       * tech_parameters['thermal_loss_var'])
                  ))
    
    # cost coefficients for objective function
    
    # k_fix: power-independent investment and operation & maintenance costs for 
    # pipes (EUR/a)
    m.k_fix = pyomo.Param(m.edge, initialize=dict(
                    edges['length']
                        * 0.5 # x and Pmax are forced in both directions (i,j),(j,i)
                        * tech_parameters['c_fix'] 
                        * tech_parameters['annuity']
                        * (1 - edges['pipe_exist']) +
                    edges['length']
                        * 0.5 # x and Pmax are forced in both directions (i,j),(j,i)
                        * tech_parameters['c_om']
                    ))
    
    # k_var: power-dependent pipe investment costs (EUR/kW/a)
    m.k_var = pyomo.Param(m.edge, initialize=dict(
                    edges['length']
                        * 0.5 # x and Pmax are forced in both directions (i,j),(j,i)
                        * tech_parameters['c_var'] 
                        * tech_parameters['annuity']
                        * (1- edges['pipe_exist'])
                    ))
    
    # k_heat: costs for heat generation (EUR/h)
    # as the source-term for power flow is lowered by concurrence effect (cf.
    # m.delta), for conversion to energy integral, it must be removed again
    m.k_heat = pyomo.Param(m.vertex, initialize=dict(
                     vertex['cost_heat']
                        / tech_parameters['concurrence']
                     ))
    
    # r_heat: revenue for heat delivery (EUR/h)
    #
    m.r_heat = pyomo.Param(m.edge, initialize=dict(
                     edges['peak']
                        * 0.5 # x and Pmax are forced in both directions (i,j),(j,i)
                        * edges['cnct_quota']
                        * tech_parameters['r_heat']
                     ))
    m.availability = pyomo.Param(m.source_vertex, m.timesteps, initialize={
            (s,t[0]): availability[x,y]
            for y,s in enumerate(source_vertex)
            for x,t in enumerate(timesteps)
            })
    m.dt = pyomo.Param(m.timesteps, initialize={t[0]:t[1] for t in timesteps})
    m.scaling_factor = pyomo.Param(m.timesteps, initialize={t[0]:t[2] for t in timesteps})
    
    # Variables
    m.costs = pyomo.Var(m.cost_types)
    m.x = pyomo.Var(m.edge, within=pyomo.Binary)
    m.Pmax = pyomo.Var(m.edge, within=pyomo.NonNegativeReals)

    m.Pin = pyomo.Var(m.edge, m.timesteps, within=pyomo.NonNegativeReals)
    m.Pot = pyomo.Var(m.edge, m.timesteps, within=pyomo.NonNegativeReals)
    m.Q = pyomo.Var(m.vertex, m.timesteps, within=pyomo.NonNegativeReals)
    m.y = pyomo.Var(m.edge, m.timesteps, within=pyomo.Binary)
    
    m.energy_conservation = pyomo.Constraint(
        m.vertex, m.timesteps,
        doc='Power flow is conserved in vertex',
        rule=energy_conservation_rule)
    m.demand_satisfaction = pyomo.Constraint(
        m.edge, m.timesteps,
        doc='Peak demand (delta) must be satisfied in edge, if pipe is built',
        rule=demand_satisfaction_rule)
    m.pipe_capacity = pyomo.Constraint(
        m.edge, m.timesteps,
        doc='Power flow is smaller than pipe capacity Pmax',
        rule=pipe_capacity_rule)
    m.pipe_usage = pyomo.Constraint(
        m.edge, m.timesteps,
        doc='Power flow through pipe=0 if y[i,j,t]=0',
        rule=pipe_usage_rule)
    m.must_build = pyomo.Constraint(
        m.edge,
        doc='Pipe must be built if must_build == 1',
        rule=must_build_rule)
    m.build_capacity = pyomo.Constraint(
        m.edge, 
        doc='Pipe capacity Pmax must be smaller than edge attribute cap_max',
        rule=build_capacity_rule)
    m.unidirectionality = pyomo.Constraint(
        m.edge, m.timesteps, 
        doc='Power flow only in one direction per timestep',
        rule=unidirectionality_rule)
    m.symmetry_x = pyomo.Constraint(
        m.edge, 
        doc='Pipe may be used in both directions, if built',
        rule=symmetry_x_rule)
    m.symmetry_Pmax = pyomo.Constraint(
        m.edge, 
        doc='Pipe has same capacity in both directions, if built',
        rule=symmetry_Pmax_rule)
    m.built_then_use = pyomo.Constraint(
        m.edge, m.timesteps, 
        doc='Demand must be satisfied from at least one direction, if built',
        rule=built_then_use_rule)
    m.source_vertices = pyomo.Constraint(
        m.vertex, m.timesteps,
        doc='Non-zero source term Q is only allowed in source vertices',
        rule=source_vertices_rule)
    
    # Objective
    m.def_costs = pyomo.Constraint(
        m.cost_types,
        doc='Cost definitions by type',
        rule=cost_rule)
    m.obj = pyomo.Objective(
        sense=pyomo.minimize,
        doc='Minimize costs = network + heat - revenue',
        rule=obj_rule)

    return m


# Constraints
def energy_conservation_rule(m, i, t):
    return sum(m.Pin[i,k,t] - m.Pot[k,i,t] for k in m.neighbours[i]) <= m.Q[i,t]
    
def demand_satisfaction_rule(m, i, j, t):
    return m.Pot[i,j,t] == \
           m.Pin[i,j,t] * m.eta[i,j] - \
           m.y[i,j,t] * m.delta[i,j] * m.scaling_factor[t]

def pipe_capacity_rule(m, i, j, t):
    return m.Pin[i,j,t] <= m.Pmax[i,j]
    
def pipe_usage_rule(m, i,j ,t):
    return m.Pin[i,j,t] <= m.y[i,j,t] * m.edges.ix[i,j]['cap_max']
    
def must_build_rule(m, i, j):
    return m.x[i,j] >= m.edges.ix[i,j]['must_build']

def build_capacity_rule(m, i, j):
    return m.Pmax[i,j] <= m.x[i,j] * m.edges.ix[i,j]['cap_max']

def unidirectionality_rule(m, i, j, t):
    return m.y[i,j,t] + m.y[j,i,t] <= 1
           
def symmetry_x_rule(m, i, j):
    return m.x[i,j] == m.x[j,i]
    
def symmetry_Pmax_rule(m, i, j):
    return m.Pmax[i,j] == m.Pmax[j,i]
    
def built_then_use_rule(m, i, j, t):
    return m.y[i,j,t] + m.y[j,i,t] >= (m.x[i,j] + m.x[j,i]) / 2
    
def source_vertices_rule(m, i, t):
    if i in m.source_vertex:
        return m.Q[i,t] <= m.vertices.ix[i]['capacity'] * m.availability[i,t]
    else:
        return m.Q[i,t] <= 0

# minimize total costs (network + heat - revenue)
def cost_rule(m, cost_type):
    if cost_type == 'network':
        return m.costs['network'] == \
                sum(m.k_fix[i,j] * m.x[i,j] + 
                    m.k_var[i,j] * m.Pmax[i,j] 
                    for (i,j) in m.edge)
    elif cost_type == 'heat':
        return m.costs['heat'] == \
                sum(m.k_heat[i] * m.Q[i,t] * m.dt[t]
                    for i in m.vertex 
                    for t in m.timesteps)
    elif cost_type == 'revenue':
        return m.costs['revenue'] == \
                - sum(m.r_heat[i,j] * m.x[i,j] * m.scaling_factor[t] * m.dt[t]
                    for (i,j) in m.edge
                    for t in m.timesteps)
    else:
        raise NotImplementedError("Unknown cost type!")

def obj_rule(m):
    return sum(m.costs[cost_type] for cost_type in m.cost_types)
    

def anf(n, i):
    """calculate annuity factor
    
    Args:
        n: depreciation period (40 = 40 years)
        i: interest rate (0.06 = 6%)
    Returns:
        annuity factor derived by formula (1+i)**n * i / ((1+i)**n - 1) 
    """
    return (1+i)**n * i / ((1+i)**n - 1)


def get_entity(instance, name):
    """ Return a DataFrame for an entity in model instance.

    Args:
        instance: a Pyomo ConcreteModel instance
        name: name of a Set, Param, Var, Constraint or Objective

    Returns:
        a single-columned Pandas DataFrame with domain as index
    """

    # retrieve entity, its type and its onset names
    entity = instance.__getattribute__(name)
    labels = _get_onset_names(entity)

    # extract values
    if isinstance(entity, pyomo.Set):
        # Pyomo sets don't have values, only elements
        results = pd.DataFrame([(v, 1) for v in entity.value])

        # for unconstrained sets, the column label is identical to their index
        # hence, make index equal to entity name and append underscore to name
        # (=the later column title) to preserve identical index names for both
        # unconstrained supersets
        if not labels:
            labels = [name]
            name = name+'_'

    elif isinstance(entity, pyomo.Param):
        if entity.dim() > 1:
            results = pd.DataFrame([v[0]+(v[1],) for v in entity.items()])
        else:
            results = pd.DataFrame(entity.items())
    else:
        # create DataFrame
        if entity.dim() > 1:
            # concatenate index tuples with value if entity has
            # multidimensional indices v[0]
            results = pd.DataFrame(
                [v[0]+(v[1].value,) for v in entity.items()])
        else:
            # otherwise, create tuple from scalar index v[0]
            results = pd.DataFrame(
                [(v[0], v[1].value) for v in entity.items()])

    # check for duplicate onset names and append one to several "_" to make
    # them unique, e.g. ['sit', 'sit', 'com'] becomes ['sit', 'sit_', 'com']
    for k, label in enumerate(labels):
        if label in labels[:k]:
            labels[k] = labels[k] + "_"

    if not results.empty:
        # name columns according to labels + entity name
        results.columns = labels + [name]
        results.set_index(labels, inplace=True)

    return results


def get_entities(instance, names):
    """ Return one DataFrame with entities in columns and a common index.

    Works only on entities that share a common domain (set or set_tuple), which
    is used as index of the returned DataFrame.

    Args:
        instance: a Pyomo ConcreteModel instance
        names: list of entity names (as returned by list_entities)

    Returns:
        a Pandas DataFrame with entities as columns and domains as index
    """

    df = pd.DataFrame()
    for name in names:
        other = get_entity(instance, name)

        if df.empty:
            df = other
        else:
            index_names_before = df.index.names

            df = df.join(other, how='outer')

            if index_names_before != df.index.names:
                df.index.names = index_names_before

    return df


def list_entities(instance, entity_type):
    """ Return list of sets, params, variables, constraints or objectives

    Args:
        instance: a Pyomo ConcreteModel object
        entity_type: "set", "par", "var", "con" or "obj"

    Returns:
        DataFrame of entities

    Example:
        >>> data = read_excel('mimo-example.xlsx')
        >>> model = create_model(data, range(1,25))
        >>> list_entities(model, 'obj')  #doctest: +NORMALIZE_WHITESPACE
                                         Description Domain
        Name
        obj   minimize(cost = sum of all cost types)     []

    """

    # helper function to discern entities by type
    def filter_by_type(entity, entity_type):
        if entity_type == 'set':
            return isinstance(entity, pyomo.Set) and not entity.virtual
        elif entity_type == 'par':
            return isinstance(entity, pyomo.Param)
        elif entity_type == 'var':
            return isinstance(entity, pyomo.Var)
        elif entity_type == 'con':
            return isinstance(entity, pyomo.Constraint)
        elif entity_type == 'obj':
            return isinstance(entity, pyomo.Objective)
        else:
            raise ValueError("Unknown entity_type '{}'".format(entity_type))

    # iterate through all model components and keep only
    iter_entities = instance.__dict__.items()
    entities = sorted(
        (name, entity.doc, _get_onset_names(entity))
        for (name, entity) in iter_entities
        if filter_by_type(entity, entity_type))

    # if something was found, wrap tuples in DataFrame, otherwise return empty
    if entities:
        entities = pd.DataFrame(entities,
                                columns=['Name', 'Description', 'Domain'])
        entities.set_index('Name', inplace=True)
    else:
        entities = pd.DataFrame()
    return entities


def _get_onset_names(entity):
    """ Return a list of domain set names for a given model entity
    
    Args:
        entity: a member entity (i.e. a Set, Param, Var, Objective, Constraint)
                of a Pyomo ConcreteModel object
                
    Returns:
        list of domain set names for that entity
        
    Example:
        >>> data = read_excel('mimo-example.xlsx')
        >>> model = create_model(data, range(1,25))
        >>> _get_onset_names(model.e_co_stock)
        ['t', 'sit', 'com', 'com_type']
    """
    # get column titles for entities from domain set names
    labels = []

    if isinstance(entity, pyomo.Set):
        if entity.dimen > 1:
            # N-dimensional set tuples, possibly with nested set tuples within
            if entity.domain:
                domains = entity.domain.set_tuple
            else:
                domains = entity.set_tuple

            for domain_set in domains:
                labels.extend(_get_onset_names(domain_set))

        elif entity.dimen == 1:
            if entity.domain:
                # 1D subset; add domain name
                labels.append(entity.domain.name)
            else:
                # unrestricted set; add entity name
                labels.append(entity.name)
        else:
            # no domain, so no labels needed
            pass

    elif isinstance(entity, (pyomo.Param, pyomo.Var, pyomo.Constraint,
                    pyomo.Objective)):
        if entity.dim() > 0 and entity._index:
            labels = _get_onset_names(entity._index)
        else:
            # zero dimensions, so no onset labels
            pass

    else:
        raise ValueError("Unknown entity type!")

    return labels

