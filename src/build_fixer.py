import logging
import subprocess
import os
from log import LogFormatter
from lief import ELF

def newer_edition_patch(crate_path):
    cargo_file_path = crate_path+'/Cargo.toml'
    if os.path.exists(cargo_file_path):
        new_cargo_file_lines = []
        with open(cargo_file_path, 'r') as cargo_file:
            cargo_file_lines = cargo_file.readlines()
            for line in cargo_file_lines:
                line = line.strip()
                if '[package]' in line:
                    new_cargo_file_lines.append('[package]\n')
                    new_cargo_file_lines.append('edition = "2021"\n')
                elif not line.startswith('edition ') and not line.startswith('edition='):
                    new_cargo_file_lines.append(line+'\n')
            cargo_file.close()
        with open(cargo_file_path, 'w') as cargo_file:
            cargo_file.writelines(new_cargo_file_lines)
            cargo_file.close()
    
def std_redefinition_patch(crate_path):
    lib_file_path = crate_path+'/src/lib.rs'
    if os.path.exists(lib_file_path):
        new_lib_file_lines = []
        with open(lib_file_path, 'r') as lib_file:
            lib_file_lines = lib_file.readlines()
            for line in lib_file_lines:
                line = line
                if 'no_std' not in line and 'as std;' not in line:
                    new_lib_file_lines.append(line+'\n')
            lib_file.close()
        with open(lib_file_path, 'w') as lib_file:
            lib_file.writelines(new_lib_file_lines)
            lib_file.close()

def add_workspace_patch(crate_path):
    cargo_file_path = crate_path+'/Cargo.toml'
    if os.path.exists(cargo_file_path):
        cargo_file_lines = []
        with open(cargo_file_path, 'r') as cargo_file:
            cargo_file_lines = cargo_file.readlines()
            cargo_file_lines.append('[workspace]\n')
            cargo_file.close()
        with open(cargo_file_path, 'w') as cargo_file:
            cargo_file.writelines(cargo_file_lines)
            cargo_file.close()

class BuildFixer:

    PREFIX = '[bright blue]BuildFixer -> '

    TRACE_TO_PATCH = {
        'maybe a missing crate `core`?': ['EDITION 2021', newer_edition_patch],
        'the name `std` is defined multiple times': ['STD REDEFINITION', std_redefinition_patch],
        'language item required, but not found: `eh_personality`': ['STD REDEFINITION', std_redefinition_patch],
        'current package believes it\'s in a workspace when it\'s not': ['ADD WORKSPACE', add_workspace_patch]
    }

    def __init__(self, crate_path, build_err, elf_arch):
        self.success = False
        self.applied_patches = {}
        self.crate_path = crate_path
        self.elf_arch = elf_arch
        self.compute_error(build_err, 0)

    def compute_error(self, build_err, iter_index):
        found_patch = False
        for err_line in build_err:
            err_line = err_line.decode()
            for trace in self.TRACE_TO_PATCH:
                if trace in err_line:
                    patch_name, patch_func = self.TRACE_TO_PATCH[trace]
                    if patch_name not in self.applied_patches:
                        found_patch = True
                        self.applied_patches[patch_name] = iter_index
                        logging.info(f'{self.PREFIX}[cyan]]Applying patch : [bright white] {patch_name}')
                        patch_func(self.crate_path)
                    else:
                        patch_iter_index = self.applied_patches[patch_name]
                        if iter_index != patch_iter_index:
                            logging.error(f'{self.PREFIX}[red]Patch recursion detected...')
                            return
                        if not found_patch:
                            logging.error(f'{self.PREFIX}[red]No patch was found...')
            return
        logging.info(f'{self.PREFIX}[cyan]Building crate again...')
        build_status, new_build_err = self.build_crate()
        if build_status:
            self.success = True
            logging.success(f'{self.PREFIX}[green]Success !')
        else:
            logging.info(f'{self.PREFIX}[cyan]Trying to patch new error trace...')
            self.compute_error(new_build_err, iter_index+1)

    def build_crate(self):
        build_params = ['cargo','build','--release']
        if self.elf_arch == ELF.ARCH.i386:
            build_params.append('--target=i686-unknown-linux-gnu')
        try:
            build_output = subprocess.run(build_params, cwd=self.crate_path, capture_output=True)
        except Exception as e:
            logging.error(f'{self.PREFIX}[red]]Build failed...')
            logging.debug(e)
            return [False, None]
        build_err = build_output.stderr
        if build_err is not None:
            build_err = build_err.split(b'\n')
            is_error = False
            for err_line in build_err:
                if err_line.decode().strip().startswith('error: '):
                    is_error = True
            if is_error:
                logging.error(f'{self.PREFIX}[red]Build failed...')
                logging.debug(f'{self.PREFIX}[red]Here is the trace :')
                if logging.getLogger(__name__).getEffectiveLevel() <= logging.DEBUG:
                    for err_line in build_err:
                        print('[bright blue]'+err_line.decode())
                return [False, build_err]
        return [True, None]
