"""
solution_v2.py file meant to solve the test for position of
Software Development Intern (DevOps) (Mechanical Analysis Division, R&D, Siemens PLM Software)

:author Baleskin Vitalii
"""


import functools
import os
import re
import multiprocessing


class Regexes:
    memory_peak = re.compile(
        r'Memory Working Set Current = [\d.]* Mb, Memory Working Set Peak = (?P<value>.*) Mb'
        )
    bricks_total = re.compile(r'MESH::Bricks: Total=(?P<value>.*) Gas=*')

class FileData:
    def __init__(self, name: str) -> None:
        self.name = name
        self.errors = []  # expected structure [[line number, error line]]
        self.solver_presence = False
        self.memory_peak = 0.0
        self.total_bricks = 0.0

def process_file(path_to_folder: str, filename: str, check_errors_and_solver_presence: bool) -> FileData:
    with open(path_to_folder+filename, 'r', encoding='utf-8') as file:
        result = FileData(filename)
        for line_number, line in enumerate(file):
            if check_errors_and_solver_presence:
                if "error" in line.lower().replace(":", " ").split():
                    result.errors.append((line_number+1, line))
                if line.startswith("Solver finished at"):
                    result.solver_presence = True

            parsed_wsp = Regexes.memory_peak.match(line)
            if parsed_wsp is not None:
                wsp = float(parsed_wsp.group("value"))
                if wsp > result.memory_peak:
                    result.memory_peak = wsp

            parsed_total = Regexes.bricks_total.match(line)
            if parsed_total is not None:
                result.total_bricks = int(parsed_total.group("value"))
        return result


def _get_quoted_sequence(strings: list[str]):
    """
    returns a sequence of strings joined as:
    'string1', 'string2', ..., 'stringn'
    """
    add_quotes = lambda x: f"'{x}'"
    return ", ".join(map(add_quotes, strings))

def check_test(path_to_logs: str, test_name: str):
    full_path = path_to_logs + '/' + test_name
    walk_results = os.walk(full_path)
    directories = set(next(walk_results)[1])

    with open(full_path + "report.txt", "w", encoding="utf-8") as report:

        missing_directories = False
        for directory in ["ft_run", "ft_reference"]:
            if directory not in directories:
                report.write(f"directory missing: {directory}\n")
                missing_directories = True

        if missing_directories:
            return test_name

        run_files = set()
        reference_files = set()
        for path, subdirectories, files in walk_results:
            for file in files:
                if file.endswith(".stdout"):
                    filename = file.split('.')[0] + '/' + file
                    if "ft_run" in path:
                        run_files.add(filename)
                    elif "ft_reference" in path:
                        reference_files.add(filename)

        if run_files != reference_files:
            missing_files = sorted(
                reference_files.difference(run_files))
            extra_files = sorted(run_files.difference(reference_files))
            if missing_files:
                report.write("In ft_run there are missing files present in ft_reference: ")
                report.write(_get_quoted_sequence(missing_files) + "\n")

            if extra_files:
                report.write("In ft_run there are extra files not present in ft_reference: ")
                report.write(_get_quoted_sequence(extra_files) + "\n")

            return test_name

        reference_path = full_path + "ft_reference/"
        run_path = full_path + "ft_run/"

        for filename in sorted(run_files):
            reference_result = process_file(reference_path, filename, False)
            run_result = process_file(run_path, filename, True)
            for line_number, error in run_result.errors:
                report.write(f"{filename}({line_number}): {error}")
            if not run_result.solver_presence:
                report.write(f"{filename}: missing 'Solver finished at'\n")

            working_set_peak_rel_diff = run_result.memory_peak/reference_result.memory_peak - 1
            if abs(working_set_peak_rel_diff) > 0.5:
                report.write(f"{filename}: different 'Memory Working Set Peak' ")
                report.write(f"(ft_run={run_result.memory_peak},")
                report.write(f" ft_reference={reference_result.memory_peak},")
                report.write(f" rel.diff={working_set_peak_rel_diff:.2f}, criterion=0.5)\n")

            total_bricks_rel_diff = run_result.total_bricks/reference_result.total_bricks - 1
            if abs(total_bricks_rel_diff) > 0.1:
                report.write(f"{filename}: different 'Total' of bricks (")
                report.write(f"ft_run={run_result.total_bricks},")
                report.write(f" ft_reference={reference_result.total_bricks},")
                report.write(f" rel.diff={total_bricks_rel_diff:.2f},")
                report.write(" criterion=0.1)\n")

        return test_name


def get_test_list(path_to_log_folder: str):
    """
    returns a list of available test names
    """
    tests = []
    for test_set in os.listdir(path_to_log_folder):
        for test in os.listdir(path_to_log_folder + '/' + test_set):
            tests.append(f'{test_set}/{test}/')
    return tests


def process_logs(path_to_log: str):
    """processes the logs as per the task"""
    tests = get_test_list(path_to_log)
    with multiprocessing.Pool() as pool:
        for test_name in pool.imap(functools.partial(check_test, path_to_log), tests):
            report_path = path_to_log+test_name+"report.txt"
            if os.path.getsize(report_path) > 0:
                print(f"FAIL: {test_name}")
                with open(report_path, 'r', encoding='utf-8') as report:
                    for line in report:
                        print(line, end='')
            else:
                print(f"OK: {test_name}")


if __name__ == "__main__":
    process_logs("./logs/")
