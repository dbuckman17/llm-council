import { useState } from 'react';
import ReactMarkdown from 'react-markdown';
import './Stage1.css';

export default function Stage1({ responses }) {
  const [activeTab, setActiveTab] = useState(0);
  const [toolCallsExpanded, setToolCallsExpanded] = useState(false);

  if (!responses || responses.length === 0) {
    return null;
  }

  const activeResponse = responses[activeTab];
  const toolCalls = activeResponse?.tool_calls;

  return (
    <div className="stage stage1">
      <h3 className="stage-title">Stage 1: Individual Responses</h3>

      <div className="tabs">
        {responses.map((resp, index) => (
          <button
            key={index}
            className={`tab ${activeTab === index ? 'active' : ''}`}
            onClick={() => {
              setActiveTab(index);
              setToolCallsExpanded(false);
            }}
          >
            {resp.model}
          </button>
        ))}
      </div>

      <div className="tab-content">
        <div className="model-name">{activeResponse.model}</div>

        {toolCalls && toolCalls.length > 0 && (
          <div className="tool-calls-section">
            <button
              className="tool-calls-toggle"
              onClick={() => setToolCallsExpanded(!toolCallsExpanded)}
            >
              Tool Calls ({toolCalls.length}) {toolCallsExpanded ? '\u25B2' : '\u25BC'}
            </button>
            {toolCallsExpanded && (
              <div className="tool-calls-list">
                {toolCalls.map((tc, i) => (
                  <div key={i} className="tool-call-item">
                    <div className="tool-call-header">
                      <span className="tool-call-name">{tc.tool}</span>
                      <span className="tool-call-args">
                        {JSON.stringify(tc.args)}
                      </span>
                    </div>
                    <div className="tool-call-result">
                      <pre>{tc.result}</pre>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        <div className="response-text markdown-content">
          <ReactMarkdown>{activeResponse.response}</ReactMarkdown>
        </div>
      </div>
    </div>
  );
}
