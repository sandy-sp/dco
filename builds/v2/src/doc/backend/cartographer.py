import os
import ast
import re

class Cartographer:
    def __init__(self, root_path: str):
        self.root_path = root_path
        self.ignore_patterns = {
            'node_modules', '__pycache__', '.git', '.venv', 'venv', 
            '.brain', 'dist', 'build', '.pytest_cache', '.vscode', '.idea'
        }

    def generate_map(self) -> str:
        """Generates a tree-like string map of the codebase."""
        tree_lines = []
        
        for root, dirs, files in os.walk(self.root_path):
            # Prune ignored directories
            dirs[:] = [d for d in dirs if d not in self.ignore_patterns]
            
            rel_path = os.path.relpath(root, self.root_path)
            if rel_path == ".":
                rel_path = ""
            
            for file in files:
                if any(file.endswith(ext) for ext in ['.py', '.js', '.ts', '.jsx', '.tsx']):
                    full_path = os.path.join(root, file)
                    rel_file_path = os.path.join(rel_path, file)
                    
                    # Add file node
                    tree_lines.append(f"{rel_file_path}")
                    
                    # Add symbols
                    symbols = self._parse_file(full_path, file)
                    for sym in symbols:
                        tree_lines.append(f"  {sym}")
                        
        return "\n".join(tree_lines)

    def save_map(self):
        """Generates and saves the map to .brain/repo_map.txt"""
        content = self.generate_map()
        map_path = os.path.join(self.root_path, ".brain", "repo_map.txt")
        os.makedirs(os.path.dirname(map_path), exist_ok=True)
        with open(map_path, "w", encoding="utf-8") as f:
            f.write(content)
        return map_path

    def _parse_file(self, full_path, filename) -> list[str]:
        if filename.endswith('.py'):
            return self._parse_python(full_path)
        elif filename.endswith(('.js', '.ts', '.jsx', '.tsx')):
            return self._parse_javascript(full_path)
        return []

    def _parse_python(self, file_path) -> list[str]:
        symbols = []
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                tree = ast.parse(f.read())
            
            for node in tree.body:
                if isinstance(node, ast.ClassDef):
                    symbols.append(f"class {node.name}")
                    for item in node.body:
                        if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                            prefix = "async " if isinstance(item, ast.AsyncFunctionDef) else ""
                            # Simple signature extraction could be enhanced
                            args = [a.arg for a in item.args.args]
                            symbols.append(f"    {prefix}def {item.name}({', '.join(args)})")
                elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    prefix = "async " if isinstance(node, ast.AsyncFunctionDef) else ""
                    args = [a.arg for a in node.args.args]
                    symbols.append(f"{prefix}def {node.name}({', '.join(args)})")
        except Exception as e:
            # symbols.append(f"  (parse error: {e})") # Optional: detailed error
            symbols.append("  (parse error)")
        return symbols

    def _parse_javascript(self, file_path) -> list[str]:
        symbols = []
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
            
            # Basic Regex for JS/TS structure (Not perfect, but lightweight)
            # Find exported functions, classes, consts
            
            # class MyClass
            classes = re.findall(r'class\s+(\w+)', content)
            for c in classes:
                symbols.append(f"class {c}")
                
            # function myFunction
            funcs = re.findall(r'function\s+(\w+)', content)
            for f in funcs:
                symbols.append(f"function {f}")
                
            # const myVar = ...
            consts = re.findall(r'const\s+(\w+)\s*=', content)
            for c in consts:
                symbols.append(f"const {c}")

        except:
            pass
        return symbols
