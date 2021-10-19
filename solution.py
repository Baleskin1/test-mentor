import os
import sys

def generate_report(path):
    with open(path+"/"+"report.txt", "w") as report:
        folders = os.listdir(path)
        flag_fail = False
        #first test: ft_run and ft_reference should both exist
        if "ft_reference" not in folders:
            report.write("FAIL\n")
            report.write("directory missing: ft_reference\n")
            flag_fail = True
            
        if "ft_run" not in folders:
            if not flag_fail:
                report.write("FAIL\n")
            report.write("directory missing: ft_run\n")
            flag_fail = True
        if flag_fail:
            return

        # first test passed
        # second test: *.stdout file and folder names are the same
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
        paths_to_stdouts = []
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
            report.write("FAIL\n" + extra_str + "\n" + missing_str)
            return

        #second test passed
        present_files = []
        for pf in present_folders:
            filepath = pf + "/" + pf + ".stdout"
            present_files.append(filepath)

        for pf in present_files:
            run_path = run_folder + "/" + pf
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
                
                if not flag_solver or flag_fail:
                    total = "FAIL\n"+err_lines+solver_line
                    report.write(total)
                    return
        #third test passed


        #fourth test passed
        report.write("OK\n")

test_sets = os.listdir("./logs")
print(test_sets)
for test_set in test_sets:
    tests = os.listdir("./logs/"+test_set)
    #print(tests)

    for test in tests:
        path = "./logs/"+test_set+"/"+test
        generate_report(path)

    for test in tests:
        path = "./logs/"+test_set+"/"+test
        with open(path+"/"+"report.txt", "r") as report:
            data = report.readlines()
            data[-1] = data[-1].removesuffix('\n')
            verdict = data[0].removesuffix('\n')
            print(verdict, ":", test_set+"/" + test + "/")
            if verdict == "FAIL":
                print(*data[1:], sep='')
    