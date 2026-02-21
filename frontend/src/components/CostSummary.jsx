import './CostSummary.css';

export default function CostSummary({ cost }) {
  if (!cost) return null;

  const formatCost = (value) => {
    if (value < 0.01) return `$${value.toFixed(4)}`;
    return `$${value.toFixed(2)}`;
  };

  return (
    <div className="cost-summary">
      <div className="cost-header">
        <span className="cost-title">Workflow Cost</span>
        <span className="cost-total">{formatCost(cost.total)}</span>
      </div>
      <div className="cost-breakdown">
        <div className="cost-stages">
          <div className="cost-stage">
            <span className="cost-label">Stage 1</span>
            <span className="cost-value">{formatCost(cost.stage1)}</span>
          </div>
          <div className="cost-stage">
            <span className="cost-label">Stage 2</span>
            <span className="cost-value">{formatCost(cost.stage2)}</span>
          </div>
          <div className="cost-stage">
            <span className="cost-label">Stage 3</span>
            <span className="cost-value">{formatCost(cost.stage3)}</span>
          </div>
          <div className="cost-stage">
            <span className="cost-label">Stage 4</span>
            <span className="cost-value">{formatCost(cost.stage4)}</span>
          </div>
        </div>
        {cost.by_model && Object.keys(cost.by_model).length > 0 && (
          <div className="cost-models">
            <span className="cost-models-title">By Model</span>
            {Object.entries(cost.by_model)
              .sort((a, b) => b[1] - a[1])
              .map(([model, modelCost]) => (
                <div key={model} className="cost-model-row">
                  <span className="cost-model-name">{model}</span>
                  <span className="cost-value">{formatCost(modelCost)}</span>
                </div>
              ))}
          </div>
        )}
      </div>
    </div>
  );
}
