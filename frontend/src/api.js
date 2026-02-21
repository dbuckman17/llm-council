/**
 * API client for the LLM Council backend.
 */

const API_BASE = import.meta.env.VITE_API_BASE ?? 'http://localhost:8001';

export const api = {
  /**
   * List all conversations.
   */
  async listConversations() {
    const response = await fetch(`${API_BASE}/api/conversations`);
    if (!response.ok) {
      throw new Error('Failed to list conversations');
    }
    return response.json();
  },

  /**
   * Create a new conversation.
   */
  async createConversation() {
    const response = await fetch(`${API_BASE}/api/conversations`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({}),
    });
    if (!response.ok) {
      throw new Error('Failed to create conversation');
    }
    return response.json();
  },

  /**
   * Get a specific conversation.
   */
  async getConversation(conversationId) {
    const response = await fetch(
      `${API_BASE}/api/conversations/${conversationId}`
    );
    if (!response.ok) {
      throw new Error('Failed to get conversation');
    }
    return response.json();
  },

  /**
   * Fetch available system prompt templates.
   */
  async getTemplates() {
    const response = await fetch(`${API_BASE}/api/templates`);
    if (!response.ok) {
      throw new Error('Failed to fetch templates');
    }
    return response.json();
  },

  /**
   * Fetch available models organized by provider.
   */
  async getModels() {
    const response = await fetch(`${API_BASE}/api/models`);
    if (!response.ok) {
      throw new Error('Failed to fetch models');
    }
    return response.json();
  },

  /**
   * Optimize a prompt using a selected model.
   */
  async optimizePrompt(prompt, model) {
    const response = await fetch(`${API_BASE}/api/optimize-prompt`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ prompt, model }),
    });
    if (!response.ok) {
      throw new Error('Failed to optimize prompt');
    }
    return response.json();
  },

  /**
   * Upload files to a conversation.
   */
  async uploadFiles(conversationId, fileList) {
    const formData = new FormData();
    for (const file of fileList) {
      formData.append('files', file);
    }
    const response = await fetch(
      `${API_BASE}/api/conversations/${conversationId}/files`,
      { method: 'POST', body: formData }
    );
    if (!response.ok) {
      throw new Error('Failed to upload files');
    }
    return response.json();
  },

  /**
   * List files for a conversation.
   */
  async listFiles(conversationId) {
    const response = await fetch(
      `${API_BASE}/api/conversations/${conversationId}/files`
    );
    if (!response.ok) {
      throw new Error('Failed to list files');
    }
    return response.json();
  },

  /**
   * Delete a file from a conversation.
   */
  async deleteFile(conversationId, fileId) {
    const response = await fetch(
      `${API_BASE}/api/conversations/${conversationId}/files/${fileId}`,
      { method: 'DELETE' }
    );
    if (!response.ok) {
      throw new Error('Failed to delete file');
    }
    return response.json();
  },

  /**
   * Fetch available tools.
   */
  async getTools() {
    const response = await fetch(`${API_BASE}/api/tools`);
    if (!response.ok) {
      throw new Error('Failed to fetch tools');
    }
    return response.json();
  },

  /**
   * Fetch available connectors.
   */
  async getConnectors() {
    const response = await fetch(`${API_BASE}/api/connectors`);
    if (!response.ok) {
      throw new Error('Failed to fetch connectors');
    }
    return response.json();
  },

  /**
   * Send a message in a conversation.
   */
  async sendMessage(conversationId, content, councilModels, chairmanModel, systemPrompt) {
    const response = await fetch(
      `${API_BASE}/api/conversations/${conversationId}/message`,
      {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          content,
          council_models: councilModels,
          chairman_model: chairmanModel,
          system_prompt: systemPrompt || null,
        }),
      }
    );
    if (!response.ok) {
      throw new Error('Failed to send message');
    }
    return response.json();
  },

  /**
   * Send a message and receive streaming updates.
   * @param {string} conversationId - The conversation ID
   * @param {string} content - The message content
   * @param {string[]} councilModels - Selected council model IDs
   * @param {string} chairmanModel - Selected chairman model ID
   * @param {string|null} systemPrompt - Optional system prompt
   * @param {function} onEvent - Callback function for each event: (eventType, data) => void
   * @returns {Promise<void>}
   */
  async sendMessageStream(conversationId, content, councilModels, chairmanModel, systemPrompt, onEvent, previousIteration = null, provideContextToCouncil = false, enabledTools = null, enabledConnectors = null) {
    const response = await fetch(
      `${API_BASE}/api/conversations/${conversationId}/message/stream`,
      {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          content,
          council_models: councilModels,
          chairman_model: chairmanModel,
          system_prompt: systemPrompt || null,
          previous_iteration: previousIteration,
          provide_context_to_council: provideContextToCouncil,
          enabled_tools: enabledTools,
          enabled_connectors: enabledConnectors,
        }),
      }
    );

    if (!response.ok) {
      throw new Error('Failed to send message');
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder();

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      const chunk = decoder.decode(value);
      const lines = chunk.split('\n');

      for (const line of lines) {
        if (line.startsWith('data: ')) {
          const data = line.slice(6);
          try {
            const event = JSON.parse(data);
            onEvent(event.type, event);
          } catch (e) {
            console.error('Failed to parse SSE event:', e);
          }
        }
      }
    }
  },
};
