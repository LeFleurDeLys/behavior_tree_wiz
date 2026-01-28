# XML to Simba Behavior Tree Converter Documentation

## 1. System Overview

The **XML to Simba Converter** is a specialized Python utility designed to bridge the gap between visual Behavior Tree design and executable Simba code for OSRS botting.

### Purpose
The system allows developers to design Behavior Trees visually using draw.io, to then automatically convert them into a working behavior tree implementation script skelleton compatible with the `WaspLib BehaviorTree library` .

### Core Logic: The "Perfect Skeleton"
The application operates by parsing an input XML file, interpreting geometric shapes and connections as logical tree nodes, and generating a **"Perfect Skeleton"**—a fully compilable `TBehaviorTree` implementation that requires no manual structural adjustments. It handles:
*   **Visual Sorting**: Children are automatically sorted by their X-coordinate. This ensures that the Left-to-Right visual flow in the editor equates to the execution order in the code, eliminating ambiguity.
*   **Recursive Structure**: It systematically constructs the nested `Self.Tree` calls (e.g., `Self.Tree.Selector(...)`) to mirror the tree's depth and breadth.
*   **Stub Generation**: It automatically generates function stubs (e.g., `function ActionName(): Boolean;`) for every discovered Action and Condition, allowing the code to compile immediately without "unknown identifier" errors.
*   **Wrapper Generation**: For nodes with arguments (e.g., `Eat(Food)`), it generates specific wrapper functions to bridge the generic tree interface with the specific parameterized calls.

### 1.1 User Interface Capabilities
The converter provides a user-friendly GUI to manage the conversion process:
*   **File Selection**: Intuitive inputs for selecting the Source XML file and defining the Output Simba file path.
*   **Template Customization**: Text areas to edit and customize the Header and Footer code that will be wrapped around the generated tree.
*   **Persistence**: A "Save Header/Footer as Default" checkbox that saves user preferences to a local JSON file for future sessions.
*   **Execution**: A prominent "Convert & Save" button that triggers the process and provides immediate popup feedback on success or failure.

---

## 2. Architectural Design

The application follows a modular architecture heavily relying on the **Strategy** and **Factory** design patterns to manage the complexity of different Behavior Tree node types.

### Design Patterns

#### Strategy Pattern
The core of the code generation logic uses the Strategy pattern to separate *how* a node is generated from the node itself.
*   **`GenerationStrategy` (Abstract Base)**: Defines the contract `generate(...)`.
*   **`CompositeStrategy`**: Handles control flow nodes (Selectors, Sequences) that contain children. It recursively calls generators for child nodes.
*   **`LeafStrategy`**: Handles execution nodes (Actions, Conditions). It manages function name parsing and parameter wrapping.
*   **`WeightedSelectorStrategy`**: A specialized strategy that parses and injects probability weights alongside children.

#### Factory Pattern
*   **`NodeFactory`**: Acts as a central registry. It takes a node type string (e.g., "Selector") and returns the appropriate `GenerationStrategy` instance. This decouples the parser from the code generator.

#### Separation of Concerns
*   **`GraphParser`**: Purely responsible for reading XML and building an intermediate object graph (`BTNode`). It knows nothing about Simba code.
*   **`SimbaGenerator`**: Responsible for converting the `BTNode` graph into string output. It manages the global state of method definitions and wrappers.
*   **`ConverterApp`**: Manages the UI and orchestration, keeping presentation separate from logic.

---

## 3. Execution Workflow

The conversion process follows a linear pipeline:

1.  **Input Acquisition**:
    *   The user selects an XML file via the GUI.
    *   The `GraphParser` is instantiated.

2.  **XML Parsing & Graph Reconstruction** (`GraphParser.parse`):
    *   **Cell Extraction**: Iterates through all `mxCell` elements to separate vertices (nodes) from edges (connections).
    *   **Geometry Calculation**: Calculates absolute (X, Y) coordinates for every node, handling nested parent groups if necessary.
    *   **Node Type Determination**: Analyzes node labels and shapes to determine the specific node type. The logic applies the following checks in order of precedence (High to Low):
        *   **ParallelSelector**: Label contains "ParallelSelector" OR "?P"
        *   **ParallelSequence**: Label contains "ParallelSequence" OR "→→" (or multiple arrows)
        *   **WeightedSelector**: Label contains "WeightedSelector" OR "??%" OR "?%"
        *   **RandomSelector**: Label contains "RandomSelector" OR "??"
        *   **Selector**: Label contains "Selector" OR "?"
        *   **Sequence**: Label contains "Sequence" OR "→"
        *   **Root**: The only node without a parent OR Label contains "Root"
        *   **Condition**: Shape is "ellipse" OR Label starts with "Is"
        *   **Action**: Default (if no other match)
    *   **Linkage**: Matches edge source/target IDs to connect `BTNode` objects. Every node that is the target of an edge is tracked in a set of child IDs.
    *   **Ordering**: Once the Root is found, `root_node.sort_children()` is called. This recursively sorts all child arrays by their X-coordinate to ensure the visual left-to-right flow in the editor equates to execution order in the code.

3.  **Code Generation** (`SimbaGenerator.generate_code`):
    *   The generator starts at the **Root** node.
    *   It requests the appropriate strategy from `NodeFactory`.
    *   **Recursive Traversal**: The strategy generates code for the current node and recursively calls `generate_node` for all children.
    *   **Method Registration**: Leaf nodes register their function names and parameters with the generator during this pass.

4.  **Stub & Wrapper Synthesis**:
    *   `generate_placeholders()` iterates through registered methods to create Pascal function stubs (`function TBot.ActionName...`).
    *   If nodes have arguments (e.g., `Eat(Food)`), a wrapper function is generated to adapt the parameterized call to the signature expected by the behavior tree library.

5.  **Assembly & Output**:
    *   The user-defined Header and Footer are combined with the generated stubs and the tree definition.
    *   The result is written to the `.simba` file.

---

## 4. Extensibility Guide (Adding New Nodes)

To add a new node type (e.g., a "Decorator"), follow these steps:

### Step 1: Implement a Strategy
Create a class inheriting from `GenerationStrategy`.

```python
class DecoratorStrategy(GenerationStrategy):
    def __init__(self, method_name: str):
        self.method_name = method_name

    def generate(self, node: BTNode, generator_ref: 'SimbaGenerator', indent_level: int) -> str:
        indent = "  " * indent_level
        display_name = node.label.replace("'", "''")
        
        # Decorators typically have exactly one child
        if not node.children:
             return f"{indent}// Error: Decorator {display_name} has no child"

        child_code = generator_ref.generate_node(node.children[0], indent_level + 1)
        
        return (f"{indent}Self.Tree.{self.method_name}('{display_name}',\n"
                f"{child_code}\n"
                f"{indent})")
```

### Step 2: Register in Factory
Add the new type to the `NodeFactory._strategies` dictionary.

```python
class NodeFactory:
    _strategies = {
        # ... existing strategies ...
        'Decorator': DecoratorStrategy('CreateDecorator'), # <--- Add this
    }
```

### Step 3: Update Parser Logic
Modify `GraphParser.get_node_info` to recognize the new node type from the XML label.

```python
# Inside get_node_info method:
# ...
elif "Decorator" in label or label.startswith("^"): #Example of a symbol (we usually use Delta)... I will add decorators in a bit, but my brain is fried atm 
    n_type = "Decorator"
# ...
```

---

## 5. Code Reference

### `BTNode`
*   **Responsibility**: Intermediate data representation of a tree node.
*   **Key Attributes**: `node_type`, `children`, `geometry_x`.
*   **Key Methods**: `sort_children()` (ensures correct execution order).

### `NodeFactory`
*   **Responsibility**: Centralizes node creation logic.
*   **Key Methods**: `get_strategy(node_type)` returns the specific `GenerationStrategy`.

### `GraphParser`
*   **Responsibility**: Parsing XML and geometric analysis.
*   **Key Methods**:
    *   `parse(xml_path)`: Entry point, returns the Root `BTNode`. It performs the multi-pass parsing, node linking, and utilizes a heuristic-based root identification (checking for orphan nodes and specific "Root" labels).
    *   `get_node_info(cell_id)`: Heuristics to determine node type from text labels (e.g., mapping "?" to "Selector").

### `SimbaGenerator`
*   **Responsibility**: Generating the final string output.
*   **Key Attributes**: `methods` (tracks discovered actions), `wrappers` (tracks parameter wrappers).
*   **Key Methods**:
    *   `generate_code(root)`: Starts the recursive generation.
    *   `generate_placeholders()`: Creates the Pascal function stubs.
    *   `get_wrapper_name(...)`: Manages unique naming for parameterized calls.

### `ConverterApp`
*   **Responsibility**: Tkinter GUI and file I/O.
*   **Key Methods**: `run_conversion()` orchestrates the entire flow.
