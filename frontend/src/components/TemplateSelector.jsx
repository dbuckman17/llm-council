import { useState, useEffect } from 'react';
import './TemplateSelector.css';

export default function TemplateSelector({
  templates,
  systemPrompt,
  onSystemPromptChange,
  disabled,
}) {
  const [selectedTemplateId, setSelectedTemplateId] = useState('');
  const [fieldValues, setFieldValues] = useState({});

  const selectedTemplate = templates?.find((t) => t.id === selectedTemplateId);

  const handleTemplateChange = (templateId) => {
    setSelectedTemplateId(templateId);

    if (!templateId) {
      // "None" selected — clear auto-populated prompt
      onSystemPromptChange('');
      setFieldValues({});
      return;
    }

    const template = templates.find((t) => t.id === templateId);
    if (!template) return;

    // Build default field values
    const defaults = {};
    for (const field of template.configurable_fields || []) {
      defaults[field.id] = field.default || '';
    }
    setFieldValues(defaults);

    // Render the prompt with defaults
    onSystemPromptChange(renderPrompt(template.system_prompt, defaults));
  };

  const handleFieldChange = (fieldId, value) => {
    const newValues = { ...fieldValues, [fieldId]: value };
    setFieldValues(newValues);

    if (selectedTemplate) {
      onSystemPromptChange(renderPrompt(selectedTemplate.system_prompt, newValues));
    }
  };

  return (
    <div className="template-selector">
      <label className="template-label">Skill Template</label>
      <div className="template-row">
        <select
          className="template-dropdown"
          value={selectedTemplateId}
          onChange={(e) => handleTemplateChange(e.target.value)}
          disabled={disabled}
        >
          <option value="">None</option>
          {templates?.map((t) => (
            <option key={t.id} value={t.id}>
              {t.name}
            </option>
          ))}
        </select>
        {selectedTemplate && selectedTemplate.description && (
          <span className="template-description">{selectedTemplate.description}</span>
        )}
      </div>

      {selectedTemplate && selectedTemplate.configurable_fields?.length > 0 && (
        <div className="template-fields">
          {selectedTemplate.configurable_fields.map((field) => (
            <div key={field.id} className="template-field">
              <label className="field-label">{field.label}</label>
              {field.type === 'select' ? (
                <select
                  className="field-select"
                  value={fieldValues[field.id] || field.default || ''}
                  onChange={(e) => handleFieldChange(field.id, e.target.value)}
                  disabled={disabled}
                >
                  {field.options?.map((opt) => (
                    <option key={opt} value={opt}>
                      {opt}
                    </option>
                  ))}
                </select>
              ) : (
                <input
                  type="text"
                  className="field-input"
                  value={fieldValues[field.id] || ''}
                  onChange={(e) => handleFieldChange(field.id, e.target.value)}
                  placeholder={field.default || ''}
                  disabled={disabled}
                />
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function renderPrompt(template, values) {
  if (!template) return '';
  return template.replace(/\{\{(\w+)\}\}/g, (match, key) => {
    return values[key] !== undefined ? values[key] : match;
  });
}
