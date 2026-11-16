import sqlite3
import threading
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from qcodes.dataset.data_set import DataSet


def test_get_metadata_from_dataset(dataset: "DataSet") -> None:
    dataset.add_metadata("something", 123)
    something = dataset.get_metadata("something")
    assert 123 == something


def test_get_nonexisting_metadata(dataset: "DataSet") -> None:
    data = dataset.get_metadata("something")
    assert data is None


def test_get_metadata_lower_upper_case(dataset: "DataSet") -> None:
    dataset.add_metadata("something", 123)

    something_lower = dataset.metadata.get("something", "didnt find lowercase")
    assert something_lower == 123

    something_upper = dataset.metadata.get("Something", "didnt find uppercase")
    assert something_upper == "didnt find uppercase"

    get_something_lower = dataset.get_metadata("something")
    assert get_something_lower == 123

    get_something_upper = dataset.get_metadata("Something")
    assert get_something_upper is None


@pytest.mark.parametrize("existing_tag", [False, True])
def test_add_metadata_waits_for_another_writer(
    dataset: "DataSet", existing_tag: bool
) -> None:
    """
    Another connection that writes to the database, such as the background
    writer of a measurement, holds the write lock for a moment. add_metadata
    reads the runs table before it writes to it, so it must take the write lock
    when its transaction starts: else SQLite does not wait for the lock and
    raises "database is locked".
    """
    if existing_tag:
        dataset.add_metadata("something", 1)

    assert dataset.path_to_db is not None
    other = sqlite3.connect(
        dataset.path_to_db, isolation_level=None, check_same_thread=False
    )
    other.execute("BEGIN IMMEDIATE")
    release = threading.Timer(0.2, other.commit)
    release.start()
    try:
        dataset.add_metadata("something", 123)
    finally:
        release.join()
        other.close()

    assert dataset.get_metadata("something") == 123
