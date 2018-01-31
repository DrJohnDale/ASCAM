import numpy as np

def piezo_selection(time, piezo, trace, active = True, deviation = 0.05):
    """
    Selects part of the episode based on the Piezo voltage.
    The selection is done by choosing extracting the data from those time
    points where the value of the piezo voltage is either within a certain
    range (percentage wise) of the maximum or below a certain percentage 
    of the maximum.
    Works in relative terms, i.e. it does not matter if piezo voltage is
    positive or negative. Only works for blocks of the same amplitude.
    Parameters:
        time [1D array of floats] - Vector containing the time points.
        piezo [1D array of floats] - Vector of piezo voltages.
        trace [1D array of floats] - Vector of current trace.
        active [boolean] - If true return time points at which piezo 
                           voltage is within `deviation` percent of the 
                           maximum piezo voltage.
        deviation [float] - Deviation, as a percentage, from the maximum
                            piezo voltage or threshold below which voltage
                            should be.
    Returns:
        time [1D array of floats] - The timestamps of the selected points.
        piezo [1D array of floats] - The piezo voltage at selected points.
        trace [1D array of floats] - The current at selected points.
    """
    maxPiezo = np.max(np.abs(piezo))
    if active:
        indices = np.where((maxPiezo-np.abs(piezo))/maxPiezo<deviation)
    else:
        indices = np.where(np.abs(piezo)/maxPiezo<deviation)
    time = time[indices]
    piezo = piezo[indices]
    trace = trace[indices] 
    return time, piezo, trace

def interval_selection(time, signal, intervals, fs, timeUnit):
    """
    return the signal at the times specified in the interval
    """
    if timeUnit == 'ms':
        timeUnit = 1000
    elif timeUnit == 's':
        timeUnit = 1
    time_out = []
    signal_out = []
    if type(intervals[0]) is list:
        for ival in intervals:
            time_out.extend(time[ int(ival[0]*fs/timeUnit) 
                           : int(ival[-1]*fs/timeUnit) ])
            signal_out.extend(signal[ int(ival[0]*fs/timeUnit) 
                             : int(ival[-1]*fs/timeUnit)])
    elif type(intervals[0]) in [int, float]:
        time_out = time[ int(intervals[0]*fs/timeUnit)
                   : int(intervals[-1]*fs/timeUnit)]
        signal_out = signal[int(intervals[0]*fs/timeUnit)
                   : int(intervals[1]*fs/timeUnit)]
    return time_out, signal_out

def stringList_parser(list_as_string):
    whole_list = []
    current_list = []
    num_string = ''
    for char in list_as_string:
        if char == '[':
            current_list = []
        elif char == ',':
            if len(current_list) == 0:
                current_list.append(float(num_string))
            num_string = ''
        elif char == ']':
            current_list.append(float(num_string))
            whole_list.append(current_list)
        else:
            num_string += char
    return whole_list