# XML to Simba Behavior Tree Converter Documentation

## 1. System Overview

The **XML to Simba Converter** is a specialized Python utility designed to bridge the gap between visual Behavior Tree design and executable Simba code for OSRS botting.

### Purpose
The system allows developers to design Behavior Trees visually using draw.io, to then automatically convert them into a working behavior tree implementation script skeleton compatible with the `WaspLib BehaviorTree library`.

### Core Logic: The "Perfect Skeleton"
The application operates by parsing an input XML file, interpreting geometric shapes and connections as logical tree nodes, and generating a **"Perfect Skeleton"**—a fully compilable `TBehaviorTree` implementation that requires no manual structural adjustments. It handles:
*   **Visual Sorting**: Children are automatically sorted by their X-coordinate. This ensures that the Left-to-Right visual flow in the editor equates to the execution order in the code, eliminating ambiguity.
*   **Recursive Structure**: It systematically constructs the nested `Self.Tree` calls (e.g., `Self.Tree.Selector(...)`) to mirror the tree's depth and breadth.
*   **Stub Generation**: It automatically generates function stubs (e.g., `function TBot.ActionName(): EBTStatus;`) for every discovered Action and Condition, allowing the code to compile immediately without "unknown identifier" errors.
*   **Wrapper Generation**: For nodes with arguments (e.g., `Eat(Food)`), it generates specific wrapper functions to bridge the generic tree interface with the specific parameterized calls.
*   **Memory Detection**: It detects rounded rectangles in the diagram and automatically enables the 'Memory' flag for Selector and Sequence nodes in the generated code. Memory mode is **only supported** for Selector and Sequence — not for ParallelSelector, ParallelSequence, RandomSelector, or WeightedSelector.
*   **Decorator Support**: Detects diamond-shaped nodes inside groups and maps delta-symbol text to 8 decorator types (ForceSuccess, ForceFailure, Retry, Cooldown, Timeout, Repeater, Conditional, Link) with automatic parameter extraction from labels.
*   **Auto Boilerplate**: Generates the `TBot` record (with `MainForm`, `Tree`, and `MainConfig` fields), the `Init()` procedure with tree setup, `PrintStructure()` call, and `AddOnTerminate(@Self.Tree.Free)` cleanup — all automatically injected into the output.

### 1.1 User Interface Capabilities
The converter provides a user-friendly GUI to manage the conversion process:
*   **File Selection**: Browses Windows Explorer for selecting the Source XML file and defining the Output Simba file path. (The tool only creates from scratch at the moment, cannot yet use it to generate new structures on the tree.)
*   **Template Customization**: Text areas to edit and customize the Header and Footer code that will be wrapped around the generated code.
*   **Persistence**: A "Save Header/Footer as Default" checkbox that saves user preferences (including last-used file paths) to a local JSON file (`xml_converter_settings.json`) in the same directory as the script.
*   **Execution**: Convert & Save button with confirmation message for failure or success.

---

## 2. Architectural Design

The application follows a modular architecture heavily relying on the **Strategy** and **Factory** design patterns to manage the complexity of different Behavior Tree node types.

### Design Patterns

#### Strategy Pattern
The core of the code generation logic uses the Strategy pattern to separate *how* a node is generated from the node itself.
*   **`GenerationStrategy` (Abstract Base)**: Defines the contract `generate(...)`.
*   **`CompositeStrategy`**: Handles control flow nodes (Selectors, Sequences, ParallelSelector, ParallelSequence, RandomSelector) that contain children. It recursively calls generators for child nodes. Supports memory mode for `CreateSelector` and `CreateSequence` only.
*   **`LeafStrategy`**: Handles execution nodes (Actions, Conditions). It manages function name parsing and parameter wrapping.
*   **`WeightedSelectorStrategy`**: A specialized strategy that parses and injects probability weights (from edge labels) alongside children.
*   **`DecoratorStrategy`**: Handles decorator nodes that wrap exactly one child. It parses parameters from the label (integers for Retry/Cooldown/Timeout/Repeater, method references for Conditional) and injects them into the generated Simba call. Supports memory mode for ForceSuccess and ForceFailure.
*   **`RootStrategy`**: Handles the root node. If it has one child, it delegates directly. If multiple children, it wraps them in a Selector.

#### Factory Pattern
*   **`NodeFactory`**: Acts as a central registry. It takes a node type string (e.g., "Selector") and returns the appropriate `GenerationStrategy` instance. Unknown types default to `LeafStrategy('CreateAction')`. This decouples the parser from the code generator.

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
    *   **Cell Extraction**: Iterates through all `mxCell` elements to separate vertices (nodes) from edges (connections). HTML tags are stripped from cell values. Edge labels that are child cells of an edge are also collected.
    *   **Geometry Calculation**: Calculates absolute (X, Y) coordinates for every node, handling nested parent groups if necessary by walking up the parent chain and accumulating offsets.
    *   **Memory Attribute**: Checks the cell style for `rounded=1`. If present, the node is flagged as having memory.
    *   **Node Type Determination** — Three-Branch Detection:

    The parser uses the **symbol** (the cell's own text value) and the node's group membership to determine type. The detection follows a strict three-branch structure:

    **Branch 1 — Standalone nodes (not in a group, parent is `0` or `1`):**
    These nodes can only be Conditions or Actions:
                    *   **Condition**: Shape is `ellipse`
    *   **Action**: Default fallback

    **Branch 2 — Grouped nodes with rhombus (diamond) shape:**
    These are detected as Decorators based on the delta symbol in the diamond's text:
    *   **ForceSuccess**: Diamond contains `δS`
    *   **ForceFailure**: Diamond contains `δF`
    *   **Retry**: Diamond contains `δRt`
    *   **Cooldown**: Diamond contains `δCd`
    *   **Timeout**: Diamond contains `δT`
    *   **Repeater**: Diamond contains `δRp`
    *   **Conditional**: Diamond contains `δIf`
    *   **Link**: Diamond contains `δL`

    **Branch 3 — Grouped nodes without rhombus (other shapes):**
    These are checked for composite symbols. The checks are applied in this order (first match wins):
    1.  **WeightedSelector**: Symbol contains `??%`
    2.  **WeightedSelector**: Symbol contains `?%`
    3.  **RandomSelector**: Symbol contains `??`
    4.  **ParallelSelector**: Symbol contains `?P`
    5.  **Selector**: Symbol is exactly `?` or `? ` (but if the display label contains `Root` or is `RootNode`, it becomes **Root** instead)
    6.  **ParallelSequence**: Symbol contains `→→` or has 2+ `→` characters
    7.  **Sequence**: Symbol contains `→`
    8.  **Sequence** (fallback): Symbol is empty AND the node's parent group contains an edge
    9.  **Action**: Default fallback if nothing matches

    > **Important**: Text-based keywords like "Selector", "Sequence", etc. are **not** used for detection. Only the symbols listed above are recognized. The order of checks matters — e.g., `??%` is checked before `??` so that `??%` is correctly identified as WeightedSelector rather than RandomSelector.

    *   **Label Resolution**: When a node is inside a group, the parser searches the group's children for a sibling cell with `text` in its style. That sibling's text becomes the **display name** (label) used in the generated Simba code. The shape cell's own text (the symbol) is used only for type detection.

    *   **Linkage**: Matches edge source/target IDs to connect `BTNode` objects. Every node that is the target of an edge is tracked in a set of child IDs.

    *   **Root Identification**: After linking, the root is found by searching for a node that:
        1. Is not in the set of child IDs (i.e., no edge points to it), AND
        2. Either: has `node_type == 'Root'`, or has label `'RootNode'`, or is the sole node that is not anyone's child.

    *   **Ordering**: Once the Root is found, `root_node.sort_children()` is called. This recursively sorts all child arrays by their X-coordinate to ensure the visual left-to-right flow in the editor equates to execution order in the code. Child weights (for WeightedSelector) are sorted alongside.

3.  **Code Generation** (`SimbaGenerator.generate_code`):
    *   The generator starts at the **Root** node.
    *   It requests the appropriate strategy from `NodeFactory`.
    *   **Recursive Traversal**: The strategy generates code for the current node and recursively calls `generate_node` for all children.
    *   **Method Registration**: Leaf nodes register their function names and parameters with the generator during this pass.
    *   **Memory Injection**: For Selector and Sequence nodes flagged with memory, it appends a `True` argument to the constructor (e.g., `Self.Tree.Selector(..., True)`). Memory is **not** injected for any other composite type.
    *   **Decorator Generation**: `DecoratorStrategy` wraps its single child's code and appends parsed parameters (e.g., retry count, cooldown duration, condition reference). For ForceSuccess/ForceFailure, the memory flag appends `, True`.
    *   **WeightedSelector Generation**: `WeightedSelectorStrategy` generates `Self.Tree.CreateWeightedSelector('Name', [children], [weights])` with weights extracted from edge labels.

4.  **Stub & Wrapper Synthesis**:
    *   `generate_placeholders()` iterates through registered methods to create Pascal function stubs (`function TBot.ActionName...`). Stubs include a `WriteLn('Action : ActionName');` debug message (or `WriteLn('Action : ActionName with ' + p0);` for parameterized methods).
    *   If nodes have arguments (e.g., `Eat(Food)`), a wrapper function is generated to adapt the parameterized call to the signature expected by the behavior tree library. The wrapper calls the base method with the exact argument string from the label.
    *   Method names are sanitized to alphanumeric + underscore characters. Wrapper names are derived from the original name + cleaned arguments (e.g., `Eat_Food`).

5.  **Assembly & Output**:
    *   The user-defined Header and Footer are combined with the auto-generated boilerplate, stubs, and tree definition.
    *   The full output structure is:
        ```
        [User Header]
        
        type
          TBot = record
            MainForm: TScriptForm;
            Tree: TBehaviorTree;
            MainConfig: TConfigJSON;
          end;
        
        // ACTION AND CONDITION NODES
        function TBot.<Action/Condition stubs>...
        
        // WRAPPERS
        function TBot.<Wrapper stubs>...
        
        procedure TBot.Init();
        begin
          Self.Tree.Setup('MyBot');
          // Generated Tree
          Self.Tree.Root := <generated tree code>;
        
          Self.Tree.PrintStructure();
          AddOnTerminate(@Self.Tree.Free);
        end;
        
        [User Footer]
        ```
    *   The result is written to the `.simba` file.

---

## 4. Extensibility Guide (Adding New Nodes)

Decorators are already implemented (see Section 3 for detection details). To add a **new decorator type** or any other node type, follow these steps:

### Step 1: Implement a Strategy
Create a class inheriting from `GenerationStrategy`. For a new decorator, inherit from or replicate `DecoratorStrategy`:

```python
class MyNewDecoratorStrategy(GenerationStrategy):
    def __init__(self, method_name: str):
        self.method_name = method_name

    def generate(self, node: BTNode, generator_ref: 'SimbaGenerator', indent_level: int) -> str:
        indent = "  " * indent_level
        display_name = node.label.replace("'", "''")

        if not node.children:
             return f"{indent}// Decorator '{display_name}' has no child"

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
        'MyNewDecorator': MyNewDecoratorStrategy('CreateMyNewDecorator'),
    }
```

### Step 3: Update Parser Logic
Add a new delta symbol mapping in `GraphParser.get_node_info` inside the `elif "rhombus" in style:` block:

```python
elif "δN" in symbol:
    n_type = "MyNewDecorator"
```

For composites, add the symbol check inside the `else` branch (grouped non-rhombus nodes), before the existing checks. Order matters — more specific symbols must be checked first.

### Decorator Parameter Parsing

If your decorator accepts parameters, add parsing logic to `DecoratorStrategy._parse_decorator_parameters()`. Parameters are extracted from the label via regex `r'^[^(]*\((.*)\)$'` and stored on the `BTNode` instance (e.g., `node.max_retries`, `node.timer_duration`). The `generate()` method then formats them into the Simba call. Non-integer values (such as Simba expressions like `Random(1000, 2000)`) fall through to `node.decorator_raw_param` and are emitted verbatim.

---

## 4.1. Getting the Node Symbols for draw.io

Download **`photo_of_graph.draw.io.png`** from the repository and import it into your draw.io canvas via drag & drop or **Arrange → Insert → Image**. The image contains all available node symbols that you can copy and paste into your own behavior tree diagrams.

---

## 4.2. Complete Node Symbols Reference

### Detection Architecture

Node type detection depends on whether the node is **standalone** (not in a group) or **grouped** (inside a draw.io group):

- **Standalone nodes**: Only Condition (ellipse or `Is` prefix) and Action (default) can be detected.
- **Grouped nodes**: Checked for decorator symbols (if rhombus) or composite symbols (if other shape), with Action as the fallback.

This means **all composites and decorators must be inside draw.io groups** to be detected. A standalone rectangle with text `?` will be detected as an Action, not a Selector.

### Composites

| Node Type | Symbol | Shape | Memory Mode | Example Display Name | Generated Simba Call |
|-----------|--------|-------|-------------|---------------------|---------------------|
| Selector | `?` | Rectangle (grouped) | Rounded rect → `True` | `ChooseOne` | `Self.Tree.CreateSelector('ChooseOne', [...])` |
| Sequence | `→` | Rectangle (grouped) | Rounded rect → `True` | `DoAll` | `Self.Tree.CreateSequence('DoAll', [...])` |
| ParallelSelector | `?P` | Rectangle (grouped) | Not supported | `RunAny` | `Self.Tree.CreateParallelSelector('RunAny', [...])` |
| ParallelSequence | `→→` | Rectangle (grouped) | Not supported | `RunAll` | `Self.Tree.CreateParallelSequence('RunAll', [...])` |
| RandomSelector | `??` | Rectangle (grouped) | Not supported | `PickRandom` | `Self.Tree.CreateRandomSelector('PickRandom', [...])` |
| WeightedSelector | `??%` or `?%` | Rectangle (grouped) | Not supported | `WeightedPick` | `Self.Tree.CreateWeightedSelector('WeightedPick', [...], [w1, w2])` |

> **Memory Mode**: Only Selector and Sequence support memory mode (via `rounded=1` in the style). This appends `, True` to the generated call. Other composites ignore the memory flag silently.

> **WeightedSelector Weights**: Weights are specified as numeric labels on the **edges** connecting the WeightedSelector to its children. The first numeric value in each edge label is extracted. Order: `??%` is checked before `?%` and `??` to avoid misidentification.

### Leaves

| Node Type | Detection Rule | Shape | Example Label | Generated Simba Call |
|-----------|---------------|-------|---------------|---------------------|
| Condition | Ellipse shape | Ellipse | `IsAlive` | `Self.Tree.CreateCondition('IsAlive', @Self.IsAlive)` |
| Condition (params) | Ellipse shape | Ellipse | `IsHungry(Food)` | `Self.Tree.CreateCondition('IsHungry(Food)', @Self.IsHungry_Food)` + wrapper stub |
| Action | Default fallback | Rectangle | `Eat` | `Self.Tree.CreateAction('Eat', @Self.Eat)` |
| Action (params) | Default fallback | Rectangle | `Eat(Food)` | `Self.Tree.CreateAction('Eat(Food)', @Self.Eat_Food)` + wrapper stub |

> **Note**: The ellipse shape check only applies to **standalone** (non-grouped) nodes. Grouped non-rhombus nodes are checked for composite symbols and default to Action.

#### Parameterized Actions & Conditions

When you add parentheses with a value to an Action or Condition label (e.g., `Eat(Food)`, `Log(Hello world)`), the converter generates **two** things:

1. **Base method stub** — accepts a `p0: string` parameter and includes a `WriteLn` debug message:
   ```pascal
   function TBot.Eat(p0: string): EBTStatus;
   begin
     WriteLn('Action : Eat with ' + p0);
     Result := EBTStatus.Success;
   end;
   ```

2. **Wrapper function** — calls the base method with your specific argument, adapting it to the parameterless signature the tree expects:
   ```pascal
   function TBot.Eat_Food(): EBTStatus;
   begin
     Result := Self.Eat(Food);
   end;
   ```

You can put any string or expression inside the parentheses — it is passed through verbatim to the wrapper call (e.g., `Log(Starting up)`, `WalkTo(Lumbridge)`, `Eat('Shark')`). The `WriteLn` message in the stub helps with debugging during development.

### Root

| Node Type | Detection Rule | Example Label |
|-----------|---------------|---------------|
| Root | Only node without a parent in the tree (no edge points to it), OR grouped `?` node with display label containing `Root`, OR any node with label `RootNode` | `Root` |

In generated code, `RootStrategy` delegates to its first child. If the root has multiple children, they are automatically wrapped in a `CreateSelector` call.

### Decorators

> **All decorators must be inside a draw.io group** with a diamond (rhombus) shape.

| Symbol | Type | Parameter | Example Label | Generated Simba Call |
|--------|------|-----------|---------------|---------------------|
| `δS` | ForceSuccess | None | `AlwaysWin` | `Self.Tree.CreateForceSuccess('AlwaysWin', <child>)` |
| `δF` | ForceFailure | None | `AlwaysFail` | `Self.Tree.CreateForceFailure('AlwaysFail', <child>)` |
| `δRt` | Retry | `max_retries` (int or expression) | `Retry(5)` | `Self.Tree.CreateRetry('Retry', <child>, 5)` |
| `δCd` | Cooldown | `duration_ms` (int or expression) | `Cooldown(3000)` | `Self.Tree.CreateCooldown('Cooldown', <child>, 3000)` |
| `δT` | Timeout | `duration_ms` (int or expression) | `Timeout(5000)` | `Self.Tree.CreateTimeout('Timeout', <child>, 5000)` |
| `δRp` | Repeater | `count` (int or expression) | `Repeat(3)` | `Self.Tree.CreateRepeater('Repeat', <child>, 3)` |
| `δIf` | Conditional | `condition_ref` (string) | `IfGuard(IsReady)` | `Self.Tree.CreateConditional('IfGuard', <child>, @IsReady)` |
| `δL` | Link | None | `GoToNode` | `Self.Tree.CreateLink('GoToNode', <child>)` |

#### Decorator Parameter Details

- **Retry / Cooldown / Timeout / Repeater**: Pass an integer in parentheses (e.g., `Retry(5)`, `Cooldown(3000)`). Non-integer values (such as Simba expressions like `Random(1000, 2000)`) are passed through verbatim as raw expressions.
- **Conditional**: Pass a method reference (e.g., `IfGuard(IsReady)` or `IfGuard(@Self.CheckReady)`). The `@` prefix is auto-added if omitted. References starting with `@Self.` or `@` are used as-is.
- **ForceSuccess / ForceFailure**: No parameters. Supports **memory mode** via rounded rectangles (appends `, True`). Link does not support memory mode.

---

## 5. Code Reference

### `BTNode`
*   **Responsibility**: Intermediate data representation of a tree node.
*   **Key Attributes**:
    *   `node_type` — The detected type string (e.g., `'Selector'`, `'Action'`, `'ForceSuccess'`).
    *   `children` — List of child `BTNode` objects.
    *   `child_weights` — List of float weights (for WeightedSelector), aligned with `children`.
    *   `geometry_x`, `geometry_y` — Absolute X/Y coordinates (accumulated through parent groups).
    *   `has_memory` — Whether `rounded=1` was detected in the cell style.
    *   Decorator-specific: `max_retries`, `timer_duration`, `repeat_count`, `condition_reference`, `decorator_raw_param`.
*   **Key Methods**: `sort_children()` — Recursively sorts children (and their weights) by X-coordinate. `add_child(child, weight)` — Appends a child with an optional weight.

### `NodeFactory`
*   **Responsibility**: Centralizes node creation logic via the Strategy pattern.
*   **Registered Strategies**:
    *   Composites: `Selector`, `ParallelSelector`, `RandomSelector`, `WeightedSelector`, `Sequence`, `ParallelSequence` (all use `CompositeStrategy` except `WeightedSelector` which has its own strategy).
    *   Leaves: `Action`, `Condition` (use `LeafStrategy`).
    *   Special: `Root` (uses `RootStrategy`).
    *   Decorators: `ForceSuccess`, `ForceFailure`, `Retry`, `Cooldown`, `Timeout`, `Repeater`, `Conditional`, `Link` (all use `DecoratorStrategy`).
*   **Fallback**: Unknown node types default to `LeafStrategy('CreateAction')`.
*   **Key Methods**: `get_strategy(node_type)` returns the specific `GenerationStrategy`.

### `GraphParser`
*   **Responsibility**: Parsing XML and geometric analysis. Builds the `BTNode` tree.
*   **Key Attributes**:
    *   `cells` — Dict of `cell_id → mxCell` for all vertex cells.
    *   `edges` — List of `(source_id, target_id, label_text)` tuples.
    *   `groups` — Dict of `parent_id → list of child mxCell elements`.
*   **Key Methods**:
    *   `parse(xml_path)` — Entry point, returns the Root `BTNode`. Performs multi-pass parsing: cell extraction, edge collection with label resolution, node creation via `get_node_info`, edge-based linking, root identification, and recursive X-coordinate sorting.
    *   `get_node_info(cell_id)` — Determines node type, label, geometry, and memory flag. Uses the three-branch detection logic (standalone → Condition/Action; grouped rhombus → Decorator; grouped other → Composite/Action). Resolves display names from group sibling text labels.

### `SimbaGenerator`
*   **Responsibility**: Generating the final string output.
*   **Key Attributes**:
    *   `methods` — Dict of `func_name → {'type': str, 'has_params': bool}`. Tracks all discovered actions and conditions.
    *   `wrappers` — List of dicts with keys `name`, `original`, `args`, `type`. Tracks parameter wrappers.
*   **Key Methods**:
    *   `generate_code(root)` — Starts the recursive generation from the root node.
    *   `generate_node(node, indent_level)` — Dispatches to the strategy from `NodeFactory`.
    *   `generate_placeholders()` — Creates the Pascal function stubs and wrapper functions. Stubs return `EBTStatus` for Actions, `Boolean` for Conditions. Parameterized stubs accept `p0: string`.
    *   `register_method(name, node_type, has_params)` — Registers a discovered method.
    *   `get_wrapper_name(original_name, args, node_type)` — Generates a unique wrapper name by cleaning the args string (alphanumeric only, max 30 chars). Ensures uniqueness against existing wrappers and methods.

### `ConverterApp`
*   **Responsibility**: Tkinter GUI and file I/O.
*   **Key Attributes**:
    *   `SETTINGS_FILE` — `"xml_converter_settings.json"`, stored in the script's directory.
    *   Default header: `{$I WaspLib/osrs.simba}` and `{$I behaviortree.simba}`.
    *   Default footer: `var Bot: TBot; begin Bot.Init(); while True do Bot.Tree.Tick(); end.`
*   **Key Methods**:
    *   `run_conversion()` — Orchestrates the entire flow: parse → generate → assemble → write. Injects auto-generated `TBot` record, stubs, wrappers, and `Init()` procedure between user header and footer.
    *   `load_settings()` / `save_settings()` — Manages persistence of last-used paths and header/footer templates.

### Auto-Generated Output Components

The converter injects the following code between the user's header and footer:

1. **`TBot` record** — With fields `MainForm: TScriptForm`, `Tree: TBehaviorTree`, `MainConfig: TConfigJSON`.
2. **Action/Condition stubs** — One `function TBot.<Name>()` per discovered leaf node.
3. **Wrapper functions** — One per parameterized action/condition.
4. **`TBot.Init()` procedure** — Contains `Self.Tree.Setup('MyBot')`, the generated tree assigned to `Self.Tree.Root`, `Self.Tree.PrintStructure()`, and `AddOnTerminate(@Self.Tree.Free)`.
