import math
import warnings
from enum import Enum
from functools import partial
from pathlib import Path
from typing import Optional, Sequence, cast

import imageio
import matplotlib
import napari
import napari.layers
import napari.viewer
import numpy as np
import pandas as pd
from magicgui.widgets import (
    ComboBox,
    Container,
    FileEdit,
    LineEdit,
    PushButton,
    RadioButtons,
    Select,
    TextEdit,
    create_widget,
)

from napari_feature_classifier.annotator_init_widget import LabelAnnotatorTextSelector
from napari_feature_classifier.annotator_widget import (
    LabelAnnotator,
    get_class_selection,
)


def main():
    lbls = imageio.imread(Path("sample_data/test_labels.tif"))
    labels = np.unique(lbls)[1:]

    viewer = napari.Viewer()
    lbls_layer = viewer.add_labels(lbls)
    lbls_layer.features = get_features(labels, n_features=6)
    widget = ClassifierWidget(viewer)
    viewer.window.add_dock_widget(widget)
    viewer.show(block=True)


def get_features(labels: Sequence[int], n_features: int = 10, seed: int = 42):
    columns = [f"feature_{i}" for i in range(n_features)]
    rng = np.random.default_rng(seed=seed)
    features = rng.random(size=(len(labels), n_features))
    return pd.DataFrame(index=labels, columns=columns, data=features)


class ClassifierInitContainer(Container):
    def __init__(self, feature_options: list[str]):
        self._name_edit = LineEdit(value="classifier")
        self._feature_combobox = Select(choices=feature_options, allow_multiple=True)
        self._annotation_name_selector = LabelAnnotatorTextSelector()
        self._initialize_button = PushButton(text="Initialize")
        super().__init__(
            widgets=[
                self._name_edit,
                self._feature_combobox,
                self._annotation_name_selector,
                self._initialize_button,
            ]
        )


class ClassifierRunContainer(Container):
    def __init__(self, viewer: napari.viewer.Viewer, class_names: list[str]):
        self._annotator = LabelAnnotator(viewer, get_class_selection(class_names))
        self._run_button = PushButton(text="Run")
        self._save_button = PushButton(text="Save")
        super().__init__(
            widgets=[
                self._annotator,
                self._run_button,
                self._save_button,
            ]
        )


class LoadFeaturesContainer(Container):
    pass


class LoadClassifierContainer(Container):
    pass


class ClassifierWidget(Container):
    def __init__(self, viewer: napari.viewer.Viewer):
        self._viewer = viewer
        # Extract feature for first label layer
        label_layer = [
            l for l in self._viewer.layers if isinstance(l, napari.layers.Labels)
        ][0]
        feature_names = list(label_layer.features.columns)
        self._init_container = ClassifierInitContainer(feature_names)
        print(type(self._init_container))
        super().__init__(widgets=[self._init_container])
        self._init_container._initialize_button.clicked.connect(
            self.initialize_run_widget
        )

    def initialize_run_widget(self):
        class_names = self._init_container._annotation_name_selector.get_class_names()
        # FIXME: Parse selected features
        # FIXME: Parse selected name
        self.close()
        # self.runner_container = ClassifierRunContainer(self.viewer, class_names)


if __name__ == "__main__":
    main()
