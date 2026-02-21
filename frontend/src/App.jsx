import { useState, useEffect } from 'react';
import Sidebar from './components/Sidebar';
import ChatInterface from './components/ChatInterface';
import { api } from './api';
import './App.css';

function App() {
  const [conversations, setConversations] = useState([]);
  const [currentConversationId, setCurrentConversationId] = useState(null);
  const [currentConversation, setCurrentConversation] = useState(null);
  const [isLoading, setIsLoading] = useState(false);

  // Model selection state
  const [availableModels, setAvailableModels] = useState(null);
  const [selectedCouncilModels, setSelectedCouncilModels] = useState([]);
  const [chairmanModel, setChairmanModel] = useState('');
  const [systemPrompt, setSystemPrompt] = useState('');

  // Templates state
  const [templates, setTemplates] = useState([]);

  // Files state
  const [conversationFiles, setConversationFiles] = useState([]);

  // Tools state
  const [availableTools, setAvailableTools] = useState([]);
  const [enabledTools, setEnabledTools] = useState([]);

  // Connectors state
  const [availableConnectors, setAvailableConnectors] = useState([]);
  const [enabledConnectors, setEnabledConnectors] = useState([]);

  // Reasoning effort state
  const [reasoningEffort, setReasoningEffort] = useState('off');

  // Load conversations and models on mount
  useEffect(() => {
    loadConversations();
    loadModels();
    loadTemplates();
    loadTools();
    loadConnectors();
  }, []);

  // Load conversation details and files when selected
  useEffect(() => {
    if (currentConversationId) {
      loadConversation(currentConversationId);
      loadFiles(currentConversationId);
    } else {
      setConversationFiles([]);
    }
  }, [currentConversationId]);

  const loadConversations = async () => {
    try {
      const convs = await api.listConversations();
      setConversations(convs);
    } catch (error) {
      console.error('Failed to load conversations:', error);
    }
  };

  const loadConversation = async (id) => {
    try {
      const conv = await api.getConversation(id);
      setCurrentConversation(conv);
    } catch (error) {
      console.error('Failed to load conversation:', error);
    }
  };

  const loadFiles = async (convId) => {
    try {
      const data = await api.listFiles(convId);
      setConversationFiles(data);
    } catch (error) {
      console.error('Failed to load files:', error);
      setConversationFiles([]);
    }
  };

  const loadTools = async () => {
    try {
      const data = await api.getTools();
      setAvailableTools(data);
    } catch (error) {
      console.error('Failed to load tools:', error);
    }
  };

  const loadConnectors = async () => {
    try {
      const data = await api.getConnectors();
      setAvailableConnectors(data);
    } catch (error) {
      console.error('Failed to load connectors:', error);
    }
  };

  const loadTemplates = async () => {
    try {
      const data = await api.getTemplates();
      setTemplates(data);
    } catch (error) {
      console.error('Failed to load templates:', error);
    }
  };

  const loadModels = async () => {
    try {
      const models = await api.getModels();
      setAvailableModels(models);

      // Set sensible defaults: one model per provider
      const defaults = [];
      for (const providerModels of Object.values(models)) {
        if (providerModels.length > 0) {
          defaults.push(providerModels[0]);
        }
      }
      setSelectedCouncilModels(defaults);

      // Default chairman: first Google model if available, otherwise first model
      const allModels = Object.values(models).flat();
      const googleModels = models['Google'] || [];
      setChairmanModel(googleModels[0] || allModels[0] || '');
    } catch (error) {
      console.error('Failed to load models:', error);
    }
  };

  const handleNewConversation = async () => {
    try {
      const newConv = await api.createConversation();
      setConversations([
        { id: newConv.id, created_at: newConv.created_at, title: 'New Conversation', message_count: 0 },
        ...conversations,
      ]);
      setCurrentConversationId(newConv.id);
    } catch (error) {
      console.error('Failed to create conversation:', error);
    }
  };

  const handleSelectConversation = (id) => {
    setCurrentConversationId(id);
  };

  const handleSendMessage = async (content) => {
    if (!currentConversationId) return;

    setIsLoading(true);
    try {
      // Optimistically add user message to UI
      const userMessage = { role: 'user', content };
      setCurrentConversation((prev) => ({
        ...prev,
        messages: [...prev.messages, userMessage],
      }));

      // Create a partial assistant message that will be updated progressively
      const assistantMessage = {
        role: 'assistant',
        stage1: null,
        stage2: null,
        stage3: null,
        stage4: null,
        metadata: null,
        loading: {
          stage1: false,
          stage2: false,
          stage3: false,
          stage4: false,
        },
      };

      // Add the partial assistant message
      setCurrentConversation((prev) => ({
        ...prev,
        messages: [...prev.messages, assistantMessage],
      }));

      // Send message with streaming, including model selections
      await api.sendMessageStream(
        currentConversationId,
        content,
        selectedCouncilModels,
        chairmanModel,
        systemPrompt || null,
        (eventType, event) => {
          switch (eventType) {
            case 'stage1_start':
              setCurrentConversation((prev) => {
                const messages = [...prev.messages];
                const lastMsg = messages[messages.length - 1];
                lastMsg.loading.stage1 = true;
                return { ...prev, messages };
              });
              break;

            case 'stage1_complete':
              setCurrentConversation((prev) => {
                const messages = [...prev.messages];
                const lastMsg = messages[messages.length - 1];
                lastMsg.stage1 = event.data;
                lastMsg.loading.stage1 = false;
                return { ...prev, messages };
              });
              break;

            case 'stage2_start':
              setCurrentConversation((prev) => {
                const messages = [...prev.messages];
                const lastMsg = messages[messages.length - 1];
                lastMsg.loading.stage2 = true;
                return { ...prev, messages };
              });
              break;

            case 'stage2_complete':
              setCurrentConversation((prev) => {
                const messages = [...prev.messages];
                const lastMsg = messages[messages.length - 1];
                lastMsg.stage2 = event.data;
                lastMsg.metadata = event.metadata;
                lastMsg.loading.stage2 = false;
                return { ...prev, messages };
              });
              break;

            case 'stage3_start':
              setCurrentConversation((prev) => {
                const messages = [...prev.messages];
                const lastMsg = messages[messages.length - 1];
                lastMsg.loading.stage3 = true;
                return { ...prev, messages };
              });
              break;

            case 'stage3_complete':
              setCurrentConversation((prev) => {
                const messages = [...prev.messages];
                const lastMsg = messages[messages.length - 1];
                lastMsg.stage3 = event.data;
                lastMsg.loading.stage3 = false;
                return { ...prev, messages };
              });
              break;

            case 'stage4_start':
              setCurrentConversation((prev) => {
                const messages = [...prev.messages];
                const lastMsg = messages[messages.length - 1];
                lastMsg.loading.stage4 = true;
                return { ...prev, messages };
              });
              break;

            case 'stage4_complete':
              setCurrentConversation((prev) => {
                const messages = [...prev.messages];
                const lastMsg = messages[messages.length - 1];
                lastMsg.stage4 = event.data;
                lastMsg.loading.stage4 = false;
                return { ...prev, messages };
              });
              break;

            case 'cost_summary':
              setCurrentConversation((prev) => {
                const messages = [...prev.messages];
                const lastMsg = messages[messages.length - 1];
                lastMsg.cost_summary = event.data;
                return { ...prev, messages };
              });
              break;

            case 'title_complete':
              // Reload conversations to get updated title
              loadConversations();
              break;

            case 'complete':
              // Stream complete, reload conversations list
              loadConversations();
              setIsLoading(false);
              break;

            case 'error':
              console.error('Stream error:', event.message);
              setIsLoading(false);
              break;

            default:
              console.log('Unknown event type:', eventType);
          }
        },
        null,
        false,
        enabledTools.length > 0 ? enabledTools : null,
        enabledConnectors.length > 0 ? enabledConnectors : null,
        reasoningEffort !== 'off' ? reasoningEffort : null,
      );
    } catch (error) {
      console.error('Failed to send message:', error);
      // Remove optimistic messages on error
      setCurrentConversation((prev) => ({
        ...prev,
        messages: prev.messages.slice(0, -2),
      }));
      setIsLoading(false);
    }
  };

  const handleRerun = async (editedQuery, editedSystemPrompt, provideContext) => {
    if (!currentConversationId || !currentConversation) return;

    // Find the last assistant message to build previousIteration
    const messages = currentConversation.messages;
    const lastAssistant = [...messages].reverse().find((m) => m.role === 'assistant');
    const lastUser = [...messages].reverse().find((m) => m.role === 'user');

    if (!lastAssistant || !lastUser) return;

    const previousIteration = {
      query: lastUser.content,
      system_prompt: systemPrompt || null,
      stage3_response: lastAssistant.stage3?.response || '',
      critique: lastAssistant.stage4?.critique || '',
    };

    // Update system prompt state to the edited version
    setSystemPrompt(editedSystemPrompt || '');

    setIsLoading(true);
    try {
      // Optimistically add new user message
      const userMessage = { role: 'user', content: editedQuery };
      setCurrentConversation((prev) => ({
        ...prev,
        messages: [...prev.messages, userMessage],
      }));

      // Create partial assistant message
      const assistantMessage = {
        role: 'assistant',
        stage1: null,
        stage2: null,
        stage3: null,
        stage4: null,
        metadata: null,
        loading: {
          stage1: false,
          stage2: false,
          stage3: false,
          stage4: false,
        },
      };

      setCurrentConversation((prev) => ({
        ...prev,
        messages: [...prev.messages, assistantMessage],
      }));

      await api.sendMessageStream(
        currentConversationId,
        editedQuery,
        selectedCouncilModels,
        chairmanModel,
        editedSystemPrompt || null,
        (eventType, event) => {
          switch (eventType) {
            case 'stage1_start':
              setCurrentConversation((prev) => {
                const msgs = [...prev.messages];
                msgs[msgs.length - 1].loading.stage1 = true;
                return { ...prev, messages: msgs };
              });
              break;
            case 'stage1_complete':
              setCurrentConversation((prev) => {
                const msgs = [...prev.messages];
                const last = msgs[msgs.length - 1];
                last.stage1 = event.data;
                last.loading.stage1 = false;
                return { ...prev, messages: msgs };
              });
              break;
            case 'stage2_start':
              setCurrentConversation((prev) => {
                const msgs = [...prev.messages];
                msgs[msgs.length - 1].loading.stage2 = true;
                return { ...prev, messages: msgs };
              });
              break;
            case 'stage2_complete':
              setCurrentConversation((prev) => {
                const msgs = [...prev.messages];
                const last = msgs[msgs.length - 1];
                last.stage2 = event.data;
                last.metadata = event.metadata;
                last.loading.stage2 = false;
                return { ...prev, messages: msgs };
              });
              break;
            case 'stage3_start':
              setCurrentConversation((prev) => {
                const msgs = [...prev.messages];
                msgs[msgs.length - 1].loading.stage3 = true;
                return { ...prev, messages: msgs };
              });
              break;
            case 'stage3_complete':
              setCurrentConversation((prev) => {
                const msgs = [...prev.messages];
                const last = msgs[msgs.length - 1];
                last.stage3 = event.data;
                last.loading.stage3 = false;
                return { ...prev, messages: msgs };
              });
              break;
            case 'stage4_start':
              setCurrentConversation((prev) => {
                const msgs = [...prev.messages];
                msgs[msgs.length - 1].loading.stage4 = true;
                return { ...prev, messages: msgs };
              });
              break;
            case 'stage4_complete':
              setCurrentConversation((prev) => {
                const msgs = [...prev.messages];
                const last = msgs[msgs.length - 1];
                last.stage4 = event.data;
                last.loading.stage4 = false;
                return { ...prev, messages: msgs };
              });
              break;
            case 'cost_summary':
              setCurrentConversation((prev) => {
                const msgs = [...prev.messages];
                msgs[msgs.length - 1].cost_summary = event.data;
                return { ...prev, messages: msgs };
              });
              break;
            case 'title_complete':
              loadConversations();
              break;
            case 'complete':
              loadConversations();
              setIsLoading(false);
              break;
            case 'error':
              console.error('Stream error:', event.message);
              setIsLoading(false);
              break;
            default:
              console.log('Unknown event type:', eventType);
          }
        },
        previousIteration,
        provideContext,
        enabledTools.length > 0 ? enabledTools : null,
        enabledConnectors.length > 0 ? enabledConnectors : null,
        reasoningEffort !== 'off' ? reasoningEffort : null,
      );
    } catch (error) {
      console.error('Failed to re-run analysis:', error);
      setCurrentConversation((prev) => ({
        ...prev,
        messages: prev.messages.slice(0, -2),
      }));
      setIsLoading(false);
    }
  };

  return (
    <div className="app">
      <Sidebar
        conversations={conversations}
        currentConversationId={currentConversationId}
        onSelectConversation={handleSelectConversation}
        onNewConversation={handleNewConversation}
      />
      <ChatInterface
        conversation={currentConversation}
        onSendMessage={handleSendMessage}
        onRerun={handleRerun}
        isLoading={isLoading}
        availableModels={availableModels}
        selectedCouncilModels={selectedCouncilModels}
        onCouncilModelsChange={setSelectedCouncilModels}
        chairmanModel={chairmanModel}
        onChairmanModelChange={setChairmanModel}
        systemPrompt={systemPrompt}
        onSystemPromptChange={setSystemPrompt}
        templates={templates}
        conversationId={currentConversationId}
        conversationFiles={conversationFiles}
        onFilesChange={setConversationFiles}
        availableTools={availableTools}
        enabledTools={enabledTools}
        onEnabledToolsChange={setEnabledTools}
        availableConnectors={availableConnectors}
        enabledConnectors={enabledConnectors}
        onEnabledConnectorsChange={setEnabledConnectors}
        reasoningEffort={reasoningEffort}
        onReasoningEffortChange={setReasoningEffort}
      />
    </div>
  );
}

export default App;
