"""
Helper module to search files.
"""
import itertools
import logging
import os
import os.path
import re
from typing import Optional, NamedTuple, Callable, List, Union

logger = logging.getLogger(__name__)


class FileResolveError(ValueError):
    pass


class FileNotFound(FileResolveError):
    pass


class MultipleFilesAreFound(FileResolveError):
    pass


class SearchResult(NamedTuple):
    path: str
    level: int


def search_files(start_dirs: Union[str, List[str]], max_depth: int, file_predicate: Callable[[str], bool], *,
                 exclude_dir_predicate: Optional[Callable[[str], bool]] = None, stop_on_top_level=True) \
        -> List[SearchResult]:
    """
    Search files in the directory.

    :param start_dirs:
    :param max_depth:
    :param file_predicate:
    :param exclude_dir_predicate:
    :param stop_on_top_level: abort deeper search if any files are found at top level.
    :return:
    """

    if isinstance(start_dirs, str):
        start_dirs = [start_dirs]
    start_dirs = [os.path.abspath(start_dir) for start_dir in start_dirs]
    for start_dir in start_dirs:
        if not os.path.isdir(start_dir):
            raise ValueError(f"start_dir \"{start_dir}\" isn't a directory")

    dirs_to_visit = start_dirs
    result = []
    for level_no in range(max_depth):
        current_dirs_to_visit, dirs_to_visit = dirs_to_visit, []
        for dir_entry in itertools.chain.from_iterable(os.scandir(path) for path in current_dirs_to_visit):
            if dir_entry.is_dir():
                if exclude_dir_predicate is None or not exclude_dir_predicate(dir_entry.path):
                    dirs_to_visit.append(dir_entry.path)
            else:
                if file_predicate(dir_entry.path):
                    result.append(SearchResult(dir_entry.path, level_no))
        if stop_on_top_level and result:
            break

    return result


_ELF_SIGNATURE = b'\x7F\x45\x4C\x46'
_ELF_EXTS = ('.elf', '')


def _is_elf_file(path):
    _, ext = os.path.splitext(path)
    if ext.lower() not in _ELF_EXTS:
        return False

    with open(path, 'rb') as f:
        prefix = f.read(4)
    return prefix == _ELF_SIGNATURE


_BUILD_DIR_RE = re.compile(r'\bbuild\b', re.IGNORECASE)
_MAX_ELF_SEARCH_DEPTH = 2


def _build_dir_predicate(path):
    basename = os.path.basename(path)
    return _BUILD_DIR_RE.search(basename) is not None


def resolve_elf_file_location(project_dir: str, elf_path: Optional[str]) -> str:
    """
    Resolve elf file location.
    """
    elf_dirs = []

    if elf_path is None:
        # try to find elf file automatically
        for dir_entry in os.scandir(project_dir):
            if not dir_entry.is_dir():
                continue
            if not _build_dir_predicate(dir_entry.path):
                continue
            elf_dirs.append(dir_entry.path)
        if not elf_dirs:
            elf_dirs.append(project_dir)
    else:
        elf_path = os.path.abspath(elf_path)
        if not os.path.exists(elf_path):
            raise FileNotFound(f".elf path \"{elf_path}\" does not exists")
        if os.path.isfile(elf_path):
            if _is_elf_file(elf_path):
                return elf_path
            else:
                raise FileResolveError(f"File \"{elf_path}\" isn't elf file")
        else:
            elf_dirs.append(elf_path)

    # search elf files in the candidate directories
    elf_files = search_files(
        start_dirs=elf_dirs,
        max_depth=_MAX_ELF_SEARCH_DEPTH,
        file_predicate=_is_elf_file,
        stop_on_top_level=True
    )

    if len(elf_files) == 1:
        return elf_files[0].path
    elif len(elf_files) > 1:
        raise MultipleFilesAreFound(
            "Multiple elf files are found:\n{}".format('\n'.join(elf_file.path for elf_file in elf_files))
        )
    else:
        raise FileNotFound("No elf files are found in the directories:\n{}".format('\n'.join(elf_dirs)))


_MAX_CFG_SEARCH_DEPTH = 2


def _is_openocd_config_file(path):
    _, ext = os.path.splitext(path)
    return '.cfg' == ext.lower()


def resolve_openocd_config_file(project_dir: str, config_path: Optional[str]) -> str:
    """
    Resolve openocd file location.
    """
    search_dir = project_dir
    if config_path is not None:
        config_path = os.path.abspath(config_path)
        if os.path.isfile(config_path):
            return config_path
        else:
            search_dir = config_path
    cfg_files = search_files(
        start_dirs=search_dir,
        max_depth=_MAX_CFG_SEARCH_DEPTH,
        file_predicate=_is_openocd_config_file,
        stop_on_top_level=True
    )
    if len(cfg_files) == 1:
        return cfg_files[0].path
    elif len(cfg_files) > 1:
        raise MultipleFilesAreFound(
            "Found multiple cfg files:\n{}".format('\n'.join(cfg_file.path for cfg_file in cfg_files))
        )
    else:
        raise FileNotFound(f"No cfg files are found in the directory:\n{search_dir}")
