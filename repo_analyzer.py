#!/usr/bin/env python3
"""
Repository Analyzer
Scans a Git repository to extract architecture information.
"""

import os
import json
from pathlib import Path
from collections import defaultdict
import subprocess
import re
import argparse, tempfile, shutil, os, sys

# File types we're interested in analyzing more deeply
CODE_EXTENSIONS = {
    # Web
    '.js': 'JavaScript',
    '.jsx': 'React',
    '.ts': 'TypeScript',
    '.tsx': 'React TypeScript',
    '.html': 'HTML',
    '.css': 'CSS',
    '.scss': 'SCSS',
    # Backend
    '.py': 'Python',
    '.java': 'Java',
    '.rb': 'Ruby',
    '.go': 'Go',
    '.php': 'PHP',
    '.rs': 'Rust',
    '.c': 'C',
    '.cpp': 'C++',
    '.cs': 'C#',
    # Data
    '.json': 'JSON',
    '.yaml': 'YAML',
    '.yml': 'YAML',
    '.xml': 'XML',
    '.sql': 'SQL',
    # Config
    '.toml': 'TOML',
    '.ini': 'INI',
    '.env': 'Environment',
    '.md': 'Markdown',
    '.gitignore': 'Git Config',
    'Dockerfile': 'Docker',
    'docker-compose.yml': 'Docker Compose',
    'package.json': 'NPM Config',
    'requirements.txt': 'Python Dependencies',
}

# Directories to ignore
IGNORE_DIRS = {
    '.git', 'node_modules', '__pycache__', 'build', 'dist', 'venv',
    'env', '.venv', '.env', '.idea', '.vscode', 'target', 'bin'
}


class RepoAnalyzer:
    def __init__(self, repo_path="."):
        self.repo_path = Path(repo_path).absolute()
        self.structure = {
            "repo_name": self.repo_path.name,
            "directories": {},
            "files_by_type": defaultdict(int),
            "language_breakdown": {},
            "components": [],
            "dependencies": [],
        }

    def analyze(self):
        """Main analysis function"""
        print(f"🔍 Analyzing repository: {self.repo_path.name}")

        # Get basic file structure
        self._analyze_file_structure(self.repo_path)

        # Get git info
        self._analyze_git_info()

        # Identify main components
        self._identify_components()

        # Analyze relationships
        self._analyze_relationships()

        # Normalize data for output
        self._finalize_structure()

        return self.structure

    def _analyze_file_structure(self, path, rel_path=None):
        """Recursively analyze the file structure"""
        if rel_path is None:
            rel_path = Path('.')

        dir_structure = {
            "name": path.name,
            "type": "directory",
            "files": [],
            "subdirs": []
        }

        try:
            for item in path.iterdir():
                # Skip ignored directories
                if item.is_dir() and item.name in IGNORE_DIRS:
                    continue

                if item.is_file():
                    ext = item.suffix.lower()
                    filename = item.name

                    # Special case for files without extension
                    if not ext and filename in CODE_EXTENSIONS:
                        file_type = CODE_EXTENSIONS[filename]
                    else:
                        file_type = CODE_EXTENSIONS.get(ext, "Other")

                    file_info = {
                        "name": item.name,
                        "type": "file",
                        "file_type": file_type,
                        "size": item.stat().st_size,
                        "rel_path": str(rel_path / item.name)
                    }

                    # Count file types
                    self.structure["files_by_type"][file_type] += 1

                    # Special handling for important files
                    if item.name.lower() in ['readme.md', 'package.json', 'requirements.txt',
                                             'setup.py', 'dockerfile', 'docker-compose.yml',
                                             'makefile', '.env.example']:
                        try:
                            with open(item, 'r', encoding='utf-8', errors='ignore') as f:
                                file_info["content"] = f.read()
                        except:
                            pass

                    dir_structure["files"].append(file_info)

                elif item.is_dir():
                    subdir_info = self._analyze_file_structure(item, rel_path / item.name)
                    dir_structure["subdirs"].append(subdir_info)

        except PermissionError:
            pass

        # Store in structure
        dir_key = str(rel_path)
        self.structure["directories"][dir_key] = dir_structure

        return dir_structure

    def _analyze_git_info(self):
        """Extract Git repository information"""
        try:
            # Get primary remote URL
            remote_cmd = ["git", "-C", str(self.repo_path), "remote", "-v"]
            remote_output = subprocess.check_output(remote_cmd, text=True, stderr=subprocess.DEVNULL)

            # Extract first remote URL
            remote_match = re.search(r'origin\s+([^ ]+)', remote_output)
            if remote_match:
                self.structure["remote_url"] = remote_match.group(1)

            # Get main branch
            branch_cmd = ["git", "-C", str(self.repo_path), "branch", "--show-current"]
            self.structure["main_branch"] = subprocess.check_output(branch_cmd, text=True).strip()

            # Get commit count
            commit_cmd = ["git", "-C", str(self.repo_path), "rev-list", "--count", "HEAD"]
            self.structure["commit_count"] = int(subprocess.check_output(commit_cmd, text=True).strip())

            # Get contributors
            contrib_cmd = ["git", "-C", str(self.repo_path), "shortlog", "-s", "-n", "HEAD"]
            contrib_output = subprocess.check_output(contrib_cmd, text=True, stderr=subprocess.DEVNULL)
            self.structure["contributors"] = [line.split('\t')[1].strip()
                                              for line in contrib_output.splitlines()]

        except (subprocess.SubprocessError, ValueError):
            # Git commands failed, possibly not a git repo
            self.structure["git_info_available"] = False

    def _identify_components(self):
        """Identify major components in the codebase"""
        components = []

        # Look for common architectural patterns
        patterns = {
            "frontend": ["src/components", "src/pages", "public", "web", "frontend", "ui"],
            "backend": ["api", "server", "controllers", "routes", "app", "backend"],
            "database": ["models", "schemas", "migrations", "db"],
            "config": ["config", "settings"],
            "utils": ["utils", "helpers", "lib", "common"],
            "tests": ["tests", "test", "spec", "__tests__"],
            "docs": ["docs", "documentation"],
            "scripts": ["scripts", "tools", "bin"],
        }

        # Check each pattern against directories
        for component_type, dir_patterns in patterns.items():
            for dir_pattern in dir_patterns:
                for dir_path in self.structure["directories"]:
                    if dir_pattern in dir_path.lower():
                        components.append({
                            "type": component_type,
                            "path": dir_path,
                            "name": Path(dir_path).name
                        })

        # Look for framework-specific patterns
        frameworks = {
            "React": ["react", "jsx", "tsx", "components"],
            "Angular": ["angular", "component.ts", "module.ts"],
            "Vue": ["vue", "components"],
            "Django": ["views.py", "urls.py", "models.py"],
            "Flask": ["app.py", "routes.py"],
            "Express": ["express", "app.js", "routes"],
            "Spring": ["java", "controller", "service"],
            "Laravel": ["php", "controller", "blade.php"],
        }

        # Check each directory for framework indicators
        for framework, indicators in frameworks.items():
            for dir_path, dir_info in self.structure["directories"].items():
                # Check if any files match framework indicators
                for file_info in dir_info["files"]:
                    if any(indicator in file_info["rel_path"].lower() for indicator in indicators):
                        components.append({
                            "type": "framework",
                            "framework": framework,
                            "path": dir_path,
                            "name": f"{framework} ({Path(dir_path).name})"
                        })
                        break

        self.structure["components"] = components

    def _analyze_relationships(self):
        """Analyze relationships between components"""
        dependencies = []

        # For Python files, look for imports
        python_import_pattern = re.compile(r'(?:from|import)\s+([\w.]+)')

        # For JavaScript/TypeScript files, look for imports
        js_import_pattern = re.compile(r'(?:import|require).*[\'"](.+?)[\'"]')

        # Analyze each file for dependencies
        for dir_path, dir_info in self.structure["directories"].items():
            for file_info in dir_info["files"]:
                # Skip large files
                if file_info.get("size", 0) > 500000:  # Skip files > 500KB
                    continue

                file_path = self.repo_path / file_info["rel_path"]
                try:
                    if not file_path.exists():
                        continue

                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read()

                        # Python imports
                        if file_info["file_type"] == "Python":
                            for match in python_import_pattern.finditer(content):
                                module = match.group(1)
                                dependencies.append({
                                    "source": file_info["rel_path"],
                                    "target": module,
                                    "type": "import"
                                })

                        # JavaScript/TypeScript imports
                        elif file_info["file_type"] in ["JavaScript", "TypeScript", "React", "React TypeScript"]:
                            for match in js_import_pattern.finditer(content):
                                module = match.group(1)
                                dependencies.append({
                                    "source": file_info["rel_path"],
                                    "target": module,
                                    "type": "import"
                                })

                except (UnicodeDecodeError, PermissionError):
                    # Skip binary or inaccessible files
                    pass

        self.structure["dependencies"] = dependencies

    def _finalize_structure(self):
        """Finalize the structure for output"""
        # Calculate language breakdown percentages
        total_files = sum(self.structure["files_by_type"].values())
        if total_files > 0:
            self.structure["language_breakdown"] = {
                lang: round(count / total_files * 100, 2)
                for lang, count in self.structure["files_by_type"].items()
                if count > 0
            }

        # Remove verbose file content for a cleaner output
        for dir_info in self.structure["directories"].values():
            for file_info in dir_info["files"]:
                if "content" in file_info and len(file_info["content"]) > 1000:
                    file_info["content"] = file_info["content"][:1000] + "... [truncated]"

    def save_to_file(self, output_path="repo_structure.json"):
        """Save the analyzed structure to a JSON file"""
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(self.structure, f, indent=2)
        print(f"✅ Repository structure saved to {output_path}")
        return output_path


def main():
    p = argparse.ArgumentParser(
        description="Analyse a local folder *or* a remote Git repo")
    p.add_argument("target",
                   nargs="?",
                   default=".",
                   help="Path or Git URL of the repo to analyse "
                        "(default: current directory)")
    args = p.parse_args()

    target = args.target
    temp_dir = None

    # ── Resolve the repo path ────────────────────────────────────────────
    if target.startswith(("http://", "https://")) or target.endswith(".git"):
        import tempfile
        temp_dir = tempfile.mkdtemp(prefix="s‑n‑f_")
        print(f"📥  Cloning {target} …")
        subprocess.run(["git", "clone", "--depth", "1", target, temp_dir],
                       check=True)
        repo_root = temp_dir
    else:
        repo_root = os.path.abspath(target)

    if not os.path.isdir(repo_root):
        sys.exit(f"❌  {repo_root} is not a directory or git clone failed.")
    # ─────────────────────────────────────────────────────────────────────

    # PATCH #1 – pass the resolved path to the analyser
    analyzer = RepoAnalyzer(repo_root)

    structure = analyzer.analyze()
    output_file = analyzer.save_to_file()
    print(f"Analysis complete! Structure data saved to {output_file}")

    # PATCH #2 – delete the temporary clone, if we made one
    if temp_dir:
        shutil.rmtree(temp_dir, ignore_errors=True)

    return structure


if __name__ == "__main__":
    main()