# XML to Simba Converter

This tool converts visual behavior trees designed in XML format (e.g., from or draw.io) into an executable Simba 2000 script skeleton. It bridges the gap between visual design and the `WaspLib` behavior tree implementation.
## Features
- **Visual to Code**: Converts diagrammatic nodes (Selectors, Sequences, Actions, Decorators) into valid Simba code compatible with the behavior tree library.
- **Stub Generation**: Automatically generates function stubs for actions and conditions defined in your diagram.
- **Smart Sorting**: Executes nodes in visual left-to-right order.
- **Memory Support**: Enable memory on Sequences and Selectors by using rounded rectangles in your diagram.
- **Parameter Support**: Handles parameterized actions (e.g., `Eat(Food)`) by generating wrapper functions.
- **Decorator Support**: 8 decorator types with parameter support — see below.
- **Weighted Probabilities**: Supports `WeightedSelector` with edge-label weights for probabilistic branching.
- **Auto Boilerplate**: Generates the `TBot` record, `Init()` procedure, and cleanup code automatically.
  
### Running the Tool
Run behavior_tree_wiz.exe or the equivalent python script.

1.  **Source XML**: Select your `.xml` file containing the behavior tree diagram (which uses the given node types in `availablenodes.draw.io.png` or `photo_of_graph.draw.io.png`).
2.  **Output Simba**: Choose where to save the generated `.simba` script.
3.  **Header & Footer**: You can add whatever you want there, the generated tree and functions will appear sandwiched right between the header and footer you put in. Don't forget to have the `TBot.Tree.Tick` in your mainloop (already there in default footer).
4.  **Save as default**: Will create a small file where script was ran to save the default header and footer (also persists your last-used file paths).
5.  **Convert**: Click "Convert & Save".
<img width="799" height="634" alt="image" src="https://github.com/user-attachments/assets/98f9f67a-9e14-4055-a8da-bdc33e02066a" />
    
## Node Symbols Reference

### Getting the Symbols
Download **`availablenodes.draw.io.png`** from this repository and import it into your draw.io canvas (drag & drop or **File → Import → Device**). The image contains all node symbols below that you can copy/paste into your own diagrams, select the wholegroup and click CTRL + D to duplicate it for easy node creation.

### How Node Detection Works

The converter uses a **symbol + group** system for node type detection:

- **Leaf nodes** (Actions and Conditions) can be placed directly on the canvas as standalone shapes. Their type is determined by shape (ellipse = Condition) or label prefix (`Is` = Condition). Everything else defaults to Action.
- **Composite nodes** (Selectors, Sequences, etc.) and **Decorator nodes** must be placed inside **draw.io groups**. The shape's text is the **symbol** (e.g., `?`, `→`, `δS`), and a separate **text label** inside the same group provides the display name.

## Available Nodes at the Moment (import "availablenodes.draw.io.png/" into draw.io to have them)
<img width="1333" height="563" alt="availablenodes drawio" src="https://github.com/user-attachments/assets/58da6b74-aeba-45e6-8f8e-9b3210139a29" />

### Leaves (Actions & Conditions)

> Leaf nodes can be placed directly on the canvas (no group required). Standalone shapes are detected by shape and label text.

| Node Type | Detection Rule | Shape | Example Label | Generated Simba Call |
|-----------|---------------|-------|---------------|---------------------|
| Condition | Ellipse shape | Ellipse | `IsAlive` | `Self.Tree.CreateCondition('IsAlive', @Self.IsAlive)` |
| Action | Default fallback (any rectangle) | Rectangle | `Eat` | `Self.Tree.CreateAction('Eat', @Self.Eat)` |
| Action (with params) | Default fallback | Rectangle | `Eat(Food)` | `Self.Tree.CreateAction('Eat(Food)', @Self.Eat_Food)` |

> **Note**: The ellipse shape check only applies to nodes **not** inside a group. Nodes inside groups (that aren't decorators) are checked for composite symbols and default to Action if no symbol matches.

#### Parameterized Actions

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

You can put any string or expression inside the parentheses — it's passed through verbatim to the wrapper call (e.g., `Log(Starting up)`, `WalkTo(Lumbridge)`, `Eat('Shark')`).

## Creates Conditions & Actions Placeholder Stubs 
<img width="799" height="439" alt="image" src="https://github.com/user-attachments/assets/b6b43709-5eca-4dc9-b45a-b2fe7d906ba7" />

### Composites (Selectors & Sequences)

> **All composites must be inside a draw.io group** (shape with symbol + text label with name).

| Node Type | Symbol | Shape | Example Symbol | Example Display Name | Generated Simba Call |
|-----------|--------|-------|----------------|---------------------|---------------------|
| Selector | `?` | Rectangle (grouped) | `?` | `ChooseOne` | `Self.Tree.CreateSelector('ChooseOne', [...])` |
| Sequence | `→` | Rectangle (grouped) | `→` | `DoAll` | `Self.Tree.CreateSequence('DoAll', [...])` |
| ParallelSelector | `?P` | Rectangle (grouped) | `?P` | `RunAny` | `Self.Tree.CreateParallelSelector('RunAny', [...])` |
| ParallelSequence | `→P` | Rectangle (grouped) | `→P` | `RunAll` | `Self.Tree.CreateParallelSequence('RunAll', [...])` |
| RandomSelector | `??` | Rectangle (grouped) | `??` | `PickRandom` | `Self.Tree.CreateRandomSelector('PickRandom', [...])` |
| WeightedSelector | `?%` | Rectangle (grouped) | `?%` | `WeightedPick` | `Self.Tree.CreateWeightedSelector('WeightedPick', [...], [w1, w2, ...])` |

> **Memory Mode** (Selector and Sequence only): Use **rounded rectangles** (`rounded=1` style) to enable memory on Selector and Sequence nodes. This appends `, True` to the generated call (e.g., `Self.Tree.CreateSelector('ChooseOne', [...], True)`). Memory mode is **not** supported for ParallelSelector, ParallelSequence, RandomSelector, or WeightedSelector.

#### WeightedSelector — Specifying Weights

Weights are specified as **labels on the edges** connecting the WeightedSelector to its children. For example, if a WeightedSelector has three children with weights 0.7, 0.11, and 0.19, set those numbers as the text on each connecting edge.

The converter extracts the first numeric value from each edge label. You can use plain numbers (`0.7`) or percentages (`70%`).

#This is a WeightedSelector in which we even find a ConditionalDecorator (much wow, peak bt)
<img width="1183" height="647" alt="exampleweightedandconditional drawio" src="https://github.com/user-attachments/assets/1d7f3b92-2587-47f5-8561-44ad3cd3b44c" />

## Generates the whole behavior tree automatically
<img width="703" height="746" alt="image" src="https://github.com/user-attachments/assets/2824b72c-ba53-4288-b5d8-224c0abae0d0" />

### Decorators

Decorators are **diamond (rhombus) shapes** inside a draw.io **group**. The diamond's text is a delta symbol that determines the type. The group's text label provides the display name. Parameters go in parentheses after the name.

#### Supported Decorators

| Symbol | Type | Parameter | Example Label | Generated Simba Call |
|--------|------|-----------|---------------|---------------------|
| `δS` | ForceSuccess | None | `AlwaysWin` | `Self.Tree.CreateForceSuccess('AlwaysWin', <child>)` |
| `δF` | ForceFailure | None | `AlwaysFail` | `Self.Tree.CreateForceFailure('AlwaysFail', <child>)` |
| `δRt` | Retry | `max_retries` (int) | `Retry(5)` | `Self.Tree.CreateRetry('Retry', <child>, 5)` |
| `δCd` | Cooldown | `duration_ms` (int) | `Cooldown(3000)` | `Self.Tree.CreateCooldown('Cooldown', <child>, 3000)` |
| `δT` | Timeout | `duration_ms` (int) | `Timeout(5000)` | `Self.Tree.CreateTimeout('Timeout', <child>, 5000)` |
| `δRp` | Repeater | `count` (int) | `Repeat(3)` | `Self.Tree.CreateRepeater('Repeat', <child>, 3)` |
| `δIf` | Conditional | `condition_ref` (string) | `IfGuard(IsReady)` | `Self.Tree.CreateConditional('IfGuard', <child>, @IsReady)` |
| `δL` | Link | None | `GoToNode` | `Self.Tree.CreateLink('GoToNode', <child>)` |

#### Decorator Parameter Details

- **Retry / Cooldown / Timeout / Repeater**: Pass an integer in parentheses (e.g., `Retry(5)`, `Cooldown(3000)`). You can also use any Simba expression that returns an integer, such as `Cooldown(Random(1000, 2000))` — if the value is not a plain integer, it is passed through verbatim as a raw expression.
- **Conditional**: Pass a method reference (e.g., `IfGuard(IsReady)` or `IfGuard(@Self.CheckReady)`). The `@` prefix is auto-added if omitted.
- **ForceSuccess / ForceFailure**: No parameters. Supports **memory mode** via rounded rectangles (appends `, True`). Link does not support memory mode.

## Creates wrappers and forward declarations for link and conditional nodes
<img width="469" height="227" alt="image" src="https://github.com/user-attachments/assets/0afc6990-40ce-4e6a-a541-9bd814810050" /> 

<img width="477" height="120" alt="image" src="https://github.com/user-attachments/assets/bd3a092f-50d4-4f4d-bcda-bf1a8c68c84e" />

### Root

The root node is identified by one of:
- The only node in the diagram that is not the target of any edge (i.e., has no parent in the tree).
- A grouped `?` node whose display label contains `Root`.
- Any node with the exact label `RootNode`.

In generated code, the root simply delegates to its first child. If the root has multiple children, they are automatically wrapped in a Selector.

### Generated Output Structure

The converter generates a complete Simba script with the following structure:

```
[Your Header]

type
  TBot = record
    MainForm: TScriptForm;
    Tree: TBehaviorTree;
    MainConfig: TConfigJSON;
  end;

// Action and Condition stubs
function TBot.Eat(): EBTStatus;
begin
  WriteLn('Action : Eat');
  Result := EBTStatus.Success;
end;

// Wrapper functions (for parameterized actions)
function TBot.Eat_Food(): EBTStatus;
begin
  Result := Self.Eat(Food);
end;

procedure TBot.Init();
begin
  Self.Tree.Setup('MyBot');
  // Generated Tree
  Self.Tree.Root := Self.Tree.Selector('MyRoot', [
    ...
  ]);
  Self.Tree.PrintStructure();
  AddOnTerminate(@Self.Tree.Free);
end;

[Your Footer]
```

The `TBot` record, all stubs, wrappers, and the `Init()` procedure are auto-generated. Your header and footer wrap around this generated code.

## Example draw.io Behavior Tree snippets
#This is a LinkDecorator working within a ParallelSequence.
<img width="1483" height="794" alt="examplelinkdecor drawio" src="https://github.com/user-attachments/assets/8be5ffb0-75ad-418c-bbe1-0c71ed979df0" />


## Example tree 
<img width="4023" height="973" alt="photo_of_graph drawio" src="https://github.com/user-attachments/assets/a3645edb-70b5-4a76-b4cd-cd60163635f5" />


## Documentation (I try to keep it updated, but yeah)
**[Documentation](./docs.md)**
