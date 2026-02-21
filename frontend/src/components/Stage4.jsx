import { useState, useEffect } from 'react';
import ReactMarkdown from 'react-markdown';
import './Stage4.css';

export default function Stage4({ reflection, onRerun, isLoading }) {
  const [editedSystemPrompt, setEditedSystemPrompt] = useState('');
  const [editedQuery, setEditedQuery] = useState('');
  const [provideContext, setProvideContext] = useState(true);

  useEffect(() => {
    if (reflection) {
      setEditedSystemPrompt(reflection.suggested_system_prompt || '');
      setEditedQuery(reflection.suggested_query || '');
    }
  }, [reflection]);

  if (!reflection) {
    return null;
  }

  const handleRerun = () => {
    if (onRerun) {
      onRerun(editedQuery, editedSystemPrompt, provideContext);
    }
  };

  return (
    <div className="stage stage4">
      <h3 className="stage-title">Stage 4: Chairman's Reflection</h3>
      <div className="chairman-label">Chairman: {reflection.model}</div>

      <div className="reflection-section">
        <h4>Critique</h4>
        <div className="markdown-content">
          <ReactMarkdown>{reflection.critique}</ReactMarkdown>
        </div>
      </div>

      {reflection.comparison && (
        <div className="reflection-section">
          <h4>Comparison with Previous Iteration</h4>
          <div className="markdown-content">
            <ReactMarkdown>{reflection.comparison}</ReactMarkdown>
          </div>
        </div>
      )}

      <hr className="suggestions-divider" />

      <div className="suggestion-group">
        <label>Suggested System Prompt</label>
        <textarea
          className="suggestion-textarea"
          value={editedSystemPrompt}
          onChange={(e) => setEditedSystemPrompt(e.target.value)}
          rows={3}
          disabled={isLoading}
        />
      </div>

      <div className="suggestion-group">
        <label>Suggested Query</label>
        <textarea
          className="suggestion-textarea"
          value={editedQuery}
          onChange={(e) => setEditedQuery(e.target.value)}
          rows={3}
          disabled={isLoading}
        />
      </div>

      <label className="context-toggle">
        <input
          type="checkbox"
          checked={provideContext}
          onChange={(e) => setProvideContext(e.target.checked)}
          disabled={isLoading}
        />
        Provide previous context to council members
      </label>

      <button
        className="rerun-button"
        onClick={handleRerun}
        disabled={isLoading || !editedQuery.trim()}
      >
        Re-run Analysis
      </button>
    </div>
  );
}
