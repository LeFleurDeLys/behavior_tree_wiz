# XML to Simba Converter

This tool converts visual behavior trees designed in XML format (e.g., from diagrams.net or draw.io) into an executable Simba 2000 script skelleton. It bridges the gap between visual design and the `WaspLib` behavior tree implementation .
## Features
- **Visual to Code**: Converts diagrammatic nodes (Selectors, Sequences, Actions) into valid Simba code compatible with the behavior tree library.
- **Stub Generation**: Automatically generates function stubs for actions and conditions defined in your diagram.
- **Smart Sorting**: Executes nodes in visual left-to-right order.
- **Memory Support**: Enable memory on Sequences and Selectors by simply using rounded rectangles in your diagram.
- **Parameter Support**: Handles parameterized actions (e.g., `Eat(Food)`) by generating wrapper functions.
  
### Running the Tool
Run behavior_tree_wiz.exe or the equivalent python script.

1.  **Source XML**: Select your `.xml` file containing the behavior tree diagram (which uses the given node types in `ExampleTree.xml`).
2.  **Output Simba**: Choose where to save the generated `.simba` script.
3.  **Header & Footer**: You can add whatever you want there, the generated tree and functions will appear sandwiched right between the header and footer you put in.
4.  **Save as default**: Will create a small file where script was ran to save the default header and footer.
5.  **Convert**: Click "Convert & Save".
   

<img width="799" height="634" alt="image" src="https://github.com/user-attachments/assets/98f9f67a-9e14-4055-a8da-bdc33e02066a" />

## Creates Conditions & Actions Placeholder Stubs 
<img width="799" height="439" alt="image" src="https://github.com/user-attachments/assets/b6b43709-5eca-4dc9-b45a-b2fe7d906ba7" />

## Generates the whole behavior tree automatically
<img width="703" height="746" alt="image" src="https://github.com/user-attachments/assets/2824b72c-ba53-4288-b5d8-224c0abae0d0" />

## Creates wrappers and forward declarations for link and conditional nodes
<img width="469" height="227" alt="image" src="https://github.com/user-attachments/assets/0afc6990-40ce-4e6a-a541-9bd814810050" /> 

<img width="477" height="120" alt="image" src="https://github.com/user-attachments/assets/bd3a092f-50d4-4f4d-bcda-bf1a8c68c84e" />

# Available Nodes at the Moment (import "availablenodes.draw.io.png/" into draw.io to have them)
<img width="1333" height="563" alt="availablenodes drawio" src="https://github.com/user-attachments/assets/58da6b74-aeba-45e6-8f8e-9b3210139a29" />
You can make any sequence or selector type of node have memory by ticking the square's "Rounded" style on draw.io

## Example draw.io Behavior Tree snippets
#This is a LinkDecorator working within a ParallelSequence.
<img width="1483" height="794" alt="examplelinkdecor drawio" src="https://github.com/user-attachments/assets/8be5ffb0-75ad-418c-bbe1-0c71ed979df0" />

#This is a WeightedSelector in which we even find a ConditionalDecorator (much wow, peak bt)
<img width="1183" height="647" alt="exampleweightedandconditional drawio" src="https://github.com/user-attachments/assets/1d7f3b92-2587-47f5-8561-44ad3cd3b44c" />

## Example tree 
<img width="4023" height="973" alt="photo_of_graph drawio" src="https://github.com/user-attachments/assets/a3645edb-70b5-4a76-b4cd-cd60163635f5" />


## Documentation (I try to keep it updated, but yeah)
**[Documentation](./docs.md)**
