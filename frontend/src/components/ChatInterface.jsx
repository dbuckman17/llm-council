import { useState, useEffect, useRef } from 'react';
import ReactMarkdown from 'react-markdown';
import Stage1 from './Stage1';
import Stage2 from './Stage2';
import Stage3 from './Stage3';
import Stage4 from './Stage4';
import CostSummary from './CostSummary';
import ModelSelector from './ModelSelector';
import TemplateSelector from './TemplateSelector';
import FileUpload from './FileUpload';
import ToolSelector from './ToolSelector';
import ConnectorPanel from './ConnectorPanel';
import PromptingTips from './PromptingTips';
import { api } from '../api';
import './ChatInterface.css';

export default function ChatInterface({
  conversation,
  onSendMessage,
  onRerun,
  isLoading,
  availableModels,
  selectedCouncilModels,
  onCouncilModelsChange,
  chairmanModel,
  onChairmanModelChange,
  systemPrompt,
  onSystemPromptChange,
  templates,
  conversationId,
  conversationFiles,
  onFilesChange,
  availableTools,
  enabledTools,
  onEnabledToolsChange,
  availableConnectors,
  enabledConnectors,
  onEnabledConnectorsChange,
}) {
  const [input, setInput] = useState('');
  const [isOptimizing, setIsOptimizing] = useState(false);
  const [optimizeModel, setOptimizeModel] = useState('');
  const messagesEndRef = useRef(null);

  // Set default optimize model when available models load
  useEffect(() => {
    if (availableModels && !optimizeModel) {
      const allModels = Object.values(availableModels).flat();
      setOptimizeModel(allModels[0] || '');
    }
  }, [availableModels, optimizeModel]);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [conversation]);

  const handleSubmit = (e) => {
    e.preventDefault();
    if (input.trim() && !isLoading) {
      onSendMessage(input);
      setInput('');
    }
  };

  const handleKeyDown = (e) => {
    // Submit on Enter (without Shift)
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  };

  const handleOptimize = async () => {
    if (!input.trim() || isOptimizing) return;
    setIsOptimizing(true);
    try {
      const result = await api.optimizePrompt(input, optimizeModel);
      setInput(result.optimized_prompt);
    } catch (error) {
      console.error('Failed to optimize prompt:', error);
    } finally {
      setIsOptimizing(false);
    }
  };

  const allModels = availableModels ? Object.values(availableModels).flat() : [];

  if (!conversation) {
    return (
      <div className="chat-interface">
        <div className="empty-state">
          <h2>Welcome to LLM Council</h2>
          <p>Create a new conversation to get started</p>
        </div>
      </div>
    );
  }

  return (
    <div className="chat-interface">
      <div className="messages-container">
        {conversation.messages.length === 0 ? (
          <div className="empty-state">
            <h2>Start a conversation</h2>
            <p>Ask a question to consult the LLM Council</p>
          </div>
        ) : (
          conversation.messages.map((msg, index) => (
            <div key={index} className="message-group">
              {msg.role === 'user' ? (
                <div className="user-message">
                  <div className="message-label">You</div>
                  <div className="message-content">
                    <div className="markdown-content">
                      <ReactMarkdown>{msg.content}</ReactMarkdown>
                    </div>
                  </div>
                </div>
              ) : (
                <div className="assistant-message">
                  <div className="message-label">LLM Council</div>

                  {/* Stage 1 */}
                  {msg.loading?.stage1 && (
                    <div className="stage-loading">
                      <div className="spinner"></div>
                      <span>Running Stage 1: Collecting individual responses...</span>
                    </div>
                  )}
                  {msg.stage1 && <Stage1 responses={msg.stage1} />}

                  {/* Stage 2 */}
                  {msg.loading?.stage2 && (
                    <div className="stage-loading">
                      <div className="spinner"></div>
                      <span>Running Stage 2: Peer rankings...</span>
                    </div>
                  )}
                  {msg.stage2 && (
                    <Stage2
                      rankings={msg.stage2}
                      labelToModel={msg.metadata?.label_to_model}
                      aggregateRankings={msg.metadata?.aggregate_rankings}
                    />
                  )}

                  {/* Stage 3 */}
                  {msg.loading?.stage3 && (
                    <div className="stage-loading">
                      <div className="spinner"></div>
                      <span>Running Stage 3: Final synthesis...</span>
                    </div>
                  )}
                  {msg.stage3 && <Stage3 finalResponse={msg.stage3} />}

                  {/* Stage 4 */}
                  {msg.loading?.stage4 && (
                    <div className="stage-loading">
                      <div className="spinner"></div>
                      <span>Running Stage 4: Chairman's self-reflection...</span>
                    </div>
                  )}
                  {msg.stage4 && (
                    <Stage4
                      reflection={msg.stage4}
                      onRerun={onRerun}
                      isLoading={isLoading}
                    />
                  )}

                  {/* Cost Summary */}
                  {msg.cost_summary && (
                    <CostSummary cost={msg.cost_summary} />
                  )}
                </div>
              )}
            </div>
          ))
        )}

        {isLoading && (
          <div className="loading-indicator">
            <div className="spinner"></div>
            <span>Consulting the council...</span>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {conversation.messages.length === 0 && (
        <div className="input-area">
          <ModelSelector
            availableModels={availableModels}
            selectedCouncilModels={selectedCouncilModels}
            onCouncilModelsChange={onCouncilModelsChange}
            chairmanModel={chairmanModel}
            onChairmanModelChange={onChairmanModelChange}
            disabled={isLoading}
          />

          <TemplateSelector
            templates={templates}
            systemPrompt={systemPrompt}
            onSystemPromptChange={onSystemPromptChange}
            disabled={isLoading}
          />

          <textarea
            className="system-prompt-input"
            placeholder="System prompt (optional) — e.g., 'You are an expert in distributed systems...'"
            value={systemPrompt}
            onChange={(e) => onSystemPromptChange(e.target.value)}
            disabled={isLoading}
            rows={2}
          />

          {availableTools.length > 0 && (
            <ToolSelector
              availableTools={availableTools}
              enabledTools={enabledTools}
              onEnabledToolsChange={onEnabledToolsChange}
              disabled={isLoading}
            />
          )}

          {availableConnectors.length > 0 && (
            <ConnectorPanel
              availableConnectors={availableConnectors}
              enabledConnectors={enabledConnectors}
              onEnabledConnectorsChange={onEnabledConnectorsChange}
              disabled={isLoading}
            />
          )}

          {conversationId && (
            <FileUpload
              conversationId={conversationId}
              files={conversationFiles || []}
              onFilesChange={onFilesChange}
              disabled={isLoading}
              api={api}
            />
          )}

          <form className="input-form" onSubmit={handleSubmit}>
            <textarea
              className="message-input"
              placeholder="Ask your question... (Shift+Enter for new line, Enter to send)"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              disabled={isLoading}
              rows={3}
            />
          </form>

          <div className="input-actions">
            <div className="optimize-group">
              <button
                className="optimize-button"
                onClick={handleOptimize}
                disabled={!input.trim() || isOptimizing || isLoading}
              >
                {isOptimizing ? 'Optimizing...' : 'Optimize Prompt'}
              </button>
              <select
                className="optimize-model-select"
                value={optimizeModel}
                onChange={(e) => setOptimizeModel(e.target.value)}
                disabled={isOptimizing || isLoading}
              >
                {allModels.map((model) => (
                  <option key={model} value={model}>{model}</option>
                ))}
              </select>
            </div>
            <button
              type="button"
              className="send-button"
              disabled={!input.trim() || isLoading || selectedCouncilModels.length === 0}
              onClick={handleSubmit}
            >
              Send
            </button>
          </div>

          <PromptingTips />
        </div>
      )}
    </div>
  );
}
