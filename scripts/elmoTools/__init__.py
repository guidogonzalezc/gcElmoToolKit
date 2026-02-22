import os 

def main_folder_path():
    """
    Function to determine the main folder path of the project by finding the real path of the current file
    and splitting it to get the main directory.
    Returns:
        str: The main folder path of the project.
    """
    complete_path = os.path.realpath(__file__)
    main_path = complete_path.split("\scripts")[0]
    print(complete_path)
    print(main_path)
    return main_path

main_folder_path()