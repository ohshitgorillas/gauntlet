import pytest
from shared_helpers import load

pin = load("pin")


@pytest.mark.parametrize(
    "path, expected",
    [
        ("My Items.md", "my-items"),
        ("gauntlet/items/my-task.md", "my-task"),
        ("gauntlet/items/---.md", ""),
    ],
)
def test_slug_derives_kebab_name_from_file_path(path, expected):
    assert pin.slug(path) == expected
