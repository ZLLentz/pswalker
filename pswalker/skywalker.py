# Command and Control Module for Skywalker

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import importlib
import numpy as np

from .monitor import Monitor
from .walker import Walker
from .modelbuild import ModelBuilder
from .utils.exceptions import CNCException

class Skywalker(object):
    """
    Command and control class that interacts with the user and performs the
    alignment.
    """
    
    def __init__(self, **kwargs):
        self.monitor = kwargs.get("monitor", Monitor())
        self.walker = kwargs.get("walker", Walker(self.monitor))
        self.model_builder = kwargs.get("model_builder", None)
        self.model = kwargs.get("model", None)
        self.iter_walker = kwargs.get("iter_walker", None)
        self.model_walker = kwargs.get("model_walker", None)
        self.load_model = kwargs.get("load_model", None)
        self.p1 = kwargs.get("p1", 0)
        self.p2 = kwargs.get("p2", 0)

    def _converged(self):
        """
        Returns True if beam centroids are at the same positions as p1 and p2.
        Returns False otherwise.
        """
        if self.monitor.current_centroids == np.array((self.p1, self.p2)):
            return True
        else:
            return False
        
    def _modelbuild(self):
        """
        Runs the model building => modelwalk loop
        """
        self.model_builder = kwargs.get("model_builder", self.model_builder)
        
        # Create a new model_builder instance if we havent
        if self.model_builder is None:
            self.model_builder = ModelBuilder(self.monitor)

        # TODO: Build a model using some input parameters denoting what
        # subsection of the data should be used
        # Possible inputs:
        # # Last n inputs for alpha1, alpha2, cent1, cent2
        # # All alpha1, alpha2, cent1, cent2 for current alignment
        # # All directly inputted alpha1, alpha2, cent1, cent2
        # # All alpha1, alpha2, cent1, cent2 for previous alignment
        self.model = self.model_builder.build()

        # Create a new model walker instance if we havent already
        if self.model_walker is None:
            self.model_walker = ModelWalker(self.walker, self.model)
        # Get new alphas from model_walker
        self.model_walker.step(do_move=True, model=self.model)        
        
    def _set_goal_points(self, model):
        model.p1 = self.p1
        model.p2 = self.p2
        return model
        
    def _load(self, saved_model):
        model_module = importlib.import_module("pswalker.models.{0}".format(
            saved_model))
        model = model_module.get_model()
        model = self._set_goal_points(model)
        return model
        
    def _modelwalk(self):
        """
        Runs the modelwalk loop.
        """
        self.model = kwargs.get("model", self.model)        
        self.load_model = kwargs.get("load_model", self.load_model)
        self.model_walker = kwargs.get("model_walker", self.model_walker)
        
        if self.load_model:
            # Load the model from a saved module
            # # Add a check if model was inputted or exists and the user set
            # load_model to be True
            self.model = self._load(self.load_model)
        elif self.model is None:
            raise CNCException

        # Create a new model walker instance if we havent already
        if self.model_walker is None:
            self.model_walker = ModelWalker(self.walker, self.model)
        # Get new alphas from model_walker
        self.model_walker.step(do_move=True)

    def _iterwalk(self):
        """
        Runs the iterwalk loop until convergence
        """
        self.iter_walker = kwargs.get("iter_walker", self.iter_walker)

        if self.iter_walker is None:
            self.iter_walker = IterWalker(self.walker, self.monitor, 
                                          p1=self.p1, p2=self.p2)
        while not self._converged:
            # Get new alpha(s) from iter_walker and move to them
            self.iter_walker.step(mirror_1=True)
            self.iter_walker.step(mirror_2=True)

    def walk(self, mode='iter'):
        """
        Top level method that will call each of the walking algorithms
        singularly or in sequences depending on the inputted walk mode.
        """
        self.p1    = kwargs.get("p1", 0)
        self.p2    = kwargs.get("p2", 0)
        self.model = kwargs.get("model", self.model)
        self.load_model    = kwargs.get("load_model", self.load_model)
        self.iter_walker   = kwargs.get("iter_walker", self.iter_walker)
        self.model_walker  = kwargs.get("model_walker", self.model_walker)
        self.model_builder = kwargs.get("model_builder", self.model_builder)

        if mode == "iter":
            # Run iterwalk algorithm until completion or failure
            self._iterwalk()
        elif mode == "model":
            self.load_model = kwargs.get("load_model", self.load_model)

            # Run a step of modelwalk. End walk execution after step.
            self._modelwalk()
        elif mode == "build":
            # Build a model using saved data then run a step of modelwalk.
            self._modelbuild()
        elif mode == "auto":
            # (1) If there is a model ready to be loaded, load it and run model
            # walk
            # 	If model walk fails, run (3)
            #	If converges, end run
            # (2) If no model is provided but enough data to build a model, build
            # a new one
            #	Pass built model into modelwalk and run (1)
            # (3) No model provided and one cannot be built
            #   Take iterwalk step
            #	If midway through step enough data is collected to build a new
            #	model, run (2)
            #	If converges, end run
            raise NotImplementedError            
        else:
            raise CNCException
            	