import json
import os

class DataExport:
    """
    Class to handle data export and import for Maya rigging modules.
    This class manages the creation of a build cache file, appending data for different modules,
    and retrieving specific data attributes for modules.
    """
    def __init__(self):
        """
        Initializes the DataExport class, setting up paths for the build cache file.
        Args:
            self: Instance of the DataExport class.
        """ 

        complete_path = os.path.realpath(__file__)
        self.relative_path = complete_path.split("\\scripts")[0]
        self.build_path = os.path.join(self.relative_path, "build", "build_cache.cache")

    def new_build(self):
        """
        Creates a new build cache file by initializing an empty JSON structure.
        Args:
            self: Instance of the DataExport class.
        """

        with open(self.build_path, "w") as f:
            json.dump({}, f, indent=4)

    def append_data(self, module_name, data_dict):
        """
        Appends data for a specific module to the build cache file.
        Args:
            module_name (str): The name of the module for which data is being appended.
            data_dict (dict): A dictionary containing the data to be appended for the module.
        """

        if os.path.exists(self.build_path):
            with open(self.build_path, "r") as f:
                try:
                    current_data = json.load(f)
                except json.JSONDecodeError:
                    current_data = {}
        else:
            current_data = {}

        if module_name not in current_data:
            current_data[module_name] = {}

        current_data[module_name].update(data_dict)

        with open(self.build_path, "w") as f:
            json.dump(current_data, f, indent=4)

    def get_data(self, module_name, attribute_name):
        """
        Retrieves specific data for a module from the build cache file.
        Args:
            module_name (str): The name of the module from which data is being retrieved.
            attribute_name (str): The name of the attribute to retrieve from the module's data.
        Returns:
            The value of the specified attribute for the given module, or None if not found.
        """
        if os.path.exists(self.build_path):
            with open(self.build_path, "r") as f:
                try:
                    current_data = json.load(f)
                except json.JSONDecodeError:
                    current_data = {}
        else:
            current_data = {}

        for module, data in current_data.items():
            if module == module_name:
                for attr, value in data.items():
                    if attr == attribute_name:
                        return value
        return None


