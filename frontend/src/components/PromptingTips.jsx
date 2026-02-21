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
        <div className="tips-content">
          <ul className="tips-list">
            <li><strong>Be specific:</strong> Instead of "tell me about AI", ask "explain how transformer attention mechanisms work"</li>
            <li><strong>Provide context:</strong> Share relevant background so models can tailor their responses</li>
            <li><strong>Specify format:</strong> Request bullet points, step-by-step guides, comparisons, or code examples</li>
            <li><strong>Set scope:</strong> Indicate desired depth — overview vs. deep dive</li>
            <li><strong>Ask for reasoning:</strong> "Explain your reasoning" or "compare pros and cons" yields richer answers</li>
            <li><strong>One topic at a time:</strong> Focused questions get better evaluations from the council</li>
          </ul>

          <div className="tips-section-header">Deliberation Loop Patterns</div>
          <p className="tips-intro">
            You can embed self-orchestrated thinking directly into your prompts. These patterns make models deliberate internally before answering:
          </p>
          <ul className="tips-list">
            <li>
              <strong>Think-then-answer:</strong> Add "Think step by step before answering. First list your key considerations, then provide your final answer." This forces structured internal deliberation.
            </li>
            <li>
              <strong>Devil's advocate:</strong> Ask "First argue for option A, then argue for option B, then evaluate which is stronger and explain your final choice." Models produce more balanced answers when forced to consider both sides.
            </li>
            <li>
              <strong>Draft-critique-revise:</strong> Prompt with "Write a draft answer, then critique your own draft identifying weaknesses, then write an improved final version." The self-critique loop catches errors.
            </li>
            <li>
              <strong>Confidence calibration:</strong> Add "Rate your confidence (low/medium/high) for each claim you make, and explain what would change your mind." This surfaces uncertainty and hedging.
            </li>
            <li>
              <strong>Multi-perspective analysis:</strong> Ask "Analyze this from the perspective of [role A], then [role B], then [role C], and synthesize the key insights." Works well with the council since each model brings a different angle.
            </li>
          </ul>

          <div className="tips-section-header">Using Reasoning Effort</div>
          <p className="tips-intro">
            The Reasoning Effort selector above enables model-native extended thinking (Anthropic's thinking mode, OpenAI's reasoning effort, Google's thinking budget). Use <strong>High</strong> for complex multi-step problems, math, and code generation. Use <strong>Low</strong> for straightforward factual questions to save cost and latency.
          </p>
        </div>
      )}
    </div>
  );
}
