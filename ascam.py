#!/usr/bin/env python
"""
ASCAM for processing and analysis of data from single ion channels.
"""
import os
import sys
import logging

import getopt

from PySide2.QtWidgets import QApplication
from ascam.gui.mainwindow import MainWindow
from ascam.utils import initialize_logger


debug_logger = logging.getLogger("ascam.debug")


def parse_options():
    """
    Parse the command line options when launching ASCAM.

    Returns:
        debug (bool) - if true print contents of debug log to console
        verbose (bool) - if true print contents of analysis log to console
        logdir (string) - the directory in which the log should be saved
        test (bool) - if true load example data
    """
    debug = False
    verbose = False
    logdir = "./logfiles"
    test = False
    try:
        options, args = getopt.getopt(
            sys.argv[1:], "dvl:th", ["loglevel=", "logdir=", "help", "test"]
        )
    except getopt.GetoptError as err:
        # print help information and exit:
        print(err)  # will print something like "option -a not recognized"
        display_help()
        sys.exit(2)

    for opt, arg in options:
        if opt in ("-d", "--debug"):
            debug = True
        elif opt in ("-v", "--verbose"):
            verbose = True
        elif opt in ("-l", "--logdir"):
            logdir = arg
        elif opt in ("-t", "test"):
            test = True
        elif opt in ("-h", "--help"):
            display_help()
            sys.exit(2)
        else:
            assert False, "unhandled option"

    return verbose, logdir, test, debug


def display_help():
    """
    Print a manual for calling ASCAM to the commandline.
    """
    print(
        """Usage: ./run --debug --verbose --test --logdir=./logfiles

            -d --debug : print debug messages to console
            -v --verbose : print content of analysis log to console
            -l --logdir : directory in which the log file should be saved
            -t --test : load example data
            -h --help : display this message"""
    )


def get_version():
    here = os.path.abspath(os.path.dirname(__file__))
    stream = os.popen(f"pip freeze")
    pip_freeze = stream.read()

    stream = os.popen(f"cd {here}; git show")
    git_info = stream.read()
    git_info = "\n".join(git_info.split("\n")[:3])

    return pip_freeze, git_info


def main():
    verbose, logdir, test, debug = parse_options()

    initialize_logger(logdir, verbose, debug)
    logging.info("-" * 20 + "Start of new ASCAM session" + "-" * 20)

    pip_freeze, git_info = get_version()

    logging.info(git_info)
    logging.info(pip_freeze)

    app = QApplication([])
    main_window = MainWindow()
    main_window.show()
    if test:
        main_window.test_mode()
    sys.exit(app.exec_())


# if __name__ == "__main__":
#     main()