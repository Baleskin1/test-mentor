"""
solution.py file meant to solve the test for position of
Software Development Intern (DevOps) (Mechanical Analysis Division, R&D, Siemens PLM Software)

:author Baleskin Vitalii
"""

from io import TextIOWrapper
import os
import re
from typing import Tuple

def first_test(folders: set[str], report: TextIOWrapper)->bool:
    """
    ft_run and ft_reference directories should both exist
    :param folders - the list of subfolders in the test folder
    :param report - the report file for the test
    """
    flag_fail = False
    if "ft_reference" not in folders:
        report.write("FAIL\n")
        report.write("directory missing: ft_reference\n")
        flag_fail = True

    if "ft_run" not in folders:
        if not flag_fail:
            report.write("FAIL\n")
        report.write("directory missing: ft_run\n")
        flag_fail = True
    return flag_fail


def second_test(path: str, report: TextIOWrapper)->Tuple[bool, set[str]]:
    """
    *.stdout file and folder names are the same (as set equality)
    :param path - path to the test folder
    :param report - the report file for the test
    """
    reference_folder = path + "/ft_reference"
    run_folder = path + "/ft_run"
    reference_subfolders = set(os.listdir(reference_folder))
    run_subfolders = set(os.listdir(run_folder))
    # folders present in both reference in run can be found
    # as an intersection of the two sets
    present_folders = run_subfolders.intersection(reference_subfolders)
    missing_str = ""  # buffer for all information on missing files
    extra_str = ""  # buffer for all information on extra files
    if run_subfolders != reference_subfolders:
        for miss in reference_subfolders.difference(run_subfolders):
            missing_str+="'"+miss+'/'+miss+".stdout' "

        for ex in run_subfolders.difference(reference_subfolders):
            for file in os.listdir(run_folder + "/" + ex):
                if file.endswith(".stdout"):
                    extra_str+="'" + ex+'/'+file+"' "

    for present_folder in present_folders:
        folders = {
            "ref": reference_folder + "/" + present_folder,
            "run": run_folder + "/" + present_folder
            }
        for mis in set(os.listdir(folders["ref"])).difference(set(os.listdir(folders["run"]))):
            missing_str+="'" + present_folder + "/" + mis + "' "

        for ex in set(os.listdir(folders["run"])).difference(set(os.listdir(folders["ref"]))):
            if ex.endswith(".stdout"):
                extra_str += "'" + present_folder + "/" + ex + "' "

    if missing_str != "": # if there are any missing elements, complete the message
        missing_str = "In ft_run there are missing files present in ft_reference: " + missing_str

    if extra_str != "": # if there are any extra elements, complete the message
        extra_str = "In ft_run there are extra files not present in ft_reference: " + extra_str

    if missing_str != "" or extra_str != "":
        report.write("FAIL\n" + missing_str + ("\n" if missing_str != "" else "") + extra_str)

    return missing_str != "" or extra_str != "", present_folders


def process_lines(lines: list[str])->dict:
    """
    processes a set of lines for bricks total and memory working set peak
    :param lines: an array of lines
    """
    flag_bricks = True
    flag_wsp = True
    total = None
    max_wsp = 0
    for line in reversed(lines):
        # find the last line of format
        if flag_bricks and line.startswith("MESH::Bricks: Total="):
            parsed = re.match(r'MESH::Bricks: Total=(?P<total>.*) Gas=*', line)
            total = int(parsed.group('total'))
            flag_bricks = False

        # find the last line of format, or the one with the maximum Workin Set Peak Memory
        if flag_wsp and line.startswith("Memory Working Set Current"):
            parsed = re.match(
                r'Memory Working Set Current = [\d.]* Mb, Memory Working Set Peak = (?P<wsp>.*) Mb',
                line)
            #flag_wsp = False  # uncomment to get results similar to the reference file
            if float(parsed.group('wsp')) > max_wsp:
                max_wsp = float(parsed.group('wsp'))
    return {"total":total, "wsp":max_wsp}


def process_file(path: str)->dict:
    """
    processes a file for bricks total and memory working set peak
    :param path - path to the file to be processed
    """
    with open(path, "r", encoding="utf-8") as ref:
        lines = ref.readlines()
        return process_lines(lines)


def third_and_fourth_tests(path: str, present_folders: set[str], report: TextIOWrapper)->bool:
    """
    third test: in files check for abssence of lines containing "error"
                and presence of "Solver finished at" line
    fourth test: a) find final total number of bricks in reference and run files,
                    check that the relative run/ref difference < 0.1
                 b) relative run/ref difference of (max per file) working set peak
                    memory should be < 0.5
    NOTE: in the reference output, the search for working set peak value is done the same way
          as the total number of bricks - the last such line is taken as a source.
          In the task, however, the maximum working set peak value is to be found
    :param path - path to the test folder
    :param present_folders - folders, present in the ft_run and ft_reference directories
    :param report - the report file for the test
    """
    output = ""
    for present_file in sorted(  # sort added for correct file order
        [present_folder + "/" + present_folder + ".stdout" for present_folder in present_folders]
    ):
        with open(path + "/ft_run/" + present_file, "r", encoding="utf-8") as run:
            lines = run.readlines()
            err_lines = ""
            solver_line = present_file + ":  missing 'Solver finished at'\n"
            for i,line in enumerate(lines):  # third test
                if "error" in line.lower().replace(":", " ").split():
                    err_lines += present_file + "(" + str(i+1) + "): " + line
                if line.startswith("Solver finished at"):
                    solver_line = ""
            # start of the fourth test code
            run_stats = process_lines(lines)
            ref_stats = process_file(path + "/ft_reference/" + present_file)
            wsp_line = ''
            total_line = ''
            if abs(run_stats["wsp"]/ref_stats["wsp"] - 1) >= 0.5:  # criterion of 4.(a)
                wsp_line += present_file + ": different 'Memory Working Set Peak' (ft_run="
                wsp_line += str(run_stats["wsp"]) + ", ft_reference=" + str(ref_stats["wsp"])
                wsp_line += f", rel.diff={(round(run_stats['wsp']/ref_stats['wsp'] - 1, 2)):.2f}"
                wsp_line += ", criterion=0.5)\n"

            if abs(run_stats['total']/ref_stats['total'] - 1) >= 0.1:  # criterion of 4.(b)
                total_line += present_file + ": different 'Total' of bricks (ft_run="
                total_line += str(run_stats['total']) + ", ft_reference=" + str(ref_stats['total'])
                total_line += ", rel.diff="
                total_line += f"{(round((run_stats['total']/ref_stats['total'] - 1), 2)):.2f}"
                total_line += ", criterion=0.1)\n"

            if solver_line != "" or err_lines != "" or wsp_line != "" or total_line != "":
                output += err_lines + wsp_line + total_line + solver_line

    if output != "":
        report.write("FAIL\n")
        report.write(output)

    return output != ""


def generate_report(path: str):
    """
    Generate the report for a certain test.
    The generation cosists of conducting 4 tests as per the task.
    :param path - the path to the test folder
    """
    with open(path+"/"+"report.txt", "w", encoding="utf-8") as report:
        folders = os.listdir(path)
        if first_test(folders, report):
            return
        # first test passed
        flag_fail, present_folders = second_test(path, report)
        if flag_fail:
            return
        # second test passed
        if not third_and_fourth_tests(path, present_folders, report):
            #third and fourth tests passed
            report.write("OK\n")


def main():
    """
    main function of the solution
    processes the test sets
    """
    test_sets = os.listdir("./logs")
    for test_set in test_sets:
        tests = os.listdir("./logs/"+test_set)
        for test in tests:
            path = "./logs/"+test_set+"/"+test
            generate_report(path)

        for test in tests:
            path = "./logs/"+test_set+"/"+test
            with open(path+"/"+"report.txt", "r", encoding="utf-8") as report:
                data = report.readlines()
                # for correct text representation (e.g. no 'extra' empty lines)
                data[-1] = data[-1].removesuffix('\n')
                verdict = data[0].removesuffix('\n')
                print(verdict + ":", test_set+"/" + test + "/")
                if verdict == "FAIL":
                    print(*data[1:], sep='')

if __name__ == "__main__":
    main()
    