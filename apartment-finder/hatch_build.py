"""Hatch custom build hook — builds the React frontend before packaging."""

import pathlib
import shutil
import subprocess

from hatchling.builders.hooks.plugin.interface import BuildHookInterface


class CustomBuildHook(BuildHookInterface):
    def initialize(self, version, build_data):
        # Only build the frontend when creating a distributable wheel, not
        # during editable/development installs (which have no static/ dir).
        if version == "editable":
            return

        root = pathlib.Path(self.root)
        frontend = root / "frontend"
        static = root / "src" / "dmv_aptfind" / "static"

        subprocess.run(["npm", "install"], cwd=frontend, check=True)
        subprocess.run(["npm", "run", "build"], cwd=frontend, check=True)

        if static.exists():
            shutil.rmtree(static)
        shutil.copytree(frontend / "dist", static)
