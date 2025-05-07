import pytest
import os
from cloud_pipelines_oasis_cli import main as oasis

test_data_path = os.path.join(os.path.dirname(__file__), "test_data")


def test_components_regenerate_python_function_component():
    oasis.components_regenerate_python_function_component(
        directory=os.path.join(test_data_path, "python_function_component_1")
    )


if __name__ == "__main__":
    pytest.main()
