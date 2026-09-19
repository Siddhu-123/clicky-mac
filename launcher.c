/*
 * Clicky macOS Native App Launcher
 *
 * Compiles to Mach-O arm64 binary inside Clicky.app/Contents/MacOS/Clicky.
 * Initializes Python in-process so macOS TCC (Accessibility, Screen Recording,
 * Microphone) identifies the process as 'com.clicky.mac' (Clicky) rather
 * than the generic Python 3.14 interpreter.
 */

#define PY_SSIZE_T_CLEAN
#include <Python.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <mach-o/dyld.h>
#include <sys/stat.h>
#include <libgen.h>
#include <limits.h>

static void redirect_logs_if_needed(const char *home_dir) {
    // If not running in an interactive terminal, redirect stdout/stderr to log file
    if (!isatty(fileno(stdout))) {
        char log_dir[PATH_MAX];
        char log_file[PATH_MAX];
        snprintf(log_dir, sizeof(log_dir), "%s/Library/Logs/Clicky", home_dir);
        mkdir(log_dir, 0755);
        snprintf(log_file, sizeof(log_file), "%s/clicky.log", log_dir);
        FILE *f = freopen(log_file, "a", stdout);
        if (f) {
            dup2(fileno(stdout), fileno(stderr));
            setlinebuf(stdout);
            setlinebuf(stderr);
        }
    }
}

int main(int argc, char *argv[]) {
    char exe_path[PATH_MAX];
    uint32_t size = sizeof(exe_path);
    if (_NSGetExecutablePath(exe_path, &size) != 0) {
        fprintf(stderr, "[Clicky] Error: Unable to determine executable path.\n");
        return 1;
    }

    // Resolve real path in case of symlinks
    char real_exe[PATH_MAX];
    if (!realpath(exe_path, real_exe)) {
        strncpy(real_exe, exe_path, sizeof(real_exe) - 1);
        real_exe[sizeof(real_exe) - 1] = '\0';
    }

    // Determine Contents/ directory
    // real_exe: .../Clicky.app/Contents/MacOS/Clicky
    char exe_copy[PATH_MAX];
    strncpy(exe_copy, real_exe, sizeof(exe_copy));
    char *macos_dir = dirname(exe_copy);
    char contents_dir[PATH_MAX];
    strncpy(contents_dir, macos_dir, sizeof(contents_dir));
    char *p = dirname(contents_dir); // Contents

    char resources_dir[PATH_MAX];
    snprintf(resources_dir, sizeof(resources_dir), "%s/Resources", p);

    const char *home = getenv("HOME");
    if (home) {
        redirect_logs_if_needed(home);
    }

    printf("[Clicky] Launching native macOS companion...\n");
    printf("[Clicky] Binary: %s\n", real_exe);

    // Locate project root
    char project_dir[PATH_MAX] = {0};

    // 1. Check CLICKY_PROJECT_DIR env var
    const char *env_proj = getenv("CLICKY_PROJECT_DIR");
    if (env_proj && access(env_proj, R_OK) == 0) {
        strncpy(project_dir, env_proj, sizeof(project_dir) - 1);
    }

    // 2. Check Resources/project_path.txt
    if (project_dir[0] == '\0') {
        char path_txt[PATH_MAX];
        snprintf(path_txt, sizeof(path_txt), "%s/project_path.txt", resources_dir);
        FILE *f = fopen(path_txt, "r");
        if (f) {
            if (fgets(project_dir, sizeof(project_dir), f)) {
                // Trim trailing newline
                size_t len = strlen(project_dir);
                while (len > 0 && (project_dir[len - 1] == '\n' || project_dir[len - 1] == '\r')) {
                    project_dir[--len] = '\0';
                }
            }
            fclose(f);
        }
    }

    // 3. Fallback: Check relative to app bundle in dist/
    // .../clicky-mac/dist/Clicky.app/Contents/MacOS/Clicky -> ../../../../
    if (project_dir[0] == '\0' || access(project_dir, R_OK) != 0) {
        char candidate[PATH_MAX];
        snprintf(candidate, sizeof(candidate), "%s/../../../../main.py", macos_dir);
        char real_main[PATH_MAX];
        if (realpath(candidate, real_main)) {
            char *d = dirname(real_main);
            strncpy(project_dir, d, sizeof(project_dir) - 1);
        }
    }

    if (project_dir[0] == '\0' || access(project_dir, R_OK) != 0) {
        fprintf(stderr, "[Clicky] Error: Unable to locate project directory.\n");
        return 1;
    }

    printf("[Clicky] Project root: %s\n", project_dir);

    // Locate Python virtualenv
    char venv_dir[PATH_MAX];
    snprintf(venv_dir, sizeof(venv_dir), "%s/.venv", project_dir);
    if (access(venv_dir, R_OK) != 0) {
        fprintf(stderr, "[Clicky] Error: .venv not found at %s\n", venv_dir);
        return 1;
    }

    // Set environment variables for Python runtime
    setenv("VIRTUAL_ENV", venv_dir, 1);
    setenv("CLICKY_IS_APP_BUNDLE", "1", 1);
    setenv("CLICKY_PROJECT_DIR", project_dir, 1);

    // Initialize Python with PEP 587 PyConfig
    PyStatus status;
    PyConfig config;
    PyConfig_InitPythonConfig(&config);
    config.parse_argv = 0;

    // Pass original CLI args directly to sys.argv
    status = PyConfig_SetBytesArgv(&config, argc, argv);
    if (PyStatus_Exception(status)) {
        PyConfig_Clear(&config);
        Py_ExitStatusException(status);
    }

    // Initialize Python runtime
    status = Py_InitializeFromConfig(&config);
    PyConfig_Clear(&config);
    if (PyStatus_Exception(status)) {
        Py_ExitStatusException(status);
    }

    // Execute bootstrap Python code
    char bootstrap_code[4096];
    snprintf(bootstrap_code, sizeof(bootstrap_code),
        "import sys, os, glob\n"
        "proj = '%s'\n"
        "venv = '%s'\n"
        "site_packages = glob.glob(os.path.join(venv, 'lib', 'python3.*', 'site-packages'))\n"
        "for sp in site_packages:\n"
        "    if sp not in sys.path:\n"
        "        sys.path.insert(0, sp)\n"
        "if proj not in sys.path:\n"
        "    sys.path.insert(0, proj)\n"
        "os.chdir(proj)\n"
        "import main\n"
        "main.main()\n",
        project_dir, venv_dir
    );

    int exit_code = PyRun_SimpleString(bootstrap_code);
    Py_Finalize();

    return exit_code;
}
