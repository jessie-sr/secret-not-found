#!/usr/bin/env python3
"""
AI Diagram Generator
Uses the repository structure data and Google's Gemini AI to generate Mermaid diagrams.
"""

import os
import json
import sys
import requests
from pathlib import Path
from dotenv import load_dotenv
import re
import argparse

# Load API key from environment variables
load_dotenv()

BASE_MERMAID_INSTRUCTIONS = """
You are an expert software architect who specialises in creating Mermaid diagrams to
visualise code repositories to help people new to a project quickly understand the code base.

MERMAID FLOWCHART GRAMMAR (reference)
	1.	Begin every diagram with a single line: flowchart <TD\|LR\|BT\|RL> – never follow it with a separate direction statement.
	2.	If you open a subgraph you must close it with end.
        If a subgraph needs its own direction, write direction <…> on its own line (newline or semicolon‑terminated).
	3.	One statement per line (or end it with “;”).
	4.	After every direction line, start a new line.
	5.	Node and subgraph IDs may contain only letters, digits, and underscores.
        If a label needs spaces, keep the ID underscored and put the display label in quotes: node_id["Label With Spaces"].
	6.	Give every subgraph a unique ID (no duplicates).
	7.	Close every subgraph with end.

OUTPUT REQUIREMENTS
• Return only a fenced ```mermaid code‑block – no prose, no JSON.
• The diagram must compile cleanly with mmdc -i - -o /dev/null.
• Use `flowchart TD` on the first line; never use `graph` + `direction`.
• Follow the grammar rules above exactly.
"""


class DiagramGenerator:
    def __init__(self, structure_file=None, structure_data=None):
        """Initialize with either a structure file path or direct structure data"""
        if structure_file:
            with open(structure_file, 'r', encoding='utf-8') as f:
                self.repo_structure = json.load(f)
        elif structure_data:
            self.repo_structure = structure_data
        else:
            raise ValueError("Either structure_file or structure_data must be provided")

        # Get API key from environment
        self.api_key = os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            print("⚠️  Warning: No Google Gemini API key found in environment variables.")
            print("    Please set GEMINI_API_KEY in your .env file.")
            self.api_key = input("Enter your Gemini API key (or press Enter to cancel): ").strip()
            if not self.api_key:
                sys.exit("❌ No API key provided. Exiting.")

    def generate_architecture_diagram(self):
        """Generate a Mermaid diagram describing the repo architecture"""
        # Prepare the prompt for AI
        prompt = self._create_architecture_prompt()

        # Call the Gemini API to generate the diagram
        mermaid_code = self._call_gemini_api(prompt)

        # Extract just the Mermaid code from the response
        mermaid_code = self._extract_mermaid_code(mermaid_code)

        return mermaid_code

    def generate_component_diagram(self):
        """Generate a component relationship diagram"""
        # Prepare the prompt for AI
        prompt = self._create_component_prompt()

        # Call the Gemini API to generate the diagram
        mermaid_code = self._call_gemini_api(prompt)

        # Extract just the Mermaid code from the response
        mermaid_code = self._extract_mermaid_code(mermaid_code)

        return mermaid_code

    def _create_architecture_prompt(self):
        """Create a prompt for the architecture diagram"""
        # Extract key information from the structure
        repo_name = self.repo_structure.get("repo_name", "Repository")
        language_breakdown = self.repo_structure.get("language_breakdown", {})
        components = self.repo_structure.get("components", [])

        # Get top-level directories
        top_dirs = [path for path in self.repo_structure["directories"].keys()
                    if path.count('/') <= 1 and path != '.']

        # Format the prompt
        prompt = f"""
Generate a Mermaid flowchart diagram that visualizes the architecture of the code repository described below.

Repository: {repo_name}

Language breakdown:
{json.dumps(language_breakdown, indent=2)}

Main components identified:
{json.dumps(components, indent=2)}

Top-level directories:
{json.dumps(top_dirs, indent=2)}

Create a Mermaid diagram that:
1. Shows the overall architecture of the repository
2. Highlights key components and their relationships
3. Includes the main directories and their purpose
4. Indicates the primary languages/frameworks used
5. Uses appropriate colors and styling for readability

The code should NOT contain any comments or explanations, just the diagram.
Return ONLY the Mermaid code without any additional text explanations.
"""
        return prompt

    def _create_component_prompt(self):
        """Create a prompt for the component relationship diagram"""
        components = self.repo_structure.get("components", [])
        dependencies = self.repo_structure.get("dependencies", [])

        # Get important files
        important_files = []
        for dir_info in self.repo_structure["directories"].values():
            for file_info in dir_info["files"]:
                if file_info["name"].lower() in ['package.json', 'requirements.txt', 'dockerfile',
                                                 'app.py', 'index.js', 'main.py', 'server.js']:
                    important_files.append(file_info["rel_path"])

        # Format the prompt
        prompt = f"""
Generate a Mermaid diagram showing the relationships between components in this codebase.

Components identified:
{json.dumps(components, indent=2)}

Dependencies between files:
{json.dumps(dependencies[:50], indent=2)}  /* Limited to first 50 for brevity */

Important files:
{json.dumps(important_files, indent=2)}

Create a Mermaid class diagram or flowchart that:
1. Shows the main components of the system
2. Illustrates dependencies and relationships between components
3. Uses appropriate notation for inheritance, composition, or dependency as needed
4. Includes any key interfaces or abstract classes

The diagram should be clear and focused on the most important architectural elements and ignore trivial ones that won't significantly help a new person understand the code base.
The code should NOT contain any comments or explanations, just the diagram.
Return ONLY the Mermaid code without any additional text explanations.
"""
        return prompt

    def _call_gemini_api(self, prompt):
        """Call the Google Gemini API to generate the diagram"""
        print("🧠 Generating diagram with Gemini AI...")

        try:
            # Gemini API endpoint
            api_url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={self.api_key}"

            headers = {
                "Content-Type": "application/json"
            }

            data = {
                "contents": [
                    {
                        "role": "user",
                        "parts": [
                            {
                                "text": f"{BASE_MERMAID_INSTRUCTIONS}\n\n{prompt}"
                            }
                        ]
                    }
                ],
                "generationConfig": {
                    "temperature": 0.7,
                    "maxOutputTokens": 8192
                }
            }

            # # DEBUG
            # print(f"PROMPT:", BASE_MERMAID_INSTRUCTIONS, prompt)

            response = requests.post(
                api_url,
                headers=headers,
                json=data
            )

            if response.status_code != 200:
                print(f"❌ API error: {response.status_code}")
                print(response.text)
                return None

            result = response.json()

            # Extract text from Gemini response
            if 'candidates' in result and result['candidates']:
                content = result['candidates'][0]['content']
                if 'parts' in content and content['parts']:
                    return content['parts'][0]['text']

            print("❌ Unexpected response format from Gemini API")
            return None

        except Exception as e:
            print(f"❌ Error calling Gemini API: {e}")
            return None

    def _extract_mermaid_code(self, text):
        """Extract Mermaid code from the API response"""
        if not text:
            return ""

        # Try to extract code between ```mermaid and ```
        mermaid_match = re.search(r'```mermaid(.*?)```', text, re.DOTALL)
        if mermaid_match:
            return mermaid_match.group(1).strip()

        # If no explicit mermaid block, look for a graph or flowchart definition
        graph_match = re.search(r'(graph\s+[A-Z]+.*|flowchart\s+[A-Z]+.*|classDiagram.*|sequenceDiagram.*)', text,
                                re.DOTALL)
        if graph_match:
            return graph_match.group(1).strip()

        # Otherwise return the whole text
        return text.strip()

    def save_diagram(self, mermaid_code, output_file="architecture_diagram.mmd"):
        """Save the Mermaid diagram to a file"""
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(mermaid_code)
        print(f"✅ Diagram saved to {output_file}")
        return output_file


def main():
    import argparse
    import subprocess
    import sys
    import os

    # ── CLI -----------------------------------------------------------------
    parser = argparse.ArgumentParser(
        description="Analyse a repository and generate Mermaid diagrams in one step")
    parser.add_argument(
        "--target", "-t", default=".",
        help="Path or Git URL of the repo to analyse (default: current directory)")
    parser.add_argument(
        "--json", "-j", default="repo_structure.json",
        help="Filename for the intermediate structure JSON (default: repo_structure.json)")
    parser.add_argument(
        "--skip-analysis", action="store_true",
        help="Skip running repo_analyzer.py and use an existing JSON file")
    args = parser.parse_args()
    # -----------------------------------------------------------------------

    # ── Run repo_analyzer unless user asked not to ─────────────────────────-
    if not args.skip_analysis:
        print("🔄 Running repository analysis …")
        analyzer_cmd = [sys.executable, "repo_analyzer.py", args.target]
        subprocess.run(analyzer_cmd, check=True)
    # -----------------------------------------------------------------------

    structure_file = args.json
    if not os.path.exists(structure_file):
        sys.exit(f"❌ Structure file {structure_file} not found. "
                 f"Run with --skip-analysis only if the file already exists.")

    # ── Diagram generation ─────────────────────────────────────────────────
    generator = DiagramGenerator(structure_file=structure_file)

    arch_diagram = generator.generate_architecture_diagram()
    arch_file = generator.save_diagram(arch_diagram, "architecture_diagram.mmd")

    comp_diagram = generator.generate_component_diagram()
    comp_file = generator.save_diagram(comp_diagram, "component_diagram.mmd")

    print("\n✨ Generated diagrams:")
    print(f"   • {arch_file}  (overall architecture)")
    print(f"   • {comp_file}  (component relationships)")
    print("💡 Open these .mmd files with any Mermaid renderer to view the diagrams.")


if __name__ == "__main__":
    main()