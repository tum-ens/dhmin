""" DHMINTOOLS: utility functions specifically for DHMIN models

This package contains helper functions for pre- and postprocessing data for and
from a DHMIN model that will help to shorten script files (like rundh.py) and 
are to be used among scenarios.

"""
import matplotlib.pyplot as plt
import pandas as pd
import dhmin

def plot_flows_min(model):
    """ Plot power flows for minimal example.
    
    Creates a minimal visualisation of the `mnl.xlsx` model provided with
    DHMIN.
    """
    
    power_flows = dhmin.get_entities(model, ['Pin', 'Pot'])
    power_flows_grouped = power_flows.groupby(level='timesteps')
    
    power_input = dhmin.get_entity(model, 'Q')
    power_input_grouped = power_input.groupby(level='timesteps')
    
    plt.figure()
    for i, (name, group) in enumerate(power_flows_grouped):
        plt.subplot(2,3,i+1)
        plt.title(name)
        plt.xlim(0, 10)
        plt.ylim(0, 10)
        for key, value in group['Pin'].iterkv():
            x = [int(key[0]/10), int(key[1]/10)]
            y = [key[0]%10, key[1]%10]
            z = 2 if value > 1 else 1 # show grey lines behind red ones
            w = max(0.5, value/80)
            colour = '#ff5500' if value > 1 else '#cccccc'
            plt.plot(x, y, linewidth=w, color=colour, zorder=z, solid_capstyle='round') 
        #group['Pin'].plot()
        
        Q = power_input_grouped.get_group(name)['Q']
        for key, value in Q.iteritems():
            x = int(key[0]/10)
            y = key[0]%10
            z = 3
            w = max(0, value/4)
            colour = '#990000' if value > 1 else '#ffffff'
            plt.scatter(x, y, zorder=z, s=w, facecolors=colour, edgecolors='none', linewidths=0)
    plt.show()
    
    
def symmetrize(df):
    """ Make a directed quantity (like y, Pin, Pot) symmetric (like Pmax or x).
    
    Args:
        df: a dataframe with 2-element tuple index of (i,j) node pairs
        
    Returns:
        Symmetrized dataframe, where each element (i,j) is calculated as the 
        sum df(i,j) + df(j,i), assuming 0 for non-existing values.
        
    Example
    
    """
    df_tmp = pd.DataFrame(df)
    original_index_levels = df_tmp.index.names
    df_tmp.index.names = original_index_levels[::-1] # swap levels 
    df_tmp = df_tmp.reorder_levels(original_index_levels)
    df.index.names = original_index_levels # restore original index (!)
    df_symmetric = df.add(df_tmp, fill_value=0)
    return df_symmetric

