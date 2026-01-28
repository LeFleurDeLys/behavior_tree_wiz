# XML to Simba Converter

This tool converts visual Behavior Trees designed in XML format (e.g., from diagrams.net or draw.io) into executable Pascal/Simba code for OSRS botting. It bridges the gap between visual design and the `WaspLib` behavior tree implementation.

## Features
- **Visual to Code**: Converts diagrammatic nodes (Selectors, Sequences, Actions) into valid Simba code.
- **Stub Generation**: Automatically generates function stubs for actions and conditions defined in your diagram.
- **Smart Sorting**: Executes nodes in visual left-to-right order.
- **Parameter Support**: Handles parameterized actions (e.g., `Eat(Food)`) by generating wrapper functions.

## Quick Start

### Prerequisites
- Python 3.x
- `tkinter` (usually included with Python on Windows)

### Running the Tool
Open a terminal in this directory and run:

```bash
python "behavior_tree_wiz.py"
```

1.  **Source XML**: Select your `.xml` file containing the behavior tree diagram (which uses the given node types in `ExampleTree.xml`).
2.  **Output Simba**: Choose where to save the generated `.simba` script.
3.  **Convert**: Click "Convert & Save".

## Documentation
<img width="1048" height="778" alt="image" src="https://github.com/user-attachments/assets/75d2d262-6394-4478-912f-967a741d6849" />
These are the currently recognized node types. Decorators to be added soon...

For a deep dive into the system architecture, design patterns, and extensibility guides, please refer to the:
**[Full Technical Documentation](./docs.md)**
