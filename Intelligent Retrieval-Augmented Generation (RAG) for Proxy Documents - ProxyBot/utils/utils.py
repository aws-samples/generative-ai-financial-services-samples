import os
import re
import time
import shutil
import os
from parameters.logger import get_logger


logging = get_logger(__name__)


def strip_tag(text, tag):
    text = re.sub(f"\n", "<BR>", text)
    text = re.sub(f"^.*<{tag}>", "", text)
    text = re.sub(f"<\/{tag}>.*$", "", text)
    text = re.sub(f"<BR>", "\n", text)
    return text


def timer(message=""):
    def time_executor(time_func):
        def any_function(*args, **kwargs):
            start_time = time.time()
            _func = time_func(*args, **kwargs)
            logging.info(
                f"{message} execution time: {round((time.time()-start_time)/60, 3)} minutes\n"
            )
            return _func

        return any_function

    return time_executor


def fix_character_rendering(text):
    characters_dict = {
        "$": "\\$",
        "€": "\€",
        "£": "\£",
        "¥": "\¥",
        "*": "\*",
        "^": "\^",
        "_": "\_",
        "{": "\{",
        "}": "\}",
        "[": "\[",
        "]": "\]",
        "#": "\#",
        "~": "\~",
        "`": "\`",
        ">": "\&lt",
        "<": "\&gt",
        "|": "\|",
        "&": "\&",
        ":": "\:",
    }
    character_pattern = re.compile(
        "|".join(re.escape(key) for key in characters_dict.keys())
    )
    return character_pattern.sub(lambda match: characters_dict[match.group(0)], text)


def format_special_text(text):
    # Replace special characters with a span
    formatted_text = text.replace("$", '<span class="special-text">$</span>')
    return formatted_text


def get_raw_data(file_path):
    with open(file_path, "r") as file:
        data = file.read()
    return data


def human_readable_size(size, decimal_places=2):
    for unit in ["B", "KB", "MB", "GB", "TB", "PB"]:
        if size < 1024.0:
            break
        size /= 1024.0
    return f"{size:.{decimal_places}f} {unit}"


def get_directory_size(start_path="."):
    total_size = 0
    for dirpath, _, filenames in os.walk(start_path):
        for f in filenames:
            fp = os.path.join(dirpath, f)
            # skip if it is symbolic link
            if not os.path.islink(fp):
                total_size += os.path.getsize(fp)
    readable_size = human_readable_size(total_size)
    logging.info(f"Total size of {start_path}: {readable_size}")
    return total_size, readable_size


def delete_folder(folder_path):
    """
    Deletes a folder and its contents from the given full path.
    Args:
        folder_path (str): The full path of the folder to be deleted.
    """
    try:
        # Check if the path exists
        if os.path.exists(folder_path):
            # Removes the folder and its contents
            shutil.rmtree(folder_path)
            print(
                f"Folder '{folder_path}' and its contents have been deleted successfully."
            )
        else:
            print(f"The path '{folder_path}' does not exist.")
    except PermissionError:
        print(
            f"Permission denied to delete '{folder_path}'. Please check your access rights."
        )
    except Exception as e:
        print(f"An error occurred while deleting '{folder_path}': {e}")
