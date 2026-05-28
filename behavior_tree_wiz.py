import tkinter as tk
from tkinter import filedialog, scrolledtext, messagebox
import xml.etree.ElementTree as ET
import json
import os
import re
import abc
from typing import List, Dict, Optional, Any

# ==========================================
# Domain Logic: Behavior Tree Nodes & Parsing
# ==========================================

class BTNode:
    def __init__(self, node_id: str, label: str, node_type: str, geometry_x: float = 0, geometry_y: float = 0, has_memory: bool = False):
        self.id = node_id
        self.label = label
        self.node_type = node_type  # 'Selector', 'Sequence', 'Condition', 'Action', 'Root', 'RandomSelector', 'WeightedSelector'
        self.children: List['BTNode'] = []
        self.child_weights: List[float] = [] # Weights for children if parent is WeightedSelector
        self.geometry_x = geometry_x
        self.geometry_y = geometry_y
        self.has_memory = has_memory
        # Decorator parameters
        self.max_retries: Optional[int] = None
        self.timer_duration: Optional[int] = None
        self.repeat_count: Optional[int] = None
        self.condition_reference: Optional[str] = None
        self.decorator_raw_param: Optional[str] = None

    def add_child(self, child: 'BTNode', weight: float = 0.0):
        self.children.append(child)
        self.child_weights.append(weight)

    def sort_children(self):
        # Sort children and their weights by X coordinate
        if self.children:
            combined = list(zip(self.children, self.child_weights))
            combined.sort(key=lambda x: x[0].geometry_x)
            self.children, self.child_weights = zip(*combined)
            self.children = list(self.children)
            self.child_weights = list(self.child_weights)
            
        for child in self.children:
            child.sort_children()

    def __repr__(self):
        return f"<{self.node_type}: {self.label}>"

# --- Strategy Pattern for Node Generation ---

class GenerationStrategy(abc.ABC):
    @abc.abstractmethod
    def generate(self, node: BTNode, generator_ref: 'SimbaGenerator', indent_level: int) -> str:
        pass

class CompositeStrategy(GenerationStrategy):
    def __init__(self, method_name: str):
        self.method_name = method_name # e.g., 'CreateSelector' or 'CreateSequence'

    def generate(self, node: BTNode, generator_ref: 'SimbaGenerator', indent_level: int) -> str:
        indent = "  " * indent_level
        # Extract display name from label (maintaining nomenclature but escaping single quotes for Simba)
        display_name = node.label.replace("'", "''")
        
        simba_code = f"{indent}Self.Tree.{self.method_name}('{display_name}', [\n"
        
        child_codes = []
        for child in node.children:
            child_codes.append(generator_ref.generate_node(child, indent_level + 1))
        
        simba_code += ",\n\n".join(child_codes)
        
        closing_args = ""
        if node.has_memory and self.method_name in ['CreateSelector', 'CreateSequence']:
            closing_args = ", True"
            
        simba_code += f"\n{indent}]{closing_args})"
        return simba_code

class LeafStrategy(GenerationStrategy):
    def __init__(self, method_name: str):
        self.method_name = method_name # e.g., 'CreateAction' or 'CreateCondition'

    def generate(self, node: BTNode, generator_ref: 'SimbaGenerator', indent_level: int) -> str:
        indent = "  " * indent_level
        display_name = node.label.replace("'", "''")
        
        # Check for parameters: Name(Args)
        clean_label = node.label.strip().rstrip(';')
        # Regex to capture Name and Args
        match = re.match(r'^([a-zA-Z0-9_]+)\((.*)\)$', clean_label)
        
        if match:
            func_name = match.group(1)
            args = match.group(2)
            
            # Register base method with params (ensures it appears in definitions)
            generator_ref.register_method(func_name, node.node_type, has_params=True)
            
            # Get or create a reusable wrapper for these specific arguments
            wrapper_name = generator_ref.get_wrapper_name(func_name, args, node.node_type)
            
            return f"{indent}Self.Tree.{self.method_name}('{display_name}', @Self.{wrapper_name})"
        else:
            # Basic sanitization
            func_name = node.label.split('(')[0]
            func_name = "".join(x for x in func_name if x.isalnum() or x == '_')
            
            generator_ref.register_method(func_name, node.node_type, has_params=False)
            
            return f"{indent}Self.Tree.{self.method_name}('{display_name}', @Self.{func_name})"

class RootStrategy(GenerationStrategy):
    def generate(self, node: BTNode, generator_ref: 'SimbaGenerator', indent_level: int) -> str:
        # Root usually just delegates to its first child, or is a wrapper
        if not node.children:
            return "// Empty Root"
        
        # If multiple children, treat as a Selector (common for Root to branch into options)
        if len(node.children) > 1:
            return CompositeStrategy('CreateSelector').generate(node, generator_ref, indent_level)
        
        # We assume the Root Node in XML connects to the actual top-level tree node
        return generator_ref.generate_node(node.children[0], indent_level)

class DecoratorStrategy(GenerationStrategy):
    def __init__(self, method_name: str):
        self.method_name = method_name # e.g., 'CreateForceSuccess' or 'CreateForceFailure'

    def _parse_decorator_parameters(self, node: BTNode):
        """Parse decorator parameters from node.label in format: DECOR_TYPE_Name(Params)"""
        match = re.match(r'^[^(]*\((.*)\)$', node.label)
        if match:
            params_str = match.group(1)
            if self.method_name == 'CreateRetry':
                try:
                    node.max_retries = int(params_str.strip())
                except ValueError:
                    node.decorator_raw_param = params_str.strip()
            elif self.method_name in ['CreateCooldown', 'CreateTimeout']:
                try:
                    node.timer_duration = int(params_str.strip())
                except ValueError:
                    node.decorator_raw_param = params_str.strip()
            elif self.method_name == 'CreateRepeater':
                try:
                    node.repeat_count = int(params_str.strip())
                except ValueError:
                    node.decorator_raw_param = params_str.strip()
            elif self.method_name == 'CreateConditional':
                node.condition_reference = params_str.strip()

    def generate(self, node: BTNode, generator_ref: 'SimbaGenerator', indent_level: int) -> str:
        indent = "  " * indent_level
        paren_pos = node.label.find('(')
        if paren_pos >= 0:
            display_name = node.label[:paren_pos].strip().replace("'", "''")
        else:
            display_name = node.label.replace("'", "''")
        
        self._parse_decorator_parameters(node)
        
        if not node.children:
            return f"{indent}// Decorator '{display_name}' has no child"
        
        child_code = generator_ref.generate_node(node.children[0], indent_level + 1)
        
        param_str = ""
        if self.method_name == 'CreateRetry':
            if node.max_retries is not None:
                param_str = f", {node.max_retries}"
            elif node.decorator_raw_param is not None:
                param_str = f", {node.decorator_raw_param}"
        elif self.method_name in ['CreateCooldown', 'CreateTimeout']:
            if node.timer_duration is not None:
                param_str = f", {node.timer_duration}"
            elif node.decorator_raw_param is not None:
                param_str = f", {node.decorator_raw_param}"
        elif self.method_name == 'CreateRepeater':
            if node.repeat_count is not None:
                param_str = f", {node.repeat_count}"
            elif node.decorator_raw_param is not None:
                param_str = f", {node.decorator_raw_param}"
        elif self.method_name == 'CreateConditional' and node.condition_reference is not None:
            cond_ref = node.condition_reference
            if cond_ref.startswith('@Self.'):
                param_str = f", {cond_ref}"
            elif cond_ref.startswith('@'):
                param_str = f", {cond_ref}"
            else:
                param_str = f", @{cond_ref}"

        closing_args = ""
        if node.has_memory and self.method_name in ['CreateForceSuccess', 'CreateForceFailure']:
            closing_args = ", True"
            
        simba_code = f"{indent}Self.Tree.{self.method_name}('{display_name}', \n{child_code}{param_str}{closing_args}\n{indent})"
        return simba_code

class WeightedSelectorStrategy(GenerationStrategy):
    def generate(self, node: BTNode, generator_ref: 'SimbaGenerator', indent_level: int) -> str:
        indent = "  " * indent_level
        display_name = node.label.replace("'", "''")
        
        simba_code = f"{indent}Self.Tree.CreateWeightedSelector('{display_name}', [\n"
        
        child_codes = []
        for child in node.children:
            child_codes.append(generator_ref.generate_node(child, indent_level + 1))
        
        simba_code += ",\n\n".join(child_codes)
        
        weights_str = ", ".join(f"{w:.2f}" for w in node.child_weights)
        simba_code += f"\n{indent}], [{weights_str}])"
        return simba_code

class NodeFactory:
    _strategies = {
        'Selector': CompositeStrategy('CreateSelector'),
        'ParallelSelector': CompositeStrategy('CreateParallelSelector'),
        'RandomSelector': CompositeStrategy('CreateRandomSelector'),
        'WeightedSelector': WeightedSelectorStrategy(),
        'Sequence': CompositeStrategy('CreateSequence'),
        'ParallelSequence': CompositeStrategy('CreateParallelSequence'),
        'Action': LeafStrategy('CreateAction'),
        'Condition': LeafStrategy('CreateCondition'),
        'Root': RootStrategy(),
        # Decorator strategies
        'ForceSuccess': DecoratorStrategy('CreateForceSuccess'),
        'ForceFailure': DecoratorStrategy('CreateForceFailure'),
        'Retry': DecoratorStrategy('CreateRetry'),
        'Cooldown': DecoratorStrategy('CreateCooldown'),
        'Timeout': DecoratorStrategy('CreateTimeout'),
        'Repeater': DecoratorStrategy('CreateRepeater'),
        'Conditional': DecoratorStrategy('CreateConditional'),
        'Link': DecoratorStrategy('CreateLink')
    }

    @classmethod
    def get_strategy(cls, node_type: str) -> GenerationStrategy:
        return cls._strategies.get(node_type, LeafStrategy('CreateAction')) # Default to Action

# --- Parser & Generator ---

class GraphParser:
    def __init__(self):
        self.cells = {}
        self.edges = [] # List of (source, target, weight_text)
        self.groups = {} # parent_id -> list of child_ids

    def parse(self, xml_path: str) -> Optional[BTNode]:
        tree = ET.parse(xml_path)
        root_element = tree.getroot()
        
        # 1. First Pass: Collect all cells (nodes, edges, and potential labels)
        raw_edges = [] # List of (source, target, label, cell_id)
        edge_labels = {} # parent_id (edge_id) -> label_text

        for cell in root_element.findall(".//mxCell"):
            cell_id = cell.get('id')
            parent_id = cell.get('parent')
            val = cell.get('value', '')
            
            if parent_id:
                if parent_id not in self.groups:
                    self.groups[parent_id] = []
                self.groups[parent_id].append(cell)

            if cell.get('edge') == '1':
                source = cell.get('source')
                target = cell.get('target')
                if source and target:
                    if val and "<" in val:
                        val = re.sub(r'<[^>]+>', '', val)
                    raw_edges.append((source, target, val, cell_id))
            elif cell.get('vertex') == '1' and 'edgeLabel' not in cell.get('style', ''):
                self.cells[cell_id] = cell
            elif parent_id and val:
                # Potential label attached to an edge
                if "<" in val:
                    val = re.sub(r'<[^>]+>', '', val)
                edge_labels[parent_id] = val

        # 2. Finalize Edges: Combine edge labels from child cells if primary label is missing
        for source, target, label, edge_id in raw_edges:
            final_label = label if label else edge_labels.get(edge_id, '')
            self.edges.append((source, target, final_label))

        # 2. Identify Logical Nodes
        logical_nodes: Dict[str, BTNode] = {} # cell_id -> BTNode

        def get_node_info(cell_id: str) -> tuple[str, str, float, float, bool]:
            main_cell = self.cells.get(cell_id)
            if not main_cell: return ("Unknown", "Action", 0, 0, False)

            geo = main_cell.find('mxGeometry')
            x = float(geo.get('x', 0)) if geo is not None else 0
            y = float(geo.get('y', 0)) if geo is not None else 0
            
            curr_parent = main_cell.get('parent')
            while curr_parent and curr_parent != '1' and curr_parent != '0':
                parent_cell = self.cells.get(curr_parent)
                if parent_cell:
                    p_geo = parent_cell.find('mxGeometry')
                    if p_geo is not None:
                        x += float(p_geo.get('x', 0))
                        y += float(p_geo.get('y', 0))
                    curr_parent = parent_cell.get('parent')
                else:
                    break

            raw_value = main_cell.get('value', '')
            style = main_cell.get('style', '')

            has_memory = "rounded=1" in style

            symbol = raw_value
            if symbol and "<" in symbol:
                symbol = re.sub(r'<[^>]+>', '', symbol)
            symbol = symbol.strip()

            parent_id = main_cell.get('parent')
            is_in_group = parent_id is not None and parent_id not in ('0', '1')

            label = symbol
            if is_in_group:
                curr_search_cell = main_cell
                label_found = False
                while curr_search_cell and not label_found:
                    search_parent = curr_search_cell.get('parent')
                    if not search_parent or search_parent in ('1', '0'):
                        break

                    if search_parent in self.groups:
                        for sib in self.groups[search_parent]:
                            sib_val = sib.get('value', '')
                            if sib_val and "<" in sib_val:
                                sib_val = re.sub(r'<[^>]+>', '', sib_val)
                            if (sib_val and
                                sib.get('id') != curr_search_cell.get('id') and
                                'text' in sib.get('style', '')):
                                label = sib_val
                                label_found = True
                                break

                    if not label_found:
                        curr_search_cell = self.cells.get(search_parent)

            has_arrow_child = False
            direct_parent = main_cell.get('parent')
            if direct_parent and direct_parent in self.groups:
                for child_cell in self.groups[direct_parent]:
                    if child_cell.get('edge') == '1':
                        has_arrow_child = True
                        break

            n_type = "Action"

            if not is_in_group:
                if "ellipse" in style:
                    n_type = "Condition"

            elif "rhombus" in style:
                if "δS" in symbol:
                    n_type = "ForceSuccess"
                elif "δF" in symbol:
                    n_type = "ForceFailure"
                elif "δRt" in symbol:
                    n_type = "Retry"
                elif "δCd" in symbol:
                    n_type = "Cooldown"
                elif "δT" in symbol:
                    n_type = "Timeout"
                elif "δRp" in symbol:
                    n_type = "Repeater"
                elif "δIf" in symbol:
                    n_type = "Conditional"
                elif "δL" in symbol:
                    n_type = "Link"
            else:
                if "??%" in symbol:
                    n_type = "WeightedSelector"
                elif "?%" in symbol:
                    n_type = "WeightedSelector"
                elif "??" in symbol:
                    n_type = "RandomSelector"
                elif "?P" in symbol:
                    n_type = "ParallelSelector"
                elif symbol in ("?", "? "):
                    if "Root" in label or label == "RootNode":
                        n_type = "Root"
                    else:
                        n_type = "Selector"
                elif "→→" in symbol or symbol.count("→") >= 2:
                    n_type = "ParallelSequence"
                elif "→" in symbol:
                    n_type = "Sequence"
                elif symbol == "":
                    if has_arrow_child:
                        n_type = "Sequence"

            if label == "RootNode":
                n_type = "Root"

            return (label, n_type, x, y, has_memory)

        connected_ids = set()
        for s, t, w in self.edges:
            connected_ids.add(s)
            connected_ids.add(t)
            
        for cid in connected_ids:
            label, n_type, x, y, has_memory = get_node_info(cid)
            logical_nodes[cid] = BTNode(cid, label, n_type, x, y, has_memory)

        # 4. Link Nodes
        root_node = None
        children_ids = set()
        
        for s, t, w in self.edges:
            if s in logical_nodes and t in logical_nodes:
                weight = 0.0
                try:
                    # Extract number from weight text (e.g., "0.5" or "50%")
                    weight_match = re.search(r"(\d+\.?\d*)", w)
                    if weight_match:
                        weight = float(weight_match.group(1))
                except:
                    weight = 0.0
                
                logical_nodes[s].add_child(logical_nodes[t], weight)
                children_ids.add(t)

        # 5. Find Root
        for cid, node in logical_nodes.items():
            if cid not in children_ids:
                if node.node_type == 'Root' or node.label == 'RootNode' or len(children_ids) == len(logical_nodes) - 1:
                    root_node = node
                    break
        
        if root_node:
            root_node.sort_children()
            return root_node
        return None

class SimbaGenerator:
    def __init__(self):
        # func_name -> {'type': str, 'has_params': bool}
        self.methods: Dict[str, Dict[str, Any]] = {}
        # list of wrappers
        self.wrappers: List[Dict[str, str]] = []

    def register_method(self, name: str, node_type: str, has_params: bool = False):
        if not name: return
        if name not in self.methods:
            self.methods[name] = {'type': node_type, 'has_params': has_params}
        else:
            if has_params: self.methods[name]['has_params'] = True

    def get_wrapper_name(self, original_name: str, args: str, node_type: str) -> str:
        # Check if wrapper already exists for these exact arguments
        for w in self.wrappers:
            if w['original'] == original_name and w['args'] == args and w['type'] == node_type:
                return w['name']
        
        # Create new wrapper name
        # Basic sanitization of args to create a readable suffix
        # Remove quotes and non-alphanumeric chars
        clean_args = re.sub(r'[^a-zA-Z0-9]', '', args.replace("'", "").replace('"', ''))
        if len(clean_args) > 30:
            clean_args = clean_args[:30]
        if not clean_args:
            clean_args = "Args"
            
        wrapper_name = f"{original_name}_{clean_args}"
        
        # Ensure uniqueness
        base_name = wrapper_name
        counter = 1
        # Check against other wrappers and registered methods
        while any(w['name'] == wrapper_name for w in self.wrappers) or wrapper_name in self.methods:
            wrapper_name = f"{base_name}{counter}"
            counter += 1
            
        self.wrappers.append({
            'name': wrapper_name,
            'original': original_name,
            'args': args,
            'type': node_type
        })
        return wrapper_name

    def generate_placeholders(self) -> str:
        lines = []
        
        # 1. Base Methods
        sorted_methods = sorted(self.methods.items())
        
        if sorted_methods:
            lines.append("// ---------------------------")
            lines.append("// ACTION AND CONDITION NODES ")
            lines.append("// ---------------------------")
            lines.append("")

        for name, info in sorted_methods:
            node_type = info['type']
            has_params = info['has_params']
            
            is_condition = (node_type == 'Condition')
            ret_type = "Boolean" if is_condition else "EBTStatus"
            def_res = "True" if is_condition else "EBTStatus.Success"
            
            param_str = "p0: string" if has_params else ""
            
            lines.append(f"function TBot.{name}({param_str}): {ret_type};")
            lines.append("begin")
            if has_params:
                lines.append(f"  WriteLn('Action : {name} with ' + p0);")
            else:
                lines.append(f"  WriteLn('Action : {name}');")
            lines.append(f"  Result := {def_res};")
            lines.append("end;")
            lines.append("")

        # 2. Wrappers
        if self.wrappers:
             lines.append("// --------")
             lines.append("// WRAPPERS")
             lines.append("// --------")
             lines.append("")
             for w in self.wrappers:
                 w_name = w['name']
                 orig = w['original']
                 args = w['args']
                 n_type = w['type']
                 
                 is_cond = (n_type == 'Condition')
                 ret_type = "Boolean" if is_cond else "EBTStatus"
                 
                 lines.append(f"function TBot.{w_name}(): {ret_type};")
                 lines.append("begin")
                 lines.append(f"  Result := Self.{orig}({args});")
                 lines.append("end;")
                 lines.append("")
        
        return "\n".join(lines)

    def generate_code(self, root: BTNode) -> str:
        if not root: return "// No Tree Found"
        return self.generate_node(root, 0)

    def generate_node(self, node: BTNode, indent_level: int) -> str:
        strategy = NodeFactory.get_strategy(node.node_type)
        return strategy.generate(node, self, indent_level)

# ==========================================
# GUI Application
# ==========================================

SETTINGS_FILE = "xml_converter_settings.json"

class ConverterApp:
    def __init__(self, root):
        self.root = root
        self.root.title("XML to Simba BT Converter")
        self.root.geometry("800x600")

        self.settings = self.load_settings()

        # UI Layout
        main_frame = tk.Frame(root, padx=10, pady=10)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # File Selection
        file_frame = tk.LabelFrame(main_frame, text="Files", padx=5, pady=5)
        file_frame.pack(fill=tk.X, pady=5)
        file_frame.columnconfigure(1, weight=1)

        tk.Label(file_frame, text="Source XML:").grid(row=0, column=0, sticky="e")
        self.xml_path_var = tk.StringVar(value=self.settings.get("last_xml", ""))
        tk.Entry(file_frame, textvariable=self.xml_path_var).grid(row=0, column=1, padx=5, sticky="ew")
        tk.Button(file_frame, text="Browse", command=self.browse_xml).grid(row=0, column=2)

        tk.Label(file_frame, text="Output Simba:").grid(row=1, column=0, sticky="e")
        self.out_path_var = tk.StringVar(value=self.settings.get("last_out", ""))
        tk.Entry(file_frame, textvariable=self.out_path_var).grid(row=1, column=1, padx=5, sticky="ew")
        tk.Button(file_frame, text="Browse", command=self.browse_out).grid(row=1, column=2)

        # Header/Footer
        text_frame = tk.Frame(main_frame)
        text_frame.pack(fill=tk.BOTH, expand=True, pady=5)

        tk.Label(text_frame, text="Script Header:").pack(anchor="w")
        self.header_text = scrolledtext.ScrolledText(text_frame, height=8)
        self.header_text.pack(fill=tk.BOTH, expand=True, pady=(0, 5))
        self.header_text.insert(tk.END, self.settings.get("header_template", "{$I WaspLib/osrs.simba}\n{$I behaviortree.simba}\n"))

        tk.Label(text_frame, text="Script Footer:").pack(anchor="w")
        self.footer_text = scrolledtext.ScrolledText(text_frame, height=8)
        self.footer_text.pack(fill=tk.BOTH, expand=True, pady=(0, 5))
        self.footer_text.insert(tk.END, self.settings.get("footer_template", "var\n  Bot: TBot;\nbegin\n  Bot.Init();\n  while True do\n    Bot.Tree.Tick();\nend."))

        # Actions
        btn_frame = tk.Frame(main_frame)
        btn_frame.pack(fill=tk.X, pady=5)
        
        self.save_defaults_var = tk.BooleanVar(value=False)
        tk.Checkbutton(btn_frame, text="Save Header/Footer as Default", variable=self.save_defaults_var).pack(side=tk.LEFT)
        
        tk.Button(btn_frame, text="Convert & Save", command=self.run_conversion, bg="#dddddd", font=("Arial", 10, "bold")).pack(side=tk.RIGHT)

    def load_settings(self):
        if os.path.exists(SETTINGS_FILE):
            try:
                with open(SETTINGS_FILE, 'r') as f:
                    return json.load(f)
            except:
                pass
        return {}

    def save_settings(self):
        self.settings["last_xml"] = self.xml_path_var.get()
        self.settings["last_out"] = self.out_path_var.get()
        if self.save_defaults_var.get():
            self.settings["header_template"] = self.header_text.get("1.0", tk.END).strip()
            self.settings["footer_template"] = self.footer_text.get("1.0", tk.END).strip()
        
        try:
            with open(SETTINGS_FILE, 'w') as f:
                json.dump(self.settings, f, indent=4)
        except Exception as e:
            print(f"Failed to save settings: {e}")

    def browse_xml(self):
        f = filedialog.askopenfilename(filetypes=[("XML Files", "*.xml"), ("All Files", "*.*")])
        if f: self.xml_path_var.set(f)

    def browse_out(self):
        f = filedialog.asksaveasfilename(defaultextension=".simba", filetypes=[("Simba Scripts", "*.simba")])
        if f: self.out_path_var.set(f)

    def run_conversion(self):
        xml_path = self.xml_path_var.get()
        out_path = self.out_path_var.get()

        if not xml_path or not out_path:
            messagebox.showerror("Error", "Please select both input XML and output Simba file paths.")
            return

        try:
            # 1. Parse
            parser = GraphParser()
            root_node = parser.parse(xml_path)
            
            if not root_node:
                messagebox.showerror("Error", "Could not identify a Root Node in the XML.\nEnsure your root node has 'Root' in its label.")
                return

            # 2. Generate
            gen = SimbaGenerator()
            tree_code = gen.generate_code(root_node)
            placeholders = gen.generate_placeholders()

            # 3. Assemble
            user_header = self.header_text.get("1.0", tk.END).strip()
            user_footer = self.footer_text.get("1.0", tk.END).strip()
            
            # Boilerplate parts
            bot_record = "type\n  TBot = record\n    MainForm: TScriptForm;\n    Tree: TBehaviorTree;\n    MainConfig: TConfigJSON;\n  end;"
            init_start = "procedure TBot.Init();\nbegin\n  Self.Tree.Setup('MyBot');"
            init_end = "  Self.Tree.PrintStructure();\n  AddOnTerminate(@Self.Tree.Free);\nend;"

            full_script = (
                f"{user_header}\n\n"
                f"{bot_record}\n\n"
                f"{placeholders}\n\n"
                f"{init_start}\n"
                f"  // Generated Tree\n"
                f"  Self.Tree.Root := {tree_code};\n\n"
                f"{init_end}\n\n"
                f"{user_footer}"
            )

            # 4. Write
            with open(out_path, 'w', encoding='utf-8') as f:
                f.write(full_script)

            self.save_settings()
            messagebox.showinfo("Success", f"Simba script generated at:\n{out_path}")

        except Exception as e:
            import traceback
            traceback.print_exc()
            messagebox.showerror("Error", f"Conversion failed:\n{str(e)}")

if __name__ == "__main__":
    root = tk.Tk()
    app = ConverterApp(root)
    root.mainloop()
