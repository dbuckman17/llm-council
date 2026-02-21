import './ModelSelector.css';

export default function ModelSelector({
  availableModels,
  selectedCouncilModels,
  onCouncilModelsChange,
  chairmanModel,
  onChairmanModelChange,
  disabled,
}) {
  if (!availableModels) return null;

  const allModels = Object.values(availableModels).flat();

  const toggleModel = (modelId) => {
    if (disabled) return;
    if (selectedCouncilModels.includes(modelId)) {
      onCouncilModelsChange(selectedCouncilModels.filter((m) => m !== modelId));
    } else {
      onCouncilModelsChange([...selectedCouncilModels, modelId]);
    }
  };

  return (
    <div className="model-selector">
      <div className="model-selector-header">
        <div className="council-section">
          <label className="section-label">Council Members</label>
          <div className="provider-columns">
            {Object.entries(availableModels).map(([provider, models]) => (
              <div key={provider} className="provider-column">
                <div className="provider-name">{provider}</div>
                {models.map((model) => (
                  <label key={model} className="model-checkbox">
                    <input
                      type="checkbox"
                      checked={selectedCouncilModels.includes(model)}
                      onChange={() => toggleModel(model)}
                      disabled={disabled}
                    />
                    <span className="model-label">{model}</span>
                  </label>
                ))}
              </div>
            ))}
          </div>
        </div>
        <div className="chairman-section">
          <label className="section-label" htmlFor="chairman-select">Chairman</label>
          <select
            id="chairman-select"
            className="chairman-select"
            value={chairmanModel}
            onChange={(e) => onChairmanModelChange(e.target.value)}
            disabled={disabled}
          >
            {allModels.map((model) => (
              <option key={model} value={model}>{model}</option>
            ))}
          </select>
        </div>
      </div>
    </div>
  );
}
