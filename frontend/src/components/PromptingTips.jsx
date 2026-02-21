import { useState } from 'react';
import './PromptingTips.css';

export default function PromptingTips() {
  const [isOpen, setIsOpen] = useState(false);

  return (
    <div className="prompting-tips">
      <button
        className="tips-toggle"
        onClick={() => setIsOpen(!isOpen)}
      >
        <span className="tips-arrow">{isOpen ? '\u25BC' : '\u25B6'}</span>
        Prompting Best Practices
      </button>
      {isOpen && (
        <ul className="tips-list">
          <li><strong>Be specific:</strong> Instead of "tell me about AI", ask "explain how transformer attention mechanisms work"</li>
          <li><strong>Provide context:</strong> Share relevant background so models can tailor their responses</li>
          <li><strong>Specify format:</strong> Request bullet points, step-by-step guides, comparisons, or code examples</li>
          <li><strong>Set scope:</strong> Indicate desired depth — overview vs. deep dive</li>
          <li><strong>Ask for reasoning:</strong> "Explain your reasoning" or "compare pros and cons" yields richer answers</li>
          <li><strong>One topic at a time:</strong> Focused questions get better evaluations from the council</li>
        </ul>
      )}
    </div>
  );
}
