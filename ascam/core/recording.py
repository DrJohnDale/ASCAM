import logging
import pickle

import numpy as np

from ascam.core.readdata import load_matlab, load_axo
from ascam.utils.tools import parse_filename, piezo_selection, interval_selection
from ascam.core.episode import Episode
from ascam.core.series import Series
from ascam.constants import ANALYSIS_LEVELV_NUM


class Recording(dict):
    @classmethod
    def from_file(
        cls,
        filename="data/180426 000 Copy Export.mat",
        sampling_rate=4e4,
        time_input_unit="s",
        trace_input_unit="A",
        piezo_input_unit="V",
        command_input_unit="V",
    ):
        """Load data from a file.

        This method creates a recording objects or reconstructs one from the
        data in the file.
        Args:
            filename - name of the file
            sampling_rate - the frequency at which the recording was sampled
            time_unit - the unit of time in the input
            trace_unit - the unit of electric current in the input
            piezo_unit - the unit of voltage in the piezo data in the input
            command_unit - the units in which the command voltage is given
        Returns:
            recording - instance of the Recording class containing the data"""
        logging.debug(f"Recording.from_file")
        logging.log(
            ANALYSIS_LEVELV_NUM,
            f"Loading data from file {filename}\n"
            f"sampling_rate = {sampling_rate}\n"
            f"time_input_unit = {time_input_unit}\n"
            f"trace_input_unit = {trace_input_unit}\n"
            f"piezo_input_unit = {piezo_input_unit}\n"
            f"command_input_unit = {command_input_unit}",
        )

        recording = cls(filename, sampling_rate)

        filetype, _, _, _ = parse_filename(filename)
        if filetype == "pkl":
            recording = cls._load_from_pickle(recording)
        elif filetype == "mat":
            recording = cls._load_from_matlab(
                recording,
                trace_input_unit=trace_input_unit,
                piezo_input_unit=piezo_input_unit,
                command_input_unit=command_input_unit,
                time_input_unit=time_input_unit,
            )
        elif "axg" in filetype:
            recording = cls._load_from_axo(
                recording,
                trace_input_unit=trace_input_unit,
                piezo_input_unit=piezo_input_unit,
                command_input_unit=command_input_unit,
                time_input_unit=time_input_unit,
            )
        else:
            raise ValueError(f"Cannot load from filetype {filetype}.")

        recording.lists = {"all": (list(range(len(recording["raw_"]))), "white", None)}

        return recording

    def __init__(self, filename="", sampling_rate=4e4):
        logging.info("""intializing Recording""")

        # parameters for loading the data
        self.filename = filename

        # attributes of the data
        self.sampling_rate = int(float(sampling_rate))

        # attributes for storing and managing the data
        self["raw_"] = Series()
        self.current_datakey = "raw_"
        self.n_episode = 0

        self.hist_times = 0
        # parameters for analysis
        # idealization
        self.tc_unit = "pA"
        self.tc_unit_factors = {
            "fA": 1e15,
            "pA": 1e12,
            "nA": 1e9,
            "µA": 1e6,
            "mA": 1e3,
            "A": 1,
        }
        self._tc_resolution = None
        # first activation
        self._fa_threshold = 0.0
        # variables for user created lists of episodes
        # `lists` stores the indices of the episodes in the list in the first
        # element, their color in the GUI in the second and the associated key
        # (i.e. for adding selected episodes to the list in the third element
        # of a tuple that is the value under the list's name (as dict key)
        self.lists = dict()
        self.current_lists = ["all"]

    @property
    def fa_threshold(self):
        return self.series._fa_threshold * self.tc_unit_factors[self.tc_unit]

    @fa_threshold.setter
    def fa_threshold(self, theta):
        if theta is not None:
            self.series._fa_threshold = theta / self.tc_unit_factors[self.tc_unit]
        else:
            self.series._fa_threshold = None

    @property
    def tc_amplitudes(self):
        return self.series._tc_amplitudes * self.tc_unit_factors[self.tc_unit]

    @tc_amplitudes.setter
    def tc_amplitudes(self, amps):
        if amps is not None:
            self.series._tc_amplitudes = amps / self.tc_unit_factors[self.tc_unit]
        else:
            self.series._tc_amplitudes = np.array([])

    @property
    def tc_thresholds(self):
        return self.series._tc_thresholds * self.tc_unit_factors[self.tc_unit]

    @tc_thresholds.setter
    def tc_thresholds(self, thetas):
        if thetas is not None:
            self.series._tc_thresholds = thetas / self.tc_unit_factors[self.tc_unit]
        else:
            self.series._tc_thresholds = np.array([])

    @property
    def tc_resolution(self):
        if self.series._tc_resolution:
            return self.series._tc_resolution * self.episode.time_unit_factor
        else:
            return None

    @tc_resolution.setter
    def tc_resolution(self, resolution):
        if resolution is not None:
            self.series._tc_resolution = resolution / self.episode.time_unit_factor
        else:
            self.series.tc_resolution = None

    @property
    def interpolation_factor(self):
        return self.series.interpolation_factor

    @interpolation_factor.setter
    def interpolation_factor(self, factor):
        if factor is not None:
            self.series.interpolation_factor = factor
        else:
            self.series.interpolation_factor = 1

    @property
    def selected_episodes(self):
        indices = list()
        for listname in self.current_lists:
            indices.extend(self.lists[listname][0])
        # remove duplicate indices
        indices = np.array(list(set(indices)))
        logging.debug(f"Selected episodes: {indices}")
        return np.array(self.series)[indices]

    @property
    def series(self):
        # logging.debug(f"Returning series {self.current_datakey}")
        return self[self.current_datakey]

    @property
    def episode(self):
        return self.series[self.n_episode]

    @property
    def has_piezo(self):
        return self.series.has_piezo

    @property
    def has_command(self):
        return self.series.has_command

    @property
    def time_unit(self):
        return self.episode.time_unit

    @property
    def trace_unit(self):
        return self.episode.trace_unit

    @property
    def piezo_unit(self):
        return self.episode.piezo_unit

    @property
    def command_unit(self):
        return self.episode.command_unit

    def baseline_correction(
        self,
        method="poly",
        poly_degree=1,
        intval=[],
        select_intvl=False,
        piezo_diff=0.05,
        select_piezo=True,
        active_piezo=False,
    ):
        """Apply a baseline correction to the current series."""
        logging.debug(f"baseline_correction")

        logging.log(
            ANALYSIS_LEVELV_NUM,
            f"baseline_correction on series '{self.current_datakey}',"
            f"using method '{method}' with degree {poly_degree}\n"
            f"select_intvl is {select_intvl}; select_piezo is "
            f"{select_piezo}\n"
            f"the selected intervals are {intval}\n"
            f"select where piezo is active is {active_piezo}; the "
            f"difference to piezo baseline is {piezo_diff}",
        )
        if self.current_datakey == "raw_":
            # if its the first operation drop the 'raw_'
            new_datakey = "BC_"
        else:
            # if operations have been done before combine the names
            new_datakey = self.current_datakey + "BC_"
        logging.info(f"new datakey is {new_datakey}")
        self[new_datakey] = self[self.current_datakey].baseline_correct_all(
            intervals=intval,
            method=method,
            degree=poly_degree,
            select_intvl=select_intvl,
            select_piezo=select_piezo,
            active=active_piezo,
            deviation=piezo_diff,
        )
        self.current_datakey = new_datakey
        logging.debug("keys of the recording are now {}".format(self.keys()))

    def gauss_filter_series(self, filter_freq):
        """Filter the current series using a gaussian filter"""
        logging.debug(f"gaussian_filter")

        logging.log(
            ANALYSIS_LEVELV_NUM,
            f"gauss filtering series '{self.current_datakey}'\n"
            f"with frequency {filter_freq}",
        )

        fdatakey = f"GFILTER{filter_freq}_"
        if self.current_datakey == "raw_":
            # if its the first operation drop the 'raw-'
            new_key = fdatakey
        else:
            # if operations have been done before combine the names
            new_key = self.current_datakey + fdatakey
        self[new_key] = self.series.gaussian_filter(filter_freq)
        self.current_datakey = new_key

    def CK_filter_series(
        self,
        window_lengths,
        weight_exponent,
        weight_window,
        apriori_f_weights=False,
        apriori_b_weights=False,
    ):
        """Filter the current series using the Chung-Kennedy filter banks"""
        logging.debug(f"CK_filter_series")
        logging.log(
            ANALYSIS_LEVELV_NUM,
            f"Chung-Kennedy filtering on series "
            f"'{self.current_datakey}'\n"
            f"window_lengths: {window_lengths}\n"
            f"weight_exponent: {weight_exponent}\n"
            f"weight_window: {weight_window}\n"
            f"apriori_f_weights: {apriori_f_weights}\n"
            f"apriori_b_weights: {apriori_b_weights}",
        )

        n_filters = len(window_lengths)
        fdatakey = f"CKFILTER_K{n_filters}p{weight_exponent}M{weight_window}_"
        if self.current_datakey == "raw_":
            # if its the first operation drop the 'raw-'
            new_datakey = fdatakey
        else:
            # if operations have been done before combine the names
            new_datakey = self.current_datakey + fdatakey
        self[new_datakey] = self[self.current_datakey].CK_filter(
            window_lengths,
            weight_exponent,
            weight_window,
            apriori_f_weights,
            apriori_b_weights,
        )
        self.current_datakey = new_datakey

    def idealize_series(self):
        """Idealize the current series."""
        logging.debug(f"idealize_series")

        logging.log(
            ANALYSIS_LEVELV_NUM,
            f"idealizing series '{self.current_datakey}'\n"
            f"amplitudes: {self.series._tc_amplitudes}\n"
            f"thresholds: {self.series._tc_thresholds}\n"
            f"resolution: {self.series._tc_resolution}\n"
            f"interpolation_factor: {self.series.interpolation_factor}",
        )

        for episode in self.series:
            episode.idealize_or_interpolate(
                self.series._tc_amplitudes,
                self.series._tc_thresholds,
                self.series._tc_resolution,
                self.series.interpolation_factor,
            )

    def idealize_episode(self):
        """Idealize current episode."""
        logging.debug(f"idealize_episode")

        logging.log(
            ANALYSIS_LEVELV_NUM,
            f"idealizing episode '{self.n_episode}'\n"
            f"amplitudes: {self.series._tc_amplitudes}\n"
            f"thresholds: {self.series._tc_thresholds}\n"
            f"resolution: {self.series._tc_resolution}\n"
            f"interpolation_factor: {self.series.interpolation_factor}",
        )

        self.episode.idealize_or_interpolate(
            self.series._tc_amplitudes,
            self.series._tc_thresholds,
            self.series._tc_resolution,
            self.series.interpolation_factor,
        )

    def detect_fa(self, exclude=[]):
        """Apply first event detection to all episodes in the selected series"""

        logging.debug(f"detect_fa")

        [
            episode.detect_first_activation(self._fa_threshold)
            for episode in self.series
            if episode.n_episode not in exclude
        ]

    def series_hist(
        self,
        active=True,
        select_piezo=True,
        deviation=0.05,
        n_bins=50,
        density=False,
        intervals=False,
    ):
        """Create a histogram of all episodes in the presently selected series
        """
        logging.debug(f"series_hist")
        # put all piezo traces and all current traces in lists
        piezos = [episode.piezo for episode in self.series]
        traces = [episode.trace for episode in self.series]
        trace_list = []
        if not self.has_piezo:
            # this is a failsafe, select_piezo should never be true if has_piezo
            # is false
            if select_piezo:
                logging.debug(
                    (f"Tried piezo selection even " "though there is no piezo data!")
                )
            select_piezo = False
        # select the time points that are used for the histogram
        if select_piezo:
            for piezo, trace in zip(piezos, traces):
                time, trace_points = piezo_selection(
                    self.episode.time, piezo, trace, active, deviation
                )
                trace_list.extend(trace_points)
            self.hist_times = np.array(time)
        elif intervals:
            for trace in traces:
                time, trace_points = interval_selection(
                    self.episode.time, trace, intervals, self.sampling_rate
                )
                trace_list.extend(trace_points)
            self.hist_times = np.array(time)
        else:
            trace_list = traces
            self.hist_times = np.array(self.episode.time)
        # turn the collected traces into a 1D numpy array for the histogram
        # function
        trace_list = np.asarray(trace_list)
        trace_list = trace_list.flatten()
        heights, bins = np.histogram(trace_list, n_bins, density=density)
        # get centers of all the bins
        centers = (bins[:-1] + bins[1:]) / 2
        # get the width of a(ll) bin(s)
        width = bins[1] - bins[0]
        return heights, bins, centers, width

    def episode_hist(
        self,
        active=True,
        select_piezo=True,
        deviation=0.05,
        n_bins=50,
        density=False,
        intervals=False,
    ):
        """Create a histogram of the current in the presently selected episode.
        """
        logging.debug(f"episode_hist")

        # failsafe for piezo selection
        if not self.has_piezo:
            select_piezo = False
        # select time points to include in histogram
        if select_piezo:
            time, trace_points = piezo_selection(
                self.episode.time,
                self.episode.piezo,
                self.episode.trace,
                active,
                deviation,
            )
            self.hist_times = np.array(time)
        elif intervals:
            time, trace_points = interval_selection(
                self.episode.time,
                self.episode.trace,
                intervals,
                self.episode.sampling_rate,
            )
            self.hist_times = np.array(time)
        else:
            trace_points = self.episode.trace
            self.hist_times = np.array(self.episode.time)
        heights, bins = np.histogram(trace_points, n_bins, density=density)
        # get centers of all the bins
        centers = (bins[:-1] + bins[1:]) / 2
        # get the width of a(ll) bin(s)
        width = bins[1] - bins[0]
        # self.histogram = heights, bins, centers, width
        return heights, bins, centers, width

    # exporting and saving methods
    def save_to_pickle(self, filepath):
        """Dump the recording to a pickle."""
        logging.debug(f"save_to_pickle")

        if not filepath.endswith(".pkl"):
            filepath += ".pkl"
        with open(filepath, "wb") as save_file:
            pickle.dump(self, save_file)

    def export_matlab(
        self,
        filepath,
        datakey,
        lists_to_save,
        save_piezo,
        save_command,
        time_unit="s",
        trace_unit="A",
        piezo_unit="V",
        command_unit="V",
    ):
        """Export all the episodes in the givens list(s) from the given series
        (only one) to a matlab file."""
        logging.debug(
            f"export_matlab:\n"
            f"saving the lists: {lists_to_save}\n"
            f"of series {datakey}\n"
            f"save piezo: {save_piezo}; "
            "save command: {save_command}\n"
            f"saving to destination: {filepath}"
        )
        from scipy import io

        # create dict to write matlab file and add the time vector
        export_dict = dict()
        export_dict["time"] = (
            self["raw_"][0].time * Episode.time_unit_factors[time_unit]
        )
        no_episodes = len(self[datakey])
        fill_length = len(str(no_episodes))
        # get the episodes we want to save
        indices = list()
        for listname in lists_to_save:
            indices.extend(self.lists[listname][0])
        indices = np.array(list(set(indices)))
        episodes = np.array(self[datakey])[indices]
        for episode in episodes:
            n = str(episode.n_episode).zfill(fill_length)
            export_dict["trace" + n] = (
                episode._trace * Episode.trace_unit_factors[trace_unit]
            )
            if save_piezo:
                export_dict["piezo" + n] = (
                    episode._piezo * Episode.piezo_unit_factors[piezo_unit]
                )
            if save_command:
                export_dict["command" + n] = (
                    episode._command * Episode.command_unit_factors[command_unit]
                )
        io.savemat(filepath, export_dict)

    def export_axo(self, filepath, datakey, lists_to_save, save_piezo, save_command):
        """Export data to an axograph file.

        Argument:
            filepath - location where the file is to be stored
            datakey - series that should be exported
            lists_to_save - the user-created lists of episodes that should be
                includes
            save_piezo - if true piezo data will be exported
            save_command - if true command voltage data will be exported"""
        logging.debug(
            f"export_axo:\n"
            f"saving the lists: {lists_to_save}\n"
            f"of series {datakey}\n"
            f"save piezo: {save_piezo}; save command: {save_command}\n"
            f"saving to destination: {filepath}"
        )

        import axographio

        column_names = [f"time ({self.time_unit})"]

        # to write to axgd we need a list as the second argument of the 'write'
        # method, this elements in the lists will be the columns in data table
        # the first column in this will be a list of episode numbers
        data_list = [self.episode.time]

        # get the episodes we want to save
        indices = list()
        for listname in lists_to_save:
            indices.extend(self.lists[listname][0])
        indices = np.array(list(set(indices)))
        episodes = np.array(self.series)[indices]

        for episode in episodes:
            data_list.append(np.array(episode._trace))
            column_names.append(f"Ipatch ({self.trace_unit} ep#{episode.n_episode}")
            if save_piezo:
                column_names.append(
                    f"piezo voltage ({self.piezo_unit} ep#{episode.n_episode}"
                )
                data_list.append(np.array(episode._piezo))
            if save_command:
                column_names.append(
                    f"command voltage ({self.command_unit} ep#{episode.n_episode})"
                )
                data_list.append(np.array(episode._command))
        file = axographio.file_contents(column_names, data_list)
        file.write(filepath)

    def export_idealization(self, filepath, time_unit, trace_unit):
        logging.debug(f"export_idealization")

        if not filepath.endswith(".csv"):
            filepath += ".csv"
        export_array = np.zeros(
            shape=(len(self.selected_episodes) + 1, self.episode._idealization.size)
        )
        export_array[0] = self.episode._time * Episode.time_unit_factors[time_unit]
        for k, episode in enumerate(self.selected_episodes):
            export_array[k + 1] = (
                episode._idealization * Episode.trace_unit_factors[trace_unit]
            )
        # note that we transpose the export array to export the matrix
        # as time x episode
        np.savetxt(filepath, export_array.T, delimiter=",")

    def export_events(self, filepath):
        """Export a table of events in the current (idealized) series and
        duration to a csv file."""
        logging.debug(f"export_events")

        import pandas as pd

        if not filepath.endswith(".csv"):
            filepath += ".csv"
        export_array = np.zeros((0, 5)).astype(object)
        header = [
            f"amplitude [{self.trace_unit}]",
            f"duration [{self.time_unit}]",
            f"t_start",
            "t_stop",
            "episode number",
        ]
        for episode in self.series:
            # create a column containing the episode number
            ep_events = episode.get_events()
            episode_number = episode.n_episode * np.ones(len(ep_events[:, 0]))
            # glue that column to the event
            ep_events = np.concatenate(
                (ep_events, episode_number[:, np.newaxis]), axis=1
            )
            export_array = np.concatenate((export_array, ep_events), axis=0)
        export_array = pd.DataFrame(export_array)
        # truncate floats for duration and timestamps to 3 decimals (standard 1 micro s)
        for i in [1, 2, 3]:
            export_array[i] = export_array[i].map(lambda x: f"{x:.3f}")
        export_array.to_csv(filepath)

    def export_first_activation(self, filepath, time_unit):
        """Export csv file of first activation times."""
        logging.debug(f"export_first_activation")

        if not filepath.endswith(".csv"):
            filepath += ".csv"
        export_array = np.array(
            [
                (
                    episode.n_episode,
                    episode._first_activation * Episode.time_unit_factors[time_unit],
                )
                for episode in self.selected_episodes
            ]
        )
        np.savetxt(filepath, export_array, delimiter=",")

    @staticmethod
    def _load_from_axo(
        recording,
        trace_input_unit,
        piezo_input_unit,
        command_input_unit,
        time_input_unit,
    ):
        """Load a recording from an axograph file.

        Recordings edited in ASCAM can be saved as pickles, this method
        reconstructs such saved recordings.
        Args:
            recording - recording object to be filled with data
        Returns:
            recording the instance of the recording that was stored in the
            file."""
        logging.debug(f"from_axo")

        names, time, current, piezo, command = load_axo(recording.filename)
        n_episodes = len(current)
        if not piezo:
            piezo = [None] * n_episodes
        if not command:
            command = [None] * n_episodes
        recording["raw_"] = Series(
            [
                Episode(
                    time,
                    current[i],
                    n_episode=i,
                    piezo=piezo[i],
                    command=command[i],
                    sampling_rate=recording.sampling_rate,
                    input_time_unit=time_input_unit,
                    input_trace_unit=trace_input_unit,
                    input_piezo_unit=piezo_input_unit,
                    input_command_unit=command_input_unit,
                )
                for i in range(n_episodes)
            ]
        )
        return recording

    @staticmethod
    def _load_from_pickle(recording):
        """Load a recording from a '.pkl' file.

        Recordings edited in ASCAM can be saved as pickles, this method
        reconstructs such saved recordings.
        Args:
            recording - recording object to be filled with data
        Returns:
            recording the instance of the recording that was stored in the
            pickle."""
        with open(recording.filename, "rb") as file:
            data = pickle.load(file).__dict__
            recording.__dict__ = data.__dict__
            for key, value in data.items():
                recording[key] = value
        return recording

    @staticmethod
    def _load_from_matlab(
        recording,
        trace_input_unit,
        piezo_input_unit,
        command_input_unit,
        time_input_unit,
    ):
        """Load data from a matlab file.

        This method creates a recording objects from the data in the file.
        Args:
            recording - recording object to be filled with data
        Returns:
            recording - instance of the Recording class containing the data"""
        logging.debug(f"from_matlab")

        names, time, current, piezo, command = load_matlab(recording.filename)
        n_episodes = len(current)
        if not piezo:
            piezo = [None] * n_episodes
        if not command:
            command = [None] * n_episodes
        recording["raw_"] = Series(
            [
                Episode(
                    time,
                    current[i],
                    n_episode=i,
                    piezo=piezo[i],
                    command=command[i],
                    sampling_rate=recording.sampling_rate,
                    input_time_unit=time_input_unit,
                    input_trace_unit=trace_input_unit,
                    input_piezo_unit=piezo_input_unit,
                    input_command_unit=command_input_unit,
                )
                for i in range(n_episodes)
            ]
        )
        return recording