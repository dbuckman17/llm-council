import { test, expect } from '@playwright/test';

// ─── Mock Data ──────────────────────────────────────────────────────────────

const MOCK_MODELS = {
  Anthropic: ['claude-opus-4-6', 'claude-sonnet-4-6', 'claude-haiku-4-5-20251001'],
  OpenAI: ['gpt-4.1', 'gpt-4.1-mini', 'o3'],
  Google: ['gemini-2.5-pro', 'gemini-2.5-flash', 'gemini-2.0-flash'],
};

const MOCK_TEMPLATES = [
  {
    id: 'expert_coder',
    name: 'Expert Coder',
    description: 'Specialized in programming tasks',
    system_prompt: 'You are an expert {{language}} programmer.',
    configurable_fields: [
      { id: 'language', label: 'Language', type: 'text', default: 'Python' },
    ],
  },
  {
    id: 'research_analyst',
    name: 'Research Analyst',
    description: 'Deep research and analysis',
    system_prompt: 'You are a research analyst specializing in {{topic}}.',
    configurable_fields: [
      { id: 'topic', label: 'Topic', type: 'text', default: '' },
    ],
  },
];

const MOCK_TOOLS = [
  { name: 'web_search', description: 'Search the web for information' },
  { name: 'calculator', description: 'Evaluate math expressions' },
  { name: 'code_execution', description: 'Execute Python code' },
];

const MOCK_CONNECTORS = [
  {
    name: 'web_search_prequery',
    description: 'Auto-search the web before querying models',
    config_schema: {
      properties: { num_results: { type: 'integer', default: 3, description: 'Number of results' } },
      required: [],
    },
  },
  {
    name: 'url_content',
    description: 'Fetch and inject URL content',
    config_schema: {
      properties: { url: { type: 'string', description: 'URL to fetch' } },
      required: ['url'],
    },
  },
];

const MOCK_CONVERSATIONS = [];

const MOCK_CONVERSATION = {
  id: 'test-conv-1',
  created_at: '2026-02-21T00:00:00Z',
  title: 'Test Conversation',
  messages: [],
};

// ─── Setup: Mock all backend API routes ─────────────────────────────────────

async function setupMocks(page) {
  await page.route('**/api/models', (route) =>
    route.fulfill({ json: MOCK_MODELS })
  );
  await page.route('**/api/templates', (route) =>
    route.fulfill({ json: MOCK_TEMPLATES })
  );
  await page.route('**/api/tools', (route) =>
    route.fulfill({ json: MOCK_TOOLS })
  );
  await page.route('**/api/connectors', (route) =>
    route.fulfill({ json: MOCK_CONNECTORS })
  );
  await page.route('**/api/conversations', (route, request) => {
    if (request.method() === 'GET') {
      return route.fulfill({ json: MOCK_CONVERSATIONS });
    }
    if (request.method() === 'POST') {
      return route.fulfill({ json: MOCK_CONVERSATION });
    }
    return route.continue();
  });
  await page.route('**/api/conversations/test-conv-1', (route) =>
    route.fulfill({ json: MOCK_CONVERSATION })
  );
  await page.route('**/api/conversations/test-conv-1/files', (route, request) => {
    if (request.method() === 'GET') {
      return route.fulfill({ json: [] });
    }
    return route.continue();
  });
}

// ─── Tests ──────────────────────────────────────────────────────────────────

test.describe('LLM Council UI', () => {
  test.beforeEach(async ({ page }) => {
    await setupMocks(page);
    await page.goto('/');
  });

  // ── 1. Page Load & Layout ─────────────────────────────────────────────────

  test('page loads with correct title and layout', async ({ page }) => {
    // Sidebar header
    await expect(page.locator('.sidebar h1')).toHaveText('LLM Council');
    // New Conversation button
    await expect(page.locator('.new-conversation-btn')).toBeVisible();
    // Empty state in main area
    await expect(page.locator('.empty-state h2')).toHaveText('Welcome to LLM Council');
    await expect(page.locator('.empty-state p')).toHaveText('Create a new conversation to get started');
  });

  // ── 2. Sidebar ────────────────────────────────────────────────────────────

  test('sidebar shows empty state and can create a conversation', async ({ page }) => {
    // Initially shows "No conversations yet"
    await expect(page.locator('.no-conversations')).toHaveText('No conversations yet');

    // Click New Conversation
    await page.click('.new-conversation-btn');

    // After creating, the conversation appears in the list
    await expect(page.locator('.conversation-item')).toHaveCount(1);
    // The item should be active
    await expect(page.locator('.conversation-item.active')).toHaveCount(1);
  });

  // ── 3. Chat Interface: Empty Conversation ─────────────────────────────────

  test('new conversation shows input area with all components', async ({ page }) => {
    await page.click('.new-conversation-btn');
    await page.waitForSelector('.input-area');

    // Model Selector exists
    await expect(page.locator('.model-selector')).toBeVisible();

    // Reasoning Effort selector exists
    await expect(page.locator('.reasoning-effort-selector')).toBeVisible();

    // Template Selector exists
    await expect(page.locator('.template-selector')).toBeVisible();

    // System prompt textarea exists
    await expect(page.locator('.system-prompt-input')).toBeVisible();

    // Tool Selector exists (because we return mock tools)
    await expect(page.locator('.tool-selector')).toBeVisible();

    // Connector Panel exists
    await expect(page.locator('.connector-panel')).toBeVisible();

    // File Upload exists
    await expect(page.locator('.file-upload')).toBeVisible();

    // Message input form exists
    await expect(page.locator('.message-input')).toBeVisible();

    // Optimize and Send buttons exist
    await expect(page.locator('.optimize-button')).toBeVisible();
    await expect(page.locator('.send-button')).toBeVisible();

    // Prompting Tips exists
    await expect(page.locator('.prompting-tips')).toBeVisible();
  });

  // ── 4. Model Selector ─────────────────────────────────────────────────────

  test('model selector shows all providers and models', async ({ page }) => {
    await page.click('.new-conversation-btn');
    await page.waitForSelector('.model-selector');

    // Three provider columns
    const providerColumns = page.locator('.provider-column');
    await expect(providerColumns).toHaveCount(3);

    // Provider names
    const providerNames = page.locator('.provider-name');
    await expect(providerNames.nth(0)).toHaveText('Anthropic');
    await expect(providerNames.nth(1)).toHaveText('OpenAI');
    await expect(providerNames.nth(2)).toHaveText('Google');

    // Total model checkboxes: 3 + 3 + 3 = 9
    const checkboxes = page.locator('.model-checkbox input[type="checkbox"]');
    await expect(checkboxes).toHaveCount(9);

    // Default: one per provider checked (indices 0, 3, 6)
    await expect(checkboxes.nth(0)).toBeChecked(); // claude-opus-4-6
    await expect(checkboxes.nth(3)).toBeChecked(); // gpt-4.1
    await expect(checkboxes.nth(6)).toBeChecked(); // gemini-2.5-pro

    // Chairman dropdown exists and has all models
    const chairmanSelect = page.locator('#chairman-select');
    await expect(chairmanSelect).toBeVisible();
    const chairmanOptions = chairmanSelect.locator('option');
    await expect(chairmanOptions).toHaveCount(9);
  });

  test('model selector toggles council members on click', async ({ page }) => {
    await page.click('.new-conversation-btn');
    await page.waitForSelector('.model-selector');

    const checkboxes = page.locator('.model-checkbox input[type="checkbox"]');
    // Uncheck first model
    await checkboxes.nth(0).uncheck();
    await expect(checkboxes.nth(0)).not.toBeChecked();

    // Check a new model
    await checkboxes.nth(1).check();
    await expect(checkboxes.nth(1)).toBeChecked();
  });

  test('chairman dropdown can be changed', async ({ page }) => {
    await page.click('.new-conversation-btn');
    await page.waitForSelector('.model-selector');

    const chairmanSelect = page.locator('#chairman-select');
    // Default should be first Google model
    await expect(chairmanSelect).toHaveValue('gemini-2.5-pro');

    // Change to an OpenAI model
    await chairmanSelect.selectOption('gpt-4.1');
    await expect(chairmanSelect).toHaveValue('gpt-4.1');
  });

  // ── 5. Reasoning Effort Selector ──────────────────────────────────────────

  test('reasoning effort buttons toggle correctly', async ({ page }) => {
    await page.click('.new-conversation-btn');
    await page.waitForSelector('.reasoning-effort-selector');

    const buttons = page.locator('.reasoning-option');
    await expect(buttons).toHaveCount(4);

    // Default is "Off"
    await expect(buttons.nth(0)).toHaveClass(/active/);
    await expect(page.locator('.reasoning-hint')).toHaveText('Standard responses');

    // Click High
    await buttons.nth(3).click();
    await expect(buttons.nth(3)).toHaveClass(/active/);
    await expect(buttons.nth(0)).not.toHaveClass(/active/);
    await expect(page.locator('.reasoning-hint')).toContainText('high');
  });

  // ── 6. Template Selector ──────────────────────────────────────────────────

  test('template selector shows templates and populates system prompt', async ({ page }) => {
    await page.click('.new-conversation-btn');
    await page.waitForSelector('.template-selector');

    const dropdown = page.locator('.template-dropdown');
    await expect(dropdown).toBeVisible();

    // Default is "None"
    await expect(dropdown).toHaveValue('');

    // Options: None + 2 templates = 3
    const options = dropdown.locator('option');
    await expect(options).toHaveCount(3);

    // Select Expert Coder
    await dropdown.selectOption('expert_coder');
    await expect(dropdown).toHaveValue('expert_coder');

    // Description should appear
    await expect(page.locator('.template-description')).toHaveText('Specialized in programming tasks');

    // Configurable field should appear
    await expect(page.locator('.template-field')).toBeVisible();
    await expect(page.locator('.field-label')).toHaveText('Language');

    // System prompt should be populated with default
    const systemPrompt = page.locator('.system-prompt-input');
    await expect(systemPrompt).toHaveValue('You are an expert Python programmer.');
  });

  test('template configurable field updates system prompt', async ({ page }) => {
    await page.click('.new-conversation-btn');
    await page.waitForSelector('.template-selector');

    // Select Expert Coder template
    await page.locator('.template-dropdown').selectOption('expert_coder');

    // Change the language field
    const fieldInput = page.locator('.field-input');
    await fieldInput.clear();
    await fieldInput.fill('Rust');

    // System prompt should update
    await expect(page.locator('.system-prompt-input')).toHaveValue('You are an expert Rust programmer.');
  });

  // ── 7. System Prompt ──────────────────────────────────────────────────────

  test('system prompt can be typed directly', async ({ page }) => {
    await page.click('.new-conversation-btn');
    await page.waitForSelector('.system-prompt-input');

    const systemPrompt = page.locator('.system-prompt-input');
    await systemPrompt.fill('You are a helpful assistant.');
    await expect(systemPrompt).toHaveValue('You are a helpful assistant.');
  });

  // ── 8. Tool Selector ─────────────────────────────────────────────────────

  test('tool selector shows all tools and toggles', async ({ page }) => {
    await page.click('.new-conversation-btn');
    await page.waitForSelector('.tool-selector');

    // Label
    await expect(page.locator('.tool-selector-label')).toHaveText('Stage 1 Tools');

    // 3 tools from mock data
    const toolCheckboxes = page.locator('.tool-checkbox input[type="checkbox"]');
    await expect(toolCheckboxes).toHaveCount(3);

    // All initially unchecked
    for (let i = 0; i < 3; i++) {
      await expect(toolCheckboxes.nth(i)).not.toBeChecked();
    }

    // Toggle web_search on
    await toolCheckboxes.nth(0).check();
    await expect(toolCheckboxes.nth(0)).toBeChecked();

    // Tool names visible
    await expect(page.locator('.tool-name').nth(0)).toHaveText('web_search');
    await expect(page.locator('.tool-name').nth(1)).toHaveText('calculator');
    await expect(page.locator('.tool-name').nth(2)).toHaveText('code_execution');
  });

  // ── 9. Connector Panel ────────────────────────────────────────────────────

  test('connector panel shows connectors and expands config', async ({ page }) => {
    await page.click('.new-conversation-btn');
    await page.waitForSelector('.connector-panel');

    // Label
    await expect(page.locator('.connector-panel-label')).toHaveText('Connectors');

    // 2 connectors
    const connectorToggles = page.locator('.connector-toggle input[type="checkbox"]');
    await expect(connectorToggles).toHaveCount(2);

    // Names
    await expect(page.locator('.connector-name').nth(0)).toHaveText('web_search_prequery');
    await expect(page.locator('.connector-name').nth(1)).toHaveText('url_content');

    // Enable first connector — config fields should appear
    await connectorToggles.nth(0).check();
    await expect(page.locator('.connector-config')).toBeVisible();
    await expect(page.locator('.connector-field-label')).toContainText('num_results');
  });

  // ── 10. File Upload Area ──────────────────────────────────────────────────

  test('file upload zone is visible', async ({ page }) => {
    await page.click('.new-conversation-btn');
    await page.waitForSelector('.file-upload');

    await expect(page.locator('.file-upload-label')).toHaveText('Attached Files');
    await expect(page.locator('.drop-zone')).toBeVisible();
    await expect(page.locator('.drop-zone-text')).toHaveText('Drop files here or click to browse');
  });

  // ── 11. Message Input ─────────────────────────────────────────────────────

  test('message input accepts text and send button enables', async ({ page }) => {
    await page.click('.new-conversation-btn');
    await page.waitForSelector('.message-input');

    const input = page.locator('.message-input');
    const sendButton = page.locator('.send-button');

    // Send disabled when empty
    await expect(sendButton).toBeDisabled();

    // Type text
    await input.fill('What is quantum computing?');
    await expect(input).toHaveValue('What is quantum computing?');

    // Send enabled
    await expect(sendButton).toBeEnabled();
  });

  test('optimize button enables when there is input text', async ({ page }) => {
    await page.click('.new-conversation-btn');
    await page.waitForSelector('.message-input');

    const optimizeButton = page.locator('.optimize-button');
    // Disabled when empty
    await expect(optimizeButton).toBeDisabled();

    // Type text
    await page.locator('.message-input').fill('Tell me about AI');
    await expect(optimizeButton).toBeEnabled();
  });

  // ── 12. Prompting Tips ────────────────────────────────────────────────────

  test('prompting tips starts collapsed and can be expanded', async ({ page }) => {
    await page.click('.new-conversation-btn');
    await page.waitForSelector('.prompting-tips');

    // Toggle button visible
    const toggle = page.locator('.tips-toggle');
    await expect(toggle).toContainText('Prompting Best Practices');

    // Tips content should NOT be visible initially
    await expect(page.locator('.tips-content')).not.toBeVisible();

    // Click to expand
    await toggle.click();
    await expect(page.locator('.tips-content')).toBeVisible();

    // Should contain some tips
    const tips = page.locator('.tips-list li');
    expect(await tips.count()).toBeGreaterThan(3);

    // Click again to collapse
    await toggle.click();
    await expect(page.locator('.tips-content')).not.toBeVisible();
  });

  // ── 13. Send Message Flow (mock SSE) ──────────────────────────────────────

  test('sending a message shows loading states and stages', async ({ page }) => {
    // Additional route to mock SSE streaming response
    await page.route('**/api/conversations/test-conv-1/message/stream', async (route) => {
      const events = [
        { type: 'stage1_start' },
        {
          type: 'stage1_complete',
          data: [
            { model: 'claude-opus-4-6', response: 'Claude says: Quantum computing uses qubits.', tool_calls: [] },
            { model: 'gpt-4.1', response: 'GPT says: Quantum computers leverage superposition.', tool_calls: [] },
            { model: 'gemini-2.5-pro', response: 'Gemini says: Quantum computing harnesses quantum mechanics.', tool_calls: [] },
          ],
        },
        { type: 'stage2_start' },
        {
          type: 'stage2_complete',
          data: [
            { model: 'claude-opus-4-6', ranking: 'Response A is best.\n\nFINAL RANKING:\n1. Response A\n2. Response C\n3. Response B', parsed_ranking: ['Response A', 'Response C', 'Response B'] },
            { model: 'gpt-4.1', ranking: 'Response C is thorough.\n\nFINAL RANKING:\n1. Response C\n2. Response A\n3. Response B', parsed_ranking: ['Response C', 'Response A', 'Response B'] },
            { model: 'gemini-2.5-pro', ranking: 'All are good.\n\nFINAL RANKING:\n1. Response A\n2. Response B\n3. Response C', parsed_ranking: ['Response A', 'Response B', 'Response C'] },
          ],
          metadata: {
            label_to_model: {
              'Response A': 'claude-opus-4-6',
              'Response B': 'gpt-4.1',
              'Response C': 'gemini-2.5-pro',
            },
            aggregate_rankings: [
              { model: 'claude-opus-4-6', average_rank: 1.33, rankings_count: 3 },
              { model: 'gemini-2.5-pro', average_rank: 2.0, rankings_count: 3 },
              { model: 'gpt-4.1', average_rank: 2.67, rankings_count: 3 },
            ],
          },
        },
        { type: 'stage3_start' },
        {
          type: 'stage3_complete',
          data: {
            model: 'gemini-2.5-pro',
            response: 'After considering all perspectives, quantum computing leverages quantum mechanical phenomena.',
          },
        },
        { type: 'stage4_start' },
        {
          type: 'stage4_complete',
          data: {
            model: 'gemini-2.5-pro',
            critique: 'The synthesis could be more detailed about decoherence and error correction.',
            suggested_system_prompt: 'You are a quantum physics expert.',
            suggested_query: 'Explain quantum computing with focus on practical applications and current limitations.',
          },
        },
        {
          type: 'cost_summary',
          data: {
            total: 0.1234,
            stage1: 0.05,
            stage2: 0.04,
            stage3: 0.02,
            stage4: 0.0134,
            by_model: {
              'claude-opus-4-6': 0.05,
              'gpt-4.1': 0.04,
              'gemini-2.5-pro': 0.0334,
            },
          },
        },
        { type: 'complete' },
      ];

      const body = events.map((e) => `data: ${JSON.stringify(e)}\n\n`).join('');
      await route.fulfill({
        status: 200,
        headers: { 'Content-Type': 'text/event-stream' },
        body,
      });
    });

    await page.click('.new-conversation-btn');
    await page.waitForSelector('.message-input');

    // Type and send
    await page.locator('.message-input').fill('What is quantum computing?');
    await page.locator('.send-button').click();

    // User message should appear
    await expect(page.locator('.user-message')).toBeVisible();
    await expect(page.locator('.message-label').first()).toHaveText('You');

    // Wait for Stage 1 to render
    await expect(page.locator('.stage1 .stage-title')).toHaveText('Stage 1: Individual Responses', { timeout: 10000 });

    // Stage 1 tabs
    const stage1Tabs = page.locator('.stage1 .tab');
    await expect(stage1Tabs).toHaveCount(3);
    await expect(stage1Tabs.nth(0)).toHaveText('claude-opus-4-6');
    await expect(stage1Tabs.nth(1)).toHaveText('gpt-4.1');
    await expect(stage1Tabs.nth(2)).toHaveText('gemini-2.5-pro');

    // Stage 2
    await expect(page.locator('.stage2 .stage-title')).toHaveText('Stage 2: Peer Rankings');
    // Aggregate rankings visible
    await expect(page.locator('.aggregate-rankings')).toBeVisible();
    await expect(page.locator('.aggregate-item')).toHaveCount(3);

    // Stage 3
    await expect(page.locator('.stage3 .stage-title')).toHaveText('Stage 3: Final Council Answer');
    await expect(page.locator('.chairman-label').first()).toContainText('gemini-2.5-pro');

    // Stage 4
    await expect(page.locator('.stage4 .stage-title')).toHaveText("Stage 4: Chairman's Reflection");
    // Suggested query textarea
    await expect(page.locator('.stage4 .suggestion-textarea').nth(1)).toHaveValue(
      'Explain quantum computing with focus on practical applications and current limitations.'
    );
    // Re-run button
    await expect(page.locator('.rerun-button')).toBeVisible();

    // Cost summary
    await expect(page.locator('.cost-summary')).toBeVisible();
    await expect(page.locator('.cost-total')).toContainText('$0.12');
  });

  // ── 14. Stage 1 Tab Switching ─────────────────────────────────────────────

  test('stage 1 tabs switch between model responses', async ({ page }) => {
    // Mock SSE with stage1 only for simplicity
    await page.route('**/api/conversations/test-conv-1/message/stream', async (route) => {
      const events = [
        {
          type: 'stage1_complete',
          data: [
            { model: 'claude-opus-4-6', response: 'Response from Claude', tool_calls: [] },
            { model: 'gpt-4.1', response: 'Response from GPT', tool_calls: [] },
          ],
        },
        { type: 'complete' },
      ];
      const body = events.map((e) => `data: ${JSON.stringify(e)}\n\n`).join('');
      await route.fulfill({
        status: 200,
        headers: { 'Content-Type': 'text/event-stream' },
        body,
      });
    });

    await page.click('.new-conversation-btn');
    await page.waitForSelector('.message-input');
    await page.locator('.message-input').fill('test');
    await page.locator('.send-button').click();

    await expect(page.locator('.stage1')).toBeVisible({ timeout: 10000 });

    // First tab active by default
    await expect(page.locator('.stage1 .tab.active')).toHaveText('claude-opus-4-6');
    await expect(page.locator('.response-text')).toContainText('Response from Claude');

    // Click second tab
    await page.locator('.stage1 .tab').nth(1).click();
    await expect(page.locator('.stage1 .tab.active')).toHaveText('gpt-4.1');
    await expect(page.locator('.response-text')).toContainText('Response from GPT');
  });

  // ── 15. Comprehensive Layout Check ────────────────────────────────────────

  test('app has correct CSS layout structure', async ({ page }) => {
    // Main app container
    await expect(page.locator('.app')).toBeVisible();
    // Sidebar
    await expect(page.locator('.sidebar')).toBeVisible();
    // Chat interface
    await expect(page.locator('.chat-interface')).toBeVisible();
  });

  // ── 16. Input Area Disappears After Sending ───────────────────────────────

  test('input area only shows for empty conversations', async ({ page }) => {
    await page.route('**/api/conversations/test-conv-1/message/stream', async (route) => {
      const events = [
        { type: 'stage1_complete', data: [{ model: 'claude-opus-4-6', response: 'Hello', tool_calls: [] }] },
        { type: 'complete' },
      ];
      const body = events.map((e) => `data: ${JSON.stringify(e)}\n\n`).join('');
      await route.fulfill({
        status: 200,
        headers: { 'Content-Type': 'text/event-stream' },
        body,
      });
    });

    await page.click('.new-conversation-btn');
    await page.waitForSelector('.input-area');

    // Input area visible for empty conversation
    await expect(page.locator('.input-area')).toBeVisible();

    // Send a message
    await page.locator('.message-input').fill('hi');
    await page.locator('.send-button').click();

    // After messages appear, input area should be gone
    await expect(page.locator('.stage1')).toBeVisible({ timeout: 10000 });
    await expect(page.locator('.input-area')).not.toBeVisible();
  });
});
