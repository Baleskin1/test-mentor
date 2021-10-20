"""
solution.py file meant to solve the test for position of Software Development Intern (DevOps) (Mechanical Analysis Division, R&D, Siemens PLM Software)

:author Baleskin Vitalii 
"""

import os
import re


def process_lines(lines):
    flag_bricks = True
    flag_wsp = True
    total = None
    max_wsp = 0
    for line in reversed(lines):
        if flag_bricks and line.startswith("MESH::Bricks: Total="):
            parsed = re.match(r'MESH::Bricks: Total=(?P<total>.*) Gas=*', line)
            total = int(parsed.group('total'))
            flag_bricks = False
        
        if flag_wsp and line.startswith("Memory Working Set Current"):
            parsed = re.match(r'Memory Working Set Current = [\d.]* Mb, Memory Working Set Peak = (?P<wsp>.*) Mb', line)
            #flag_wsp = False  # uncomment to get results similar to the reference file
            if float(parsed.group('wsp')) > max_wsp:
                max_wsp = float(parsed.group('wsp'))
    return total, max_wsp


def process_file(path):
    with open(path, "r") as ref:
        lines = ref.readlines()
        return process_lines(lines)
        

def first_test(folders, report):
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


def second_test(path, report):
    reference_folder = path + "/ft_reference"
    run_folder = path + "/ft_run"
    reference_subfolders = set(os.listdir(reference_folder))
    run_subfolders = set(os.listdir(run_folder))
    extra = set()
    missing = set()
    any_extra = False
    any_missing = False
    missing_str = ""
    extra_str = ""
    if (run_subfolders != reference_subfolders):
        extra = run_subfolders.difference(reference_subfolders)
        missing = reference_subfolders.difference(run_subfolders)
        if len(missing):
            missing_str = "In ft_run there are missing files present in ft_reference: "
            any_missing = True
            for m in missing:
                missing_str+="'"+m+'/'+m+".stdout' "
        
        if len(extra):
            for e in extra:
                files = os.listdir(run_folder + "/" + e)
                if len(files):
                    for file in files:
                        if file.endswith(".stdout"):
                            if not any_extra:
                                extra_str = "In ft_run there are extra files not present in ft_reference: "
                                any_extra = True
                            extra_str+="'" + e+'/'+file+"' "
    
    present_folders = run_subfolders.intersection(reference_subfolders)
    for pf in present_folders:
        pref = reference_folder + "/" + pf
        prun = run_folder + "/" + pf
        run_files = set(os.listdir(prun))
        ref_files = set(os.listdir(pref))
        extra_files = run_files.difference(ref_files)
        missing_files = ref_files.difference(run_files)
        if len(missing_files):
            if not any_missing:
                missing_str = "In ft_run there are missing files present in ft_reference: "
                any_missing = True
            for m in missing_files:
                missing_str+="'" + pf + "/" + m + "' "
        
        if len(extra_files):
            for e in extra_files:
                if e.endswith(".stdout"):
                    if not any_extra:
                        extra_str = "In ft_run there are extra files not present in ft_reference: "
                        any_extra = True
                    extra_str += "'" + pf + "/" + e + "' "
    
    if any_missing or any_extra:
        report.write("FAIL\n" + missing_str + ("\n" if len(missing_str) else "") + extra_str)
        
    return any_missing or any_extra, present_folders


def third_and_fourth_tests(path, present_folders, report):
    reference_folder = path + "/ft_reference"
    run_folder = path + "/ft_run"
    present_files = []
    for pf in present_folders:
        filepath = pf + "/" + pf + ".stdout"
        present_files.append(filepath)
    
    present_files = sorted(present_files)
    test_fail = False
    output = ""
    for pf in present_files:
        run_path = run_folder + "/" + pf
        reference_path = reference_folder + "/" + pf
        with open(run_path) as run:
            lines = run.readlines()
            flag_solver = False
            flag_fail = False
            err_lines = ""
            solver_line = ""
            for i,line in enumerate(lines):
                if "error" in line.lower().replace(":", " ").split():
                    flag_fail = True
                    err_lines += pf + "(" + str(i+1) + "): " + line
                if line.startswith("Solver finished at"):
                    flag_solver = True
            
            if not flag_solver:
                solver_line = pf + ":  missing 'Solver finished at'\n"
            
            total, wsp = process_lines(lines)
            ref_total, ref_wsp = process_file(reference_path)
            wsp_line = ''
            total_line = ''
            if abs(wsp/ref_wsp - 1) >= 0.5:
                flag_fail = True
                wsp_line += pf + ": different 'Memory Working Set Peak' (ft_run=" + str(wsp) + ", ft_reference=" + str(ref_wsp) + (", rel.diff=%.2f"%(round((wsp/ref_wsp - 1), 2))) + ", criterion=0.5)\n"
            
            if abs(total/ref_total - 1) >= 0.1:
                flag_fail = True
                total_line += pf + ": different 'Total' of bricks (ft_run=" + str(total) + ", ft_reference=" + str(ref_total) + (", rel.diff=%.2f"%(round((total/ref_total - 1), 2))) + ", criterion=0.1)\n"

            if not flag_solver or flag_fail:
                output += err_lines + wsp_line + total_line + solver_line
                test_fail = True
    
    if test_fail:
        report.write("FAIL\n")
        report.write(output)
    
    return test_fail


def generate_report(path):
    with open(path+"/"+"report.txt", "w") as report:
        folders = os.listdir(path)
        #first test: ft_run and ft_reference should both exist
        flag_fail = first_test(folders, report)
        if flag_fail:
            return
        # first test passed
        # second test: *.stdout file and folder names are the same (as sets)
        second_result, present_folders = second_test(path, report)
        if second_result:
            return
        # second test passed
        # third test: in files check for abssence of lines containing "error" and presence of "Solver finished at" line
        # fourth test: a) find final total number of bricks in reference and run files, check that the relative run/ref difference < 0.1
        #              b) relative run/ref difference of (max per file) working set peak memory should be < 0.5
        # NOTE: in the reference output, the search for working set peak value is done the same way 
        # as the total number of bricks - the last such line is taken as a source.
        # In the task, however, the maximum working set peak value is to be found
        failed_34 = third_and_fourth_tests(path, present_folders, report)
        #third test passed
        #fourth test passed
        if not failed_34:
            report.write("OK\n")


def main():
    test_sets = os.listdir("./logs")
    for test_set in test_sets:
        tests = os.listdir("./logs/"+test_set)
        for test in tests:
            path = "./logs/"+test_set+"/"+test
            generate_report(path)

        for test in tests:
            path = "./logs/"+test_set+"/"+test
            with open(path+"/"+"report.txt", "r") as report:
                data = report.readlines()
                data[-1] = data[-1].removesuffix('\n')
                verdict = data[0].removesuffix('\n')
                print(verdict + ":", test_set+"/" + test + "/")
                if verdict == "FAIL":
                    print(*data[1:], sep='')

if __name__ == "__main__":
    main()
    