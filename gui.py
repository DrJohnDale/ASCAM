import tkinter as tk
from tkinter import ttk
from tkinter.filedialog import askopenfilename
import matplotlib
matplotlib.use('TkAgg')
import model as backend
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import (FigureCanvasTkAgg,
                                            NavigationToolbar2TkAgg)
import plotting
import time

VERBOSE = False
axotest = False
bintest = False
mattest = False

class GUI(ttk.Frame):
    """
    GUI frame of the GUI for ASCAM.
    All the variables and objects are stored as attributes of this
    object to make refering them uniform.
    All other widgets will be children of this frame.
    It is easier to make to represent floats and integers using tk.StringVar
    because then they can be entered in entry fields without problems
    """
    @classmethod
    def run(cls):
        root = tk.Tk()
        root.protocol('WM_DELETE_WINDOW', quit)
        root.title("ASCAM")
        root.grid_columnconfigure(0, weight=1)
        root.grid_rowconfigure(0, weight=1)
        GUI = cls(root)
        root.mainloop()

    def __init__(self, master):
        ttk.Frame.__init__(self, master)
        self.master = master

        ### parameters for loading of a file
        self.filenamefull = tk.StringVar()
        self.filename = tk.StringVar()
        self.headerlength = tk.StringVar()
        self.datatype = tk.StringVar()
        self.path = tk.StringVar()
        self.filetypefull = tk.StringVar()
        self.filetype = tk.StringVar()

        ### parameters for the histogram
        self.hist_number_bins = tk.StringVar()
        self.hist_density = tk.IntVar()
        self.hist_density.set(0)

        ### parameters of the data
        self.samplingrate = tk.StringVar()

        # dictionary for the data
        self.data = backend.Recording()
        # datakey of the current displayed data
        self.datakey = tk.StringVar()
        self.datakey.set('raw_')
        # episode number of the currently displayed episode
        self.Nepisode = 0

        self.create_widgets()
        self.configure_grid()

        self.commandbar.loadbutton.focus()

        self.listAssignFunctions = []
        ## this list will hold all the functions that are created to assign
        ## episodes to particular lists

        self.load_for_testing()
        ## if testing arguments have been given data will be loaded when the 
        ## program starts

        self.bind("<Configure>", self.update_plots)
        # this line calls `draw` when it is run

    def load_for_testing(self):
        if bintest:
        ### testing mode that uses simulated data, the data is copied and
        ### multiplied with random numbers to create additional episodes
            if VERBOSE:
                print('Test mode with binary data')
            self.data = backend.Recording(
                                    cwd+'/data/sim1600.bin', 4e4,
                                    'bin', 3072, np.int16)
            self.data['raw_'][0]['trace']=self.data['raw_'][0]['trace'][:9999]
            self.data['raw_'][0]['time']=self.data['raw_'][0]['time'][:9999]
            for i in range(1,25):
                dummyepisode = copy.deepcopy(self.data['raw_'][0])
                randommultiplier = np.random.random(
                                    len(dummyepisode['trace']))
                dummyepisode['trace'] = dummyepisode['trace']*randommultiplier
                dummyepisode.nthEpisode = i
                self.data['raw_'].append(dummyepisode)
            self.uptdate_list()
            self.update_plots()
        elif axotest:
            if VERBOSE:
                print('Test mode with axograph data')
            self.data = backend.Recording(filename = 'data/170404 015.axgd',
                                        filetype = 'axo')
            self.uptdate_list()
            # self.update_plot()
        elif mattest:
            if VERBOSE:
                print('Test mode with matlab data.')
            self.data = backend.Recording(
                                filename = 'data/171025 025 Copy Export.mat',
                                filetype = 'mat')
            self.uptdate_list()
            self.draw_all()

    def create_widgets(self):
        """
        Create the contents of the main window.
        """
        self.commandbar = Commandframe(self)
        self.histogramFrame = HistogramFrame(self)
        self.plots = Plotframe(self)
        self.manipulations = Manipulations(self)
        self.episodeList = EpisodeList(self)
        self.listSelection = ListSelection(self)

    def configure_grid(self):
        """
        Geometry management of the elements in the main window.

        The values in col/rowconfig refer to the position of the elements
        WITHIN the widgets
        """

        ##### Place the main window in the root window
        self.grid(row=0, column=0, sticky=tk.N+tk.S+tk.E+tk.W)
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        ##### First row 
        self.commandbar.grid(row=0, column=0, columnspan=3, padx=5, pady=5,
                             sticky=tk.N+tk.W)

        self.listSelection.grid(row=0, column=3, rowspan=2, padx=5, pady=5,
                                sticky=tk.N)

        ##### Second row
        self.plots.grid(row=1, column=0, rowspan=3, columnspan=3, padx=5,
                        pady=5, sticky=tk.W)
        self.plots.grid_rowconfigure(0, weight=1)
        self.plots.grid_columnconfigure(0, weight=1)

        self.histogramFrame.grid(row=1, column=4, rowspan=3, columnspan=3,
                                 sticky=tk.E)
        self.histogramFrame.grid_rowconfigure(0, weight=1)
        self.histogramFrame.grid_columnconfigure(0, weight=1)

        ##### Third row
        self.episodeList.grid(row=2, column=3, rowspan=2)
        for i in range(2):
            self.episodeList.grid_columnconfigure(i, weight=1)
            self.episodeList.grid_rowconfigure(i, weight=1)
        ##### Fourth row

        ##### Fifth row
        self.manipulations.grid(row=4, column=0, columnspan=3, padx=5, pady=5,
                                sticky=tk.S+tk.W)

    def plot_episode(self):
        """
        Plot the current episode
        """
        if self.data:
            if VERBOSE: print('Calling `plot`, `self.data` is `True`')
            self.plots.plot()
        else:
            if VERBOSE: print('Cannot plot, `self.data` is `False`')
            pass

    def draw_histogram(self):
        """
        draw a histogram of the current episode
        """
        if self.data:
            if VERBOSE: print('Calling histogram, `self.data` is `True`.')
            self.histogramFrame.draw_histogram()
        else:
            if VERBOSE: print('Cannot draw histogram, `self.data` is `False`')
            pass

    def update_plots(self,*args,**kwargs):
        """
        update the plot and histogram of the current episode
        """
        if VERBOSE: print("updating plots")
        self.plot_episode()
        self.draw_histogram()

    def uptdate_list(self):
        if VERBOSE: print('calling `uptdate_list`')
        self.uptdate_episodelist()
        self.uptdate_listmenu()
        ### for now `update_list` will update both the list and the dropdown
        ### menu, in case they need to be uncoupled use the two functions below

    def uptdate_episodelist(self):
        if VERBOSE: print('calling `uptdate_episodelist`')
        self.episodeList.create_list()

    def uptdate_listmenu(self):
        if VERBOSE: print('calling `uptdate_listmenu`')
        self.episodeList.create_dropdownmenu()

    def quit(self):
        if VERBOSE: print('exiting ASCAM')
        self.master.destroy()
        self.master.quit()

class Commandframe(ttk.Frame):
    """
    This frame will contain all the command buttons such as loading
    data and plotting
    """
    ##### Creating the tk.Toplevel pop ups could be done with lambda functions
    def __init__(self, parent):
        ttk.Frame.__init__(self, parent)
        self.parent = parent
        self.create_widgets()

    def create_widgets(self):
        self.loadbutton = ttk.Button(self, text="Load file",
                                     command=self.load_dialog)
        self.loadbutton.grid(column=0,row=0,sticky=tk.N+tk.E)

        self.plotbutton = ttk.Button(self, text="Plot",
                                     command=self.parent.update_plots)
        self.plotbutton.grid(column=1,row=0,sticky=tk.N)

        self.histbutton = ttk.Button(self, text="Histogram",
                                     command=self.parent.draw_histogram)
        self.histbutton.grid(column=2,row=0,sticky=tk.N)

    def load_dialog(self):
        Loadframe(self.parent)

    def histogram_config(self):
        HistogramConfiguration(self.parent)

class HistogramConfiguration(tk.Toplevel):
    """
    A pop up dialog in which the setting of the histogram can be configured
    """
    def __init__(self, parent):
        ttk.Frame.__init__(self, parent)
        self.parent = parent
        self.create_widgets()

    def create_widgets(self):
        

class HistogramFrame(ttk.Frame):
    """
    Frame for the histograms.
    """
    def __init__(self, parent):
        ttk.Frame.__init__(self, parent)
        self.parent = parent
        self.fig = plt.figure(1)
        canvasHist = FigureCanvasTkAgg(self.fig, self)
        canvasHist.show()
        canvasHist.get_tk_widget().grid(row=0,column=0)
        self.canvas = canvasHist

    def draw_histogram(self, active = True, deviation = .05, n_bins = 100,
                       density = False, **kwargs):
        """
        draw a histogram of the current episode and a transparent all point hist
        in the background
        by default this uses the piezo voltage to determine which time points are
        included in the histogram
        Parameters:
            active [boolean] - If true return time points at which piezo 
                               voltage is within `deviation` percent of the 
                               maximum piezo voltage.
            deviation [float] - Deviation, as a percentage, from the maximum
                                piezo voltage or threshold below which voltage
                                should be.
            n_bins [int] - number of bins to be used in the histogram
            density [boolean] - if true the histogram is scaled to sum to one
        """
        if VERBOSE: print("`draw_histogram`")
        if self.parent.data.filename:
            ### get data
            series = self.parent.data[self.parent.datakey.get()]
            time = series[0]['time']

            ### get current episode values and put them in a list
            ### because the histogram function expects a list
            single_piezo = [series[self.parent.Nepisode]['piezo']]
            single_trace = [series[self.parent.Nepisode]['trace']]
            ### get the bins and their values or the current episode
            hist_single = plotting.histogram(time, single_piezo, single_trace, 
                                             active, deviation, n_bins,
                                             density, **kwargs)
            (heights_single,bins_single, 
             center_single, width_single) = hist_single


            ### get a list of all the currents and all the traces
            all_piezo = [episode['piezo'] for episode in series ]
            all_traces = [episode['trace'] for episode in series ]
            ### get the bins and their values for all episodes
            hist_all = plotting.histogram(time, all_piezo, all_traces, active, 
                                          deviation, n_bins, density, 
                                          **kwargs)
            heights_all, bins_all, center_all, width_all = hist_all


            ### create the plot object so we can delete it later
            plot = self.fig.add_subplot(111)
            ### draw bar graphs of the histogram values
            plot.bar(center_all, heights_all, width = width_all, alpha=.2, 
                     color='b')
            plot.bar(center_single, heights_single, width = width_single, 
                     alpha=1)

            ### draw the histogram and clear the plot object to avoid
            ### cluttering memory
            self.canvas.draw()
            plot.clear()

class Plotframe(ttk.Frame):
    def __init__(self, parent):
        ttk.Frame.__init__(self, parent)
        self.parent = parent
        self.fig = plt.figure(2, figsize=(10,5))
        canvasPlot = FigureCanvasTkAgg(self.fig, self)
        canvasPlot.show()
        canvasPlot.get_tk_widget().grid(row=0,column=0)
        self.canvas = canvasPlot
        # self.toolbar = NavigationToolbar2TkAgg(self.canvas, self)
        # self.toolbar.update()
        # self.canvas._tkcanvas.pack()

    def plot(self):
        if self.parent.data.filename:
            if VERBOSE:
                print('`data` exists, plotting...')
                print('datakey = '+self.parent.datakey.get())
                print('Nepisode = '+str(self.parent.Nepisode))
            episode = self.parent.data[
                            self.parent.datakey.get()][self.parent.Nepisode]
            x = episode['time']
            ys = [episode['trace']]
            unitCurrent = 'pA'
            unitTime = 'ms'
            ylabels = ["Current ["+unitCurrent+"]"]
            if episode['piezo'] is not None:
                if VERBOSE: print('`piezo` found')
                unitPiezoVoltage = 'V'
                ys.append(episode['piezo'])
                ylabels.append("Piezo ["+unitPiezoVoltage+']')
            if episode['commandVoltage'] is not None:
                if VERBOSE: print('`commandVoltage` found')
                ys.append(episode['commandVoltage'])
                unitCommandVoltage = 'V'
                ylabels.append("Command ["+unitCommandVoltage+']')
        else:
            if VERBOSE: print("no data found, plotting dummy")
            x = [0,1]
            ys = [[0,0],[0,0],[0,0]]
            ylabels = ['','','']

        self.subplots = []
        for i, (y, ylabel) in enumerate(zip(ys, ylabels)):
            if VERBOSE: 
                print("calling matplotlib")
                print('plotting '+ylabel)
            self.subplots.append(self.fig.add_subplot(len(ys),1,i+1))
            plt.plot(x,y)
            plt.ylabel(ylabel)
            if "Command" in ylabel:
                plt.margins(y=1)

        self.canvas.draw()
        for subplot in self.subplots:
            subplot.clear()

class Manipulations(ttk.Frame):
    """docstring for Manipulations"""
    def __init__(self, parent):
        ttk.Frame.__init__(self, parent)
        self.parent = parent
        self.cutoffFrequency = tk.StringVar()
        self.cutoffFrequency.set(1000)
        self.piezoSelection = tk.IntVar()
        self.piezoSelection.set(1)
        self.intervalSelection = tk.IntVar()
        self.intervalSelection.set(0)
        self.create_widgets()

    def create_widgets(self):
        self.filterallbutton = ttk.Button(self, text="Filter all",
                                     command=self.filter_series)
        self.filterallbutton.grid(column=1,row=0,sticky=())

        # self.filterbutton = ttk.Button(self, text="Filter",
        #                                           command=self.apply_filter)
        # self.filterbutton.grid(column=0,row=0,sticky=())

        self.cutoffentry = ttk.Entry(self, width=7, textvariable=(
                                                        self.cutoffFrequency))
        self.cutoffentry.grid(column=1,row=1)
        ttk.Label(self, text="Filter Frequency (Hz):").grid(column=0, row=1,
                                                            sticky=(tk.W))

        self.baselineButton = ttk.Button(self,text='baseline',
                                        command=self.baseline_correct_frame)
        self.baselineButton.grid(row = 0, column=2,columnspan=2)

        self.piezoCheckbutton = ttk.Checkbutton(self, text='Use Piezo', 
                                               variable = self.piezoSelection)
        self.piezoCheckbutton.grid(row=1, column=2, sticky=tk.W+tk.N)

        self.intervalCheckbutton = ttk.Checkbutton(self, text='Use Intervals', 
                                    variable = self.intervalSelection)
        self.intervalCheckbutton.grid(row=1, column=3, sticky=tk.E+tk.N)

    def filter_series(self):
        if VERBOSE: print('going to filter all episodes')
        #convert textvar to float
        cutoffFrequency = float(self.cutoffFrequency.get())
        if self.parent.data.call_operation('FILTER_',cutoffFrequency):
            if VERBOSE: print('called operation succesfully')
            self.parent.datakey.set(self.parent.data.currentDatakey)
            if VERBOSE: print('updating list and plots')
            self.parent.uptdate_list()
            self.parent.update_plots()
        ## here we should also have that if the operation has been performed
        ## the selection switches to that operation

    def baseline_correct_frame(self):
        if VERBOSE: 
            print('Opening the baseline corrention frame.')
            print('piezoSelection is ',self.piezoSelection)
        subframe = BaselineFrame(self)

class BaselineFrame(tk.Toplevel):
    """
    Temporary frame in which to chose how and based on what points
    the baseline correction should be performed.
    """
    def __init__(self, parent):
        tk.Toplevel.__init__(self, parent)
        self.parent = parent
        self.title("Baseline correction.")

        self.baselineMethod = tk.StringVar()
        self.baselineMethod.set('poly')
        self.baselineDegree = tk.StringVar()
        self.baselineDegree.set(1)

        if self.parent.piezoSelection:
            self.percentDeviation = tk.StringVar()
            self.percentDeviation.set(.05)
            self.create_piezo_widgets()
        else:
            self.create_interval_widgets()
        self.create_widgets()


    def create_widgets(self):
        """
        Creates all widgets that apply to both modes.
        """
        ttk.Label(self,text='method').grid(column=0,row=1)
        ttk.Entry(self,width=7,textvariable=self.baselineMethod).grid(
                                                            column=2,row = 1)

        ttk.Label(self,text='degree').grid(column=0,row=1)
        ttk.Entry(self,width=8,textvariable=self.baselineDegree)
        pass

    def create_piezo_widgets(self):
        """
        Create widgets for the piezo selection of time points.
        """
        ttk.Label(self, text='% deviation:').grid(column=0, row=0,
                                           sticky = (tk.N, tk.W))
        ttk.Entry(self,width=7,textvariable=self.percentDeviation)
        pass

    def create_interval_widgets(self):
        """
        Create widgets for specifying intervals to the select the time points.
        """
        pass

        # # first row - filename and button for choosing file
        # ttk.Label(self, text='File:').grid(column=1, row=1,
        #                                    sticky = (tk.N, tk.W))

        # filenamelabel = ttk.Label(self,
        #                           textvariable=self.parent.filename)
        # filenamelabel.grid(column=2, row=1, sticky=tk.N)

        # self.loadbutton = ttk.Button(self, text='Select file',
        #                              command=self.get_file)
        # self.loadbutton.grid(column = 3, row = 1, sticky=(tk.N, tk.E))

        # #second row - show filepath
        # ttk.Label(self, text='Path:').grid(column=1, row=2,
        #                                    sticky = tk.W)
        # ttk.Label(self, textvariable=self.parent.path).grid(column=2,
        #           row=2)

        # #third row - show filetype
        # ttk.Label(self, text='Filetype:').grid(column=1, row=3,
        #                                        sticky = tk.W)
        # ttk.Label(self, textvariable=self.parent.filetypefull).grid(
        #                         column=2, row=3, sticky=(tk.W, tk.E))
    # def apply_correction(self):
    #     if VERBOSE: print('applying baseline correction')
    #     baselineDegree = int(self.baselineDegree.get())
    #     self.parent.data.call_operation('BC_',)

class ListSelection(ttk.Frame):
    def __init__(self, parent):
        ttk.Frame.__init__(self, parent)
        self.parent = parent
        self.buttons = dict()
        ## the `buttons` dict holds ordered pairs of the button objects and
        ## the variables they refer to, `dict['name']=(button,var)`
        
        self.create_button()
        self.create_checkbox('All')

        self.colors = ['red', 'green', 'yellow']
        self.colorind = 0
        ## until color selection is added we use these three colors to color
        ## the episodes

    def create_checkbox(self, name, key=False): 
        """
        Create another checkbutton for a new selection of episodes and add 
        them to the buttons dict.

        The function destroys the "add" button before it creates the 
        checkbutton and then create a new button. Both objects are added using
        the `pack` which should ensure that they are places underneath one
        another.
        """
        if VERBOSE: print('Creating checkbox with name '+name)

        ### remove old 'add' button
        self.createBoxButton.destroy()

        ### create a checkbox and a variable for it
        variable = tk.IntVar()
        if not key: variable.set(1) ### start with 'all' selected
        button = ttk.Checkbutton(self, text=name, variable=variable)
        button.pack()

        ### store button and variable in dict
        self.buttons[name] = (button, variable)

        ### create new 'add' button underneath the checkbox
        self.create_button()

        if not name in self.parent.data.lists.keys():
            self.parent.data.lists[name] = []

        ### create function to color episode on keypress and add to list
        if key:
            ### convert key to lower case and take only the first letter if
            ### multiple were entered
            key=key.lower()
            key=key[0]
            def color_episode(*args,**kwargs):
                if not (self.parent.Nepisode in self.parent.data.lists[name]):
                    self.parent.episodeList.episodelist.itemconfig(
                                            self.parent.Nepisode,
                                            {'bg':self.colors[self.colorind]})
                    self.parent.data.lists[name].append(self.parent.Nepisode)
                else:
                    self.parent.episodeList.episodelist.itemconfig(
                                                        self.parent.Nepisode,
                                                        bg='white')
                    self.parent.data.lists[name].remove(self.parent.Nepisode)

            self.colorind+=1
            self.parent.listAssignFunctions.append(color_episode)
            self.parent.bind_all(key,self.parent.listAssignFunctions[-1])

    def create_button(self):
        """
        Create the button that will open the dialog for adding new lists.
        This functions uses `pack` geometry because the button will be created
        and destroyed several times at different locations in the grid.
        """
        if VERBOSE: print("Creating new checkbox maker button")

        self.createBoxButton = ttk.Button(self,text='Add',
                                          command=lambda: AddListDialog(self))
        self.createBoxButton.pack()

class AddListDialog(tk.Toplevel):
    """
    The dialog that will pop up if a new list is created, it asks for the name
    of the list.
    """
    def __init__(self, parent):
        tk.Toplevel.__init__(self, parent)
        self.parent = parent
        self.title("Add list")
        self.name = tk.StringVar()
        self.key = tk.StringVar()
        self.create_widgets()
        if VERBOSE: print("Opened new AddListDialog")

    def create_widgets(self):
        if VERBOSE: print('populating dialog')
        ttk.Label(self, text='Name:').grid(row=0,column=0)
        ttk.Entry(self, width=7, textvariable=self.name).grid(row=0,column=1)

        ttk.Label(self, text='key:').grid(row=1,column=0)
        ttk.Entry(self, width=7, textvariable=self.key).grid(row=1,column=1)

        ttk.Button(self,text="OK",command=self.ok_button).grid(row=2,column=0)
        ttk.Button(self,text="Cancel",command=self.destroy).grid(row=2,
                                                                 column=1)

    def ok_button(self):
        if VERBOSE: print("Confirmed checkbox creation through dialog")
        if self.name.get() and self.key.get():
            self.parent.create_checkbox(self.name.get(),self.key.get())
        else: print("failed to enter name and/or key")
        self.destroy()

class EpisodeList(ttk.Frame):
    """
    Frame that holds a scrollable list of all the episodes in the currently 
    selected series.
    """
    def __init__(self, parent):
        ttk.Frame.__init__(self, parent)
        self.parent = parent

        ### create the variable tracking the current selection, `currentSeries`
        ### and assign it to call the function `selection_change` when it is
        ### changed
        self.parent.datakey.trace("w", self.selection_change)
        self.create_list()
        self.create_dropdownmenu()

    def onselect_plot(self, event):
        """
        When a new episode is selected by clicking or with arrow keys get the
        change the number of the current episode and update the plots
        """
        if VERBOSE: print("selected new episode in list")
        self.parent.Nepisode = int(event.widget.curselection()[0])
        self.parent.update_plots()

    def create_list(self):
        """
        create the list of episodes and a scroll bar
        scroll bar is created first because episodelist references it
        the last line of scrollbar references episodelist so it has to come
        after the creating of episodelist
        """
        if VERBOSE: print("creating scrollbar")
        self.Scrollbar = tk.Scrollbar(self, orient=tk.VERTICAL)
        self.Scrollbar.grid(column=1, row=1, rowspan=3, sticky=tk.N+tk.S+tk.E)
        
        if VERBOSE: print("creating episodelist")
        self.episodelist = tk.Listbox(self, bd=2,
                                      yscrollcommand=self.Scrollbar.set)
        self.episodelist.grid(row=1, rowspan=3, sticky=tk.S+tk.W+tk.N)
        ### set what should happen when an episode is selected
        self.episodelist.bind('<<ListboxSelect>>', self.onselect_plot)

        self.episodelist.config(height=30)
        ### only create the list if there is data to fill it with
        if self.parent.data:
            if VERBOSE: print("found data to fill list with")
            for episode in self.parent.data[self.parent.datakey.get()]:
                self.episodelist.insert(tk.END, "episode #"
                                                +str(episode.nthEpisode))
        ### assign the scrollbar its function
        self.Scrollbar['command'] = self.episodelist.yview
        self.episodelist.selection_set(self.parent.Nepisode)

    def create_dropdownmenu(self):
        """
        create the dropdown menu that is a list of the available series
        """
        if  VERBOSE: print("creating dropdown menu")
        if self.parent.data:
            if VERBOSE: print("found data")
            ### the options in the list are all the datakeys
            listOptions = self.parent.data.keys()
        else:
            listOptions = ['']
        self.menu = tk.OptionMenu(self, self.parent.datakey, *listOptions)
        self.menu.grid(row=0,column=0,columnspan=2,sticky=tk.N)

    def selection_change(self, *args):
        """
        when the `currentSeries` variable changes this function will be called
        it needs the `*args` arguments because tkinter passes some arguments
        to it (we currently dont need those)
        """
        if VERBOSE: print(self.parent.datakey.get()+' selected')
        self.parent.uptdate_episodelist()
        self.parent.update_plots()

class Loadframe(tk.Toplevel):
    """
    Temporary frame that gets the file and information about it.
    Select file and load it by clicking 'ok' button, in case of binary
    file another window pops up to ask for additional parameters.
    """
    def __init__(self, parent):
        tk.Toplevel.__init__(self,parent)
        self.parent = parent
        self.title("Select file")
        self.reset_entryFields()
        self.create_widgets()
        self.loadbutton.focus()

    def reset_entryFields(self):
        """
        Set all the string variables to empty string so if data is loaded two 
        times the old values are not shown in the new window.
        """
        self.parent.filetype.set('')
        self.parent.filename.set('')
        self.parent.samplingrate.set('')
        self.parent.path.set('')

    def create_widgets(self):
        # first row - filename and button for choosing file
        ttk.Label(self, text='File:').grid(column=1,row=1,sticky=(tk.N, tk.W))

        filenamelabel = ttk.Label(self, textvariable=self.parent.filename)
        filenamelabel.grid(column=2, row=1, sticky=tk.N)

        self.loadbutton = ttk.Button(self, text='Select file', 
                                     command=self.get_file)
        self.loadbutton.grid(column = 3, row = 1, sticky=(tk.N, tk.E))

        #second row - show filepath
        ttk.Label(self, text='Path:').grid(column=1, row=2, sticky = tk.W)
        ttk.Label(self, textvariable=self.parent.path).grid(column=2, row=2)

        #third row - show filetype
        ttk.Label(self, text='Filetype:').grid(column=1, row=3, sticky = tk.W)
        ttk.Label(self, textvariable=self.parent.filetypefull).grid(column=2, 
                                                   row=3, sticky=(tk.W, tk.E))
        ###### lets see if this way of line splitting works

        #fourth row - enter sampling rate
        self.samplingentry = ttk.Entry(self, width=7,
                                       textvariable=self.parent.samplingrate)
        self.samplingentry.grid(column=2,row=4)
        ttk.Label(self, text="Samplingrate (Hz):").grid(column=1,
                                                        row=4, sticky=(tk.W))

        #fifth row - Load button to close and go to next window and close button
        self.loadbutton = ttk.Button(self, text="Load",
                                   command=self.load_button)
        self.loadbutton.grid(column=1, row=5, sticky=(tk.S, tk.W))

        self.closebutton = ttk.Button(self, text="Close",
                                      command=self.destroy)
        self.closebutton.grid(column=3, row=5, sticky=(tk.S, tk.E))

    def load_button(self):
        if self.parent.filetype.get() == 'bin':
            binframe = Binaryquery(self)

        elif (self.parent.filetype.get() == 'axo'
              or self.parent.filetype.get() == 'mat'):
            self.parent.data = backend.Recording(
                                    self.parent.filenamefull.get(),
                                    self.parent.samplingrate.get(),
                                    self.parent.filetype.get())
            self.parent.datakey.set(self.parent.data.currentDatakey)
            self.parent.uptdate_list()
            self.parent.update_plots()
            self.destroy()

    def get_file(self):
        """
        Get data by clicking.
        Relies on tkinter and gets name and type of the file
        """
        filename = askopenfilename()
        self.parent.filenamefull.set(filename)
        extension = ''

        N = len(filename)
        for i, char in enumerate(filename[::-1]):
            # loop over the full filename (which includes directory) backwards
            # to extract the extension and name of the file
            if char=='.':
                period = N-i
            if char=='/':
                slash = N-i
                break

        self.parent.filename.set(filename[slash:])
        self.parent.path.set(filename[:slash])
        extension=filename[period:]

        if extension == 'bin':
            self.parent.filetype.set('bin')
            self.parent.filetypefull.set('binary')

        elif extension == 'axgd':
            self.parent.filetype.set('axo')
            self.parent.filetypefull.set('axograph')

        elif extension == 'mat':
            self.parent.filetype.set('mat')
            self.parent.filetypefull.set('matlab')

        self.samplingentry.focus()

class Binaryquery(tk.Toplevel):
    """
    If the filetype is '.bin' this asks for the additional parameters
    such as the length of the header (can be zero) and the datatype
    (should be given as numpy type, such as "np.int16")
    """
    def __init__(self, parent):
        #frame configuration
        tk.Toplevel.__init__(self, parent)
        self.parent = parent.parent
        self.loadframe = parent
        self.title("Additional parameters for binary file")

        #initialize content
        self.create_widgets()
        self.headerentry.focus()

    def create_widgets(self):
        # #entry field for headerlength
        self.headerentry = ttk.Entry(self, width=7,
                                textvariable=self.parent.headerlength)
        self.headerentry.grid(column=3,row=1,sticky=(tk.W,tk.N))

        ttk.Label(self, text="Headerlength:").grid(column=2,row=1,
                                                   sticky=(tk.N))

        #entry field for filetype
        self.typeentry = ttk.Entry(self, width=7,
                                   textvariable=self.parent.datatype)
        self.typeentry.grid(column=3,row=2,sticky=(tk.W,tk.S))

        ttk.Label(self, text="Datatype:").grid(column=2,row=2,
                                               sticky=tk.S)

        #'ok' and 'cancel button
        self.okbutton = ttk.Button(self, text="Load",
                                   command=self.ok_button)
        self.okbutton.grid(columnspan=2, row=3, sticky=(tk.S, tk.W))

    def ok_button(self):
        # if self.parent.datatype.get()=='np.int16':
        datatype = np.int16 #this is here because stringvar.get
                            #returns a string which numpy doesnt
                            #understand
        self.parent.data = backend.Recording(self.parent.filenamefull.get(),
                                         self.parent.samplingrate.get(),
                                         self.parent.filetype.get(),
                                         self.parent.headerlength.get(),
                                         datatype)
        self.parent.uptdate_list()
        self.parent.update_plots()
        self.loadframe.destroy()
        self.destroy()

if __name__ == '__main__':
    import sys, os, copy
    cwd = os.getcwd()
    try:
        if 'axo' in sys.argv:
            axotest = True
        elif 'bin' in sys.argv:
            bintest = True
        elif 'mat' in sys.argv:
            mattest = True
        if 'v' in sys.argv:
            VERBOSE = True
    except IndexError:
        pass

    GUI.run()