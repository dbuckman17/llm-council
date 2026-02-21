import { useState } from 'react';
import './ConnectorPanel.css';

export default function ConnectorPanel({
  availableConnectors,
  enabledConnectors,
  onEnabledConnectorsChange,
  disabled,
}) {
  const [configs, setConfigs] = useState({});

  const isEnabled = (name) => enabledConnectors.some((c) => c.name === name);

  const toggleConnector = (name) => {
    if (disabled) return;
    if (isEnabled(name)) {
      onEnabledConnectorsChange(enabledConnectors.filter((c) => c.name !== name));
    } else {
      onEnabledConnectorsChange([
        ...enabledConnectors,
        { name, config: configs[name] || {} },
      ]);
    }
  };

  const updateConfig = (connectorName, fieldId, value) => {
    const newConfigs = {
      ...configs,
      [connectorName]: { ...(configs[connectorName] || {}), [fieldId]: value },
    };
    setConfigs(newConfigs);

    // Update the enabled connector's config if it's active
    if (isEnabled(connectorName)) {
      onEnabledConnectorsChange(
        enabledConnectors.map((c) =>
          c.name === connectorName ? { ...c, config: newConfigs[connectorName] } : c
        )
      );
    }
  };

  if (!availableConnectors || availableConnectors.length === 0) return null;

  return (
    <div className="connector-panel">
      <label className="connector-panel-label">Connectors</label>
      <div className="connector-list">
        {availableConnectors.map((conn) => {
          const active = isEnabled(conn.name);
          const schema = conn.config_schema || {};
          const properties = schema.properties || {};
          const required = schema.required || [];

          return (
            <div key={conn.name} className={`connector-item ${active ? 'active' : ''}`}>
              <label className="connector-toggle">
                <input
                  type="checkbox"
                  checked={active}
                  onChange={() => toggleConnector(conn.name)}
                  disabled={disabled}
                />
                <span className="connector-info">
                  <span className="connector-name">{conn.name}</span>
                  <span className="connector-description">{conn.description}</span>
                </span>
              </label>

              {active && Object.keys(properties).length > 0 && (
                <div className="connector-config">
                  {Object.entries(properties).map(([fieldId, fieldSchema]) => (
                    <div key={fieldId} className="connector-field">
                      <label className="connector-field-label">
                        {fieldId}
                        {required.includes(fieldId) && <span className="required">*</span>}
                      </label>
                      {fieldSchema.type === 'integer' ? (
                        <input
                          type="number"
                          className="connector-field-input"
                          value={configs[conn.name]?.[fieldId] ?? fieldSchema.default ?? ''}
                          onChange={(e) => updateConfig(conn.name, fieldId, parseInt(e.target.value) || 0)}
                          placeholder={fieldSchema.description}
                          disabled={disabled}
                        />
                      ) : fieldSchema.type === 'object' ? (
                        <input
                          type="text"
                          className="connector-field-input"
                          value={
                            typeof configs[conn.name]?.[fieldId] === 'object'
                              ? JSON.stringify(configs[conn.name][fieldId])
                              : configs[conn.name]?.[fieldId] ?? ''
                          }
                          onChange={(e) => {
                            try {
                              updateConfig(conn.name, fieldId, JSON.parse(e.target.value));
                            } catch {
                              updateConfig(conn.name, fieldId, e.target.value);
                            }
                          }}
                          placeholder={fieldSchema.description || 'JSON object'}
                          disabled={disabled}
                        />
                      ) : (
                        <input
                          type="text"
                          className="connector-field-input"
                          value={configs[conn.name]?.[fieldId] ?? fieldSchema.default ?? ''}
                          onChange={(e) => updateConfig(conn.name, fieldId, e.target.value)}
                          placeholder={fieldSchema.description}
                          disabled={disabled}
                        />
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
