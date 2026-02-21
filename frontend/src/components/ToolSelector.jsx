import './ToolSelector.css';

export default function ToolSelector({
  availableTools,
  enabledTools,
  onEnabledToolsChange,
  disabled,
}) {
  const toggleTool = (toolName) => {
    if (disabled) return;
    if (enabledTools.includes(toolName)) {
      onEnabledToolsChange(enabledTools.filter((t) => t !== toolName));
    } else {
      onEnabledToolsChange([...enabledTools, toolName]);
    }
  };

  if (!availableTools || availableTools.length === 0) return null;

  return (
    <div className="tool-selector">
      <label className="tool-selector-label">Stage 1 Tools</label>
      <div className="tool-list">
        {availableTools.map((tool) => (
          <label key={tool.name} className="tool-checkbox">
            <input
              type="checkbox"
              checked={enabledTools.includes(tool.name)}
              onChange={() => toggleTool(tool.name)}
              disabled={disabled}
            />
            <span className="tool-info">
              <span className="tool-name">{tool.name}</span>
              <span className="tool-description">{tool.description}</span>
            </span>
          </label>
        ))}
      </div>
    </div>
  );
}
