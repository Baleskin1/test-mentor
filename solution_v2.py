"""
solution_v2.py file meant to solve the test for position of
Software Development Intern (DevOps) (Mechanical Analysis Division, R&D, Siemens PLM Software)

:author Baleskin Vitalii
"""


import os
import re
import multiprocessing
from typing import Any, Callable, TextIO, Tuple


class FileResult:
    """
    Class containig check results for a single file
    """
    def __init__(self, name: str) -> None:
        self.name = name
        self.errors = []  # expected structure [[line number, error line]]
        self.solver_presence = False
        self.wsp = {"run": 0.0, "ref": 0.0, "rel.dif": 0.0, "criterion": 0.5}
        self.total_bricks = {"run": 0, "ref": 0, "rel.diff": 0.0, "criterion": 0.1}


    def failed_3(self) -> bool:
        """returns, whether the third test was failed"""
        return len(self.errors) or not self.solver_presence


    def failed_wsp(self) -> bool:
        """returns, whether the fourth test's (a) was failed"""
        return abs(self.wsp["rel.diff"]) > self.wsp["criterion"]


    def failed_total(self) -> bool:
        """returns, whether the fourth test's (b) was failed"""
        return abs(self.total_bricks["rel.diff"]) > self.total_bricks["criterion"]


    def report(self) -> str:
        """returns the report for the file"""
        result = ""
        if self.failed_3():
            for error in self.errors:
                result += f"{self.name}({error[0]}): {error[1]}"
            if not self.solver_presence:
                result += f"{self.name}: missing 'Solver finished at'\n"
        if self.failed_wsp():
            result += f"{self.name}: different 'Memory Working Set Peak' (ft_run={self.wsp['run']},"
            result += f" ft_reference={self.wsp['ref']},"
            result += f" rel.diff={self.wsp['rel.diff']:.2f}, criterion={self.wsp['criterion']})\n"
        if self.failed_total():
            result += f"{self.name}: different 'Total' of bricks ("
            result += f"ft_run={self.total_bricks['run']},"
            result += f" ft_reference={self.total_bricks['ref']},"
            result += f" rel.diff={self.total_bricks['rel.diff']:.2f},"
            result += f" criterion={self.total_bricks['criterion']})\n"
        return result



def update(line: str, prefix: str, regex: str, old_value: Any, updater: Callable) -> Any:
    """
    Updates the value with string
    :param line - line taken as a source
    :param prefix - determines the required prefix of the line
    :param regex - regex to get the value
    :param old_vale - prior value
    :param updater - some callable that takes the old value and the
        new value (as a string) and returns the new value
    """
    if line.startswith(prefix):
        parsed = re.match(regex, line)
        value = parsed.group('value')
        return updater(old_value, value)
    return old_value


def process_file(name: str, path_to_folder: str, open_file_func: Callable) -> FileResult:
    """
    process a single .stdout file into a FileResult
    :param name - name of the stdout file in format N/N.stdout
    :param path_to_run - path to the folder containing the run and reference folders.
    :param open_file_func - some callable, that allows to get contents of a file
            in a manner similar to open(...)
    """
    result = FileResult(name)
    wsp_re = r'Memory Working Set Current = [\d.]* Mb, Memory Working Set Peak = (?P<value>.*) Mb'
    bricks_re = r'MESH::Bricks: Total=(?P<value>.*) Gas=*'
    updater_take_last_int = lambda _, y: int(y)
    updater_find_max_float = lambda x, y: max(x, float(y))
    with open_file_func(path_to_folder + "ft_run/" + name, "r", encoding='utf-8') as file:
        for line_number, line in enumerate(file):
            if "error" in line.lower().replace(":", " ").split():
                result.errors.append((line_number+1, line))
            if line.startswith("Solver finished at"):
                result.solver_presence = True
            result.wsp["run"] = update(line, "Memory Working Set Current",
                wsp_re, result.wsp["run"], updater_find_max_float)
            result.total_bricks["run"] = update(line, "MESH::Bricks: Total=",
                bricks_re, result.total_bricks["run"], updater_take_last_int)

    with open_file_func(path_to_folder + "ft_reference/" + name, "r", encoding='utf-8') as file:
        for line_number, line in enumerate(file):
            result.wsp["ref"] = update(line, "Memory Working Set Current",
                wsp_re, result.wsp["ref"], updater_find_max_float)
            result.total_bricks["ref"] = update(line, "MESH::Bricks: Total=",
                bricks_re, result.total_bricks["ref"], updater_take_last_int)

    result.wsp["rel.diff"] = result.wsp["run"]/result.wsp["ref"] - 1
    result.total_bricks["rel.diff"] = result.total_bricks["run"]/result.total_bricks["ref"] - 1
    return result


class TestResult:
    """
    Class containing results for a single test
    """
    def __init__(self, full_name: str) -> None:
        self.full_name = full_name  # expecting /TEST_SET/TEST/
        self.missing_directories = []
        self.missing_files = []
        self.extra_files = []
        self.file_data: list[FileResult] = []  # a sorted list expected
        self.solver_presence = False


    def report(self) -> str:
        """returns the report for the test"""
        output = f"FAIL: {self.full_name}\n"
        add_quotes = lambda x: f"'{x}'"
        if self.missing_directories:
            for directory in self.missing_directories:
                output += f"directory missing: {directory}\n"
            return output

        if self.missing_files or self.extra_files:
            if self.missing_files:
                output += "In ft_run there are missing files present in ft_reference: "
                output += ", ".join(map(add_quotes, self.missing_files)) + "\n"
            if self.extra_files:
                output += "In ft_run there are extra files not present in ft_reference: "
                output += ", ".join(map(add_quotes, self.extra_files)) + "\n"
            return output

        for file_result in self.file_data:
            output += file_result.report()
        return f"OK: {self.full_name}\n" if output == f"FAIL: {self.full_name}\n" else output


    def write_report(self, writer: TextIO) -> None:
        """
        writes a report to file
        """
        writer.write(self.report())



class Test:
    """
    class, describing a single test and its data
    Also contains processing methods
    """
    def __init__(self, full_name: str) -> None:
        self.full_name = full_name
        self.directories = []
        self.run_files = set()
        self.reference_files = set()


    def check(self, path_to_log_folder: str, open_file_func: Callable) -> TestResult:
        """
        checks the provided test data
        :param path_to_log_folder - path to the folder that contains test logs
        :param open_file_func - function for opening files similar to open(...)
        """
        result = TestResult(self.full_name)
        for potential in ["ft_run", "ft_reference"]:
            if potential not in self.directories:
                result.missing_directories.append(potential)

        if result.missing_directories:
            return result

        if self.run_files != self.reference_files:
            result.missing_files = sorted(
                self.reference_files.difference(self.run_files))
            result.extra_files = sorted(self.run_files.difference(self.reference_files))
            return result

        for file in sorted(self.run_files):
            result.file_data.append(
                process_file(file, path_to_log_folder + '/' + result.full_name, open_file_func)
                )

        return result


    @staticmethod
    def read_from_fs(path_to_log_folder: str, test_full_name: str, traverse_func: Callable):
        """
        reads the data (directories, filenames,...) of a single test
        :param path_to_log_folder - path to logs
        :param test_full_name - full name of the test if form TEST_SET/TEST_NAME/
                (for futher details, see reference_result.txt)
        :param traverse_function - function for traversing the test folder.
                Should be similar to os.walk in terms of interface and return value format
        """
        test_data = Test(test_full_name)
        test_data.run_files= set()
        test_data.reference_files = set()
        full_path = path_to_log_folder + '/' + test_data.full_name
        walk_results = traverse_func(full_path)
        test_data.directories = next(walk_results)[1]
        for result in walk_results:
            for file in result[2]:
                if file.endswith(".stdout"):
                    filename = file.split('.')[0] + '/' + file
                    if "ft_run" in result[0]:
                        test_data.run_files.add(filename)
                    elif "ft_reference" in result[0]:
                        test_data.reference_files.add(filename)
        return test_data




def get_test_list(path_to_log_folder: str, list_subdirectories: Callable):
    """
    returns a list of available test names
    :param path_to_log_folder - path to the folder that contains logs
    :param list_subdirectories - some callable that returns
            a list of subdirs of a given path. Should be similar to os.listdir
            in terms of interface and return value format
    """
    tests = []
    for test_set in list_subdirectories(path_to_log_folder):
        for test in list_subdirectories(path_to_log_folder + '/' + test_set):
            tests.append(f'{test_set}/{test}/')
    return tests


def pipeline(args: Tuple):
    """
    The pipeline for processing each test
    :param args - [path to log folder, test full name]
    """
    path_to_logs = args[0]
    test_full_name = args[1]
    test_data = Test.read_from_fs(path_to_logs, test_full_name, os.walk)
    test_result = test_data.check(path_to_logs, open)
    with open(path_to_logs + '/' + test_result.full_name + "report.txt",
        'w', encoding='utf-8') as report:

        test_result.write_report(report)
    return test_result


def process(path_to_log: str):
    """processes the logs as per the task"""
    tests = get_test_list(path_to_log, os.listdir)
    with multiprocessing.Pool() as pool:
        test_results = pool.map(pipeline, zip([path_to_log]*len(tests), tests))
        for result in test_results:
            print(result.report().removesuffix('\n'))


if __name__ == "__main__":
    process("./logs")
