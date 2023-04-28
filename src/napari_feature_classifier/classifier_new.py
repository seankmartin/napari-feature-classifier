# FIXME: Get rid of show_info in classifier class
import pickle
import random
import string
from typing import Sequence

import pandas as pd
import pandera as pa
import xxhash

import numpy as np
import pandas as pd
from napari.utils.notifications import show_info
from napari_feature_classifier.classifier_utils import (
    get_input_and_internal_schemas,
    get_normalized_hash_column,
)


class Classifier:
    def __init__(self, feature_names, class_names):
        self._feature_names: list[str] = list(feature_names)
        self._class_names: list[str] = list(class_names)
        self._index_columns: list[str] = ["roi_id", "label"]
        self._input_schema, self._schema = get_input_and_internal_schemas(
            feature_names=feature_names,
            index_columns=self._index_columns,
            class_names=self._class_names,
        )
        # TODO: `self._schema.example(0)` does not return correct datatypes for
        # MultiIndex (issue: https://github.com/unionai-oss/pandera/issues/1049).
        # Can remove `self._schema.validate` call once fixed.
        self._data: pd.DataFrame = self._schema.validate(self._schema.example(0))

    def train(self):
        # TODO: Train the classifier
        show_info("Training classifier...")
        # TODO: Share training score

    def predict(self, df):
        # FIXME: Generate actual predictions for the df
        # FIXME: SettingWithCopyWarning => check if the actual run still
        # generates one, when we actually predict something
        with pd.option_context("mode.chained_assignment", None):
            df["predict"] = np.random.randint(1, 4, size=len(df))
        return df[["predict"]]

    def predict_on_dict(self, dict_of_dfs):
        # Make a prediction on each of the dataframes provided
        predicted_dicts = {}
        for roi in dict_of_dfs:
            show_info(f"Making a prediction for {roi=}...")
            predicted_dicts[roi] = self.predict(dict_of_dfs[roi])
        return predicted_dicts

    def add_features(self, df_raw: pd.DataFrame):
        # TODO: make sure objects with `annotation` == np.na get removed.
        show_info("Adding features...")

        df_valid = self._validate_input_features(df_raw)
        # Select index of annotations to be removed
        index = self._data.index.difference(df_valid.index)
        merged_data = pd.concat([self._data.loc[index], df_valid]).sort_index()

        index_delete = df_valid[df_valid.annotations == -1].index
        self._data = merged_data.drop(index=index_delete)

    def _validate_input_features(self, df: pd.DataFrame) -> pd.DataFrame:
        # Drop rows that don't have annotations
        df_annotated = df.dropna(subset="annotations")

        # Drop rows that have features with `NA`s, notify the user.
        df_no_nans = df_annotated.dropna()
        if len(df_no_nans) != len(df):
            print(
                f"Dropped {len(df)-len(df_no_nans)}/{len(df)} "
                "objects because of features that contained `NA`s"
            )

        # Validat the dataframe according to the schemas
        df_valid_input = self._input_schema.validate(df_no_nans)
        df_valid_internal = df_valid_input.assign(
            hash=get_normalized_hash_column(df_valid_input, self._index_columns)
        ).set_index(self._index_columns)
        return df_valid_internal

    def add_dict_of_features(self, dict_of_features):
        # Add features for each roi
        # dict_of_features is a dict with roi as key & df as value
        for roi in dict_of_features:
            if "roi_id" not in dict_of_features[roi]:
                df = dict_of_features[roi]["roid_id"] = roi
            else:
                df = df = dict_of_features[roi]
            show_info(f"Adding features for {roi=}...")
            self.add_features(df)

    def get_class_names(self):
        return self._class_names

    def get_feature_names(self):
        return self._feature_names

    def save(self, output_path):
        # TODO: Check that pickle dump works once helper functions become part of the class
        show_info(f"Saving classifier at {output_path}...")
        with open(output_path, "wb") as f:
            f.write(pickle.dumps(self))

    def __repr__(self):
        return f"{self.__class__.__name__}\n{repr(self._data)}"

def join_index_columns(df: pd.DataFrame, index_columns: Sequence[str]) -> pd.Series:
    orig_index = df.index
    return pd.Series(
        (
            df.reset_index()
            .loc[:, list(index_columns)]
            .apply(lambda x: "_".join(map(str, x)), axis=1)
        ).values,
        index=orig_index,
    ).rename("object_id")


def hash_single_object_id(object_id: str) -> float:
    max_value = 2**32
    return xxhash.xxh32(object_id).intdigest() / max_value


def get_normalized_hash_column(
    df: pd.DataFrame, index_columns: Sequence[str] = ("roi_id", "label")
) -> pd.Series:
    return join_index_columns(df, index_columns=index_columns).apply(
        hash_single_object_id
    )


def get_random_object_id(n_chars=10):
    return "".join(random.choice(string.ascii_lowercase) for i in range(n_chars))


# TODO: This is cursed, annotations is supposed to be a nullable pandas int type but
# those don't seem to be recognized by pa.Check(ignore_na=True) when doing the checks :(
def get_input_and_internal_schemas(
    feature_names: Sequence[str],
    class_names: Sequence[str],
    index_columns: Sequence[str] = ("roi_id", "label"),
) -> tuple[pa.DataFrameSchema, pa.DataFrameSchema]:
    assert len(index_columns) == 2
    input_schema = pa.DataFrameSchema(
        columns={
            index_columns[0]: pa.Column(pa.String, coerce=True),
            index_columns[1]: pa.Column(pa.UInt64, coerce=True),
            "annotations": pa.Column(
                pa.Int64,
                # pd.Int64Dtype(),
                coerce=True,
                # checks=pa.Check.between(1, len(class_names) + 1),
                checks=[
                    pa.Check(
                        lambda x: 1 <= x <= len(class_names) or x == -1,
                        element_wise=True,
                        ignore_na=True,
                    ),
                ],
                nullable=True,
            ),
            **{
                feature_name: pa.Column(pa.Float32, coerce=True)
                for feature_name in feature_names
            },
        },
        strict="filter",
        unique=list(index_columns),
    )

    internal_schema = input_schema.set_index(list(index_columns)).add_columns(
        {"hash": pa.Column(pa.Float32, coerce=True, checks=pa.Check.between(0.0, 1.0))}
    )
    return input_schema, internal_schema
